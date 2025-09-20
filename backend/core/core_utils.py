import json
import traceback
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from .utils.cache import Cache
from .utils.logger import logger
from .utils.config import config
from .utils.auth_utils import verify_and_authorize_thread_access
from core.services import redis_client as rc
from core.services.supabase import DBConnection
from core.services.llm import make_llm_api_call
from run_agent_background import update_agent_run_status, _cleanup_redis_response_list

# Global variables (will be set by initialize function)
db = None
instance_id = None

# Helper for version service
async def _get_version_service():
    from .versioning.version_service import get_version_service
    return await get_version_service()

async def cleanup():
    """Clean up resources and stop running agents on shutdown."""
    logger.debug("Starting cleanup of agent API resources")

    # Use the instance_id to find and clean up this instance's keys
    try:
        if instance_id: # Ensure instance_id is set
            running_keys = await rc.keys(f"active_run:{instance_id}:*")
            logger.debug(f"Found {len(running_keys)} running agent runs for instance {instance_id} to clean up")

            for key in running_keys:
                # Key format: active_run:{instance_id}:{agent_run_id}
                parts = key.split(":")
                if len(parts) == 3:
                    agent_run_id = parts[2]
                    await stop_agent_run_with_helpers(agent_run_id, error_message=f"Instance {instance_id} shutting down")
                else:
                    logger.warning(f"Unexpected key format found: {key}")
        else:
            logger.warning("Instance ID not set, cannot clean up instance-specific agent runs.")

    except Exception as e:
        logger.error(f"Failed to clean up running agent runs: {str(e)}")

    # Close Redis connection
    await rc.close()
    logger.debug("Completed cleanup of agent API resources")

async def stop_agent_run_with_helpers(agent_run_id: str, error_message: Optional[str] = None):
    """Update database and publish stop signal to Redis."""
    logger.debug(f"Stopping agent run: {agent_run_id}")
    client = await db.client
    final_status = "failed" if error_message else "stopped"

    # Attempt to fetch final responses from Redis
    response_list_key = f"agent_run:{agent_run_id}:responses"
    all_responses = []
    try:
        all_responses_json = await rc.lrange(response_list_key, 0, -1)
        all_responses = [json.loads(r) for r in all_responses_json]
        logger.debug(f"Fetched {len(all_responses)} responses from Redis for DB update on stop/fail: {agent_run_id}")
    except Exception as e:
        logger.error(f"Failed to fetch responses from Redis for {agent_run_id} during stop/fail: {e}")
        # Try fetching from DB as a fallback? Or proceed without responses? Proceeding without for now.

    # Update the agent run status in the database
    update_success = await update_agent_run_status(
        client, agent_run_id, final_status, error=error_message
    )

    if not update_success:
        logger.error(f"Failed to update database status for stopped/failed run {agent_run_id}")
        raise HTTPException(status_code=500, detail="Failed to update agent run status in database")

    # Send STOP signal to the global control channel
    global_control_channel = f"agent_run:{agent_run_id}:control"
    try:
        await rc.publish(global_control_channel, "STOP")
        logger.debug(f"Published STOP signal to global channel {global_control_channel}")
    except Exception as e:
        logger.error(f"Failed to publish STOP signal to global channel {global_control_channel}: {str(e)}")

    # Find all instances handling this agent run and send STOP to instance-specific channels
    try:
        instance_keys = await rc.keys(f"active_run:*:{agent_run_id}")
        logger.debug(f"Found {len(instance_keys)} active instance keys for agent run {agent_run_id}")

        for key in instance_keys:
            # Key format: active_run:{instance_id}:{agent_run_id}
            parts = key.split(":")
            if len(parts) == 3:
                instance_id_from_key = parts[1]
                instance_control_channel = f"agent_run:{agent_run_id}:control:{instance_id_from_key}"
                try:
                    await rc.publish(instance_control_channel, "STOP")
                    logger.debug(f"Published STOP signal to instance channel {instance_control_channel}")
                except Exception as e:
                    logger.warning(f"Failed to publish STOP signal to instance channel {instance_control_channel}: {str(e)}")
            else:
                 logger.warning(f"Unexpected key format found: {key}")

        # Clean up the response list immediately on stop/fail
        await _cleanup_redis_response_list(agent_run_id)

    except Exception as e:
        logger.error(f"Failed to find or signal active instances for {agent_run_id}: {str(e)}")

    logger.debug(f"Successfully initiated stop process for agent run: {agent_run_id}")

async def get_agent_run_with_access_check(client, agent_run_id: str, user_id: str):
    agent_run = await client.table('agent_runs').select('*, threads(account_id)').eq('id', agent_run_id).execute()
    if not agent_run.data:
        raise HTTPException(status_code=404, detail="Agent run not found")

    agent_run_data = agent_run.data[0]
    thread_id = agent_run_data['thread_id']
    account_id = agent_run_data['threads']['account_id']
    if account_id == user_id:
        return agent_run_data
    await verify_and_authorize_thread_access(client, thread_id, user_id)
    return agent_run_data

async def generate_and_update_project_name(project_id: str, prompt: str):
    """Generates a project name using an LLM and updates the database."""
    logger.info(f"🎯 TITLE_GEN: Starting title generation for project {project_id}")
    logger.info(f"🎯 TITLE_GEN: Original prompt: '{prompt}'")
    logger.info(f"🎯 TITLE_GEN: Prompt length: {len(prompt)} characters")
    
    try:
        db_conn = DBConnection()
        client = await db_conn.client
        logger.info(f"🎯 TITLE_GEN: Database connection established for project {project_id}")

        # Try multiple models in order of preference
        models_to_try = [
            "gemini/gemini-2.5-flash-lite",
            "openrouter/google/gemini-2.5-flash-lite", 
            "openai/gpt-4o-mini",
            "openrouter/openai/gpt-4o-mini"
        ]
        
        logger.info(f"🎯 TITLE_GEN: Will try {len(models_to_try)} models in order: {models_to_try}")
        
        system_prompt = "You are a helpful assistant that generates extremely concise titles (2-4 words maximum) for chat threads based on the user's message. Respond with only the title, no other text or punctuation."
        user_message = f"Generate an extremely brief title (2-4 words only) for a chat thread that starts with this message: \"{prompt}\""
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]

        logger.info(f"🎯 TITLE_GEN: System prompt: '{system_prompt}'")
        logger.info(f"🎯 TITLE_GEN: User message: '{user_message}'")
        logger.info(f"🎯 TITLE_GEN: Total messages: {len(messages)}")

        generated_name = None
        
        for model_index, model_name in enumerate(models_to_try, 1):
            try:
                logger.info(f"🎯 TITLE_GEN: Attempt {model_index}/{len(models_to_try)} - Trying model: {model_name}")
                logger.info(f"🎯 TITLE_GEN: Making LLM API call with max_tokens=20, temperature=0.7")
                
                response = await make_llm_api_call(messages=messages, model_name=model_name, max_tokens=20, temperature=0.7)

                logger.info(f"🎯 TITLE_GEN: Received response from {model_name}")
                logger.info(f"🎯 TITLE_GEN: Response type: {type(response)}")
                logger.info(f"🎯 TITLE_GEN: Response object: {response}")

                # Handle both dictionary responses and LiteLLM response objects
                if response:
                    logger.info(f"🎯 TITLE_GEN: Processing response from {model_name}")
                    
                    if isinstance(response, dict) and response.get('choices') and response['choices'][0].get('message'):
                        # OpenAI-style response format
                        raw_name = response['choices'][0]['message'].get('content', '').strip()
                        logger.info(f"🎯 TITLE_GEN: OpenAI-style response - extracted content: '{raw_name}'")
                    elif hasattr(response, 'choices') and response.choices and hasattr(response.choices[0], 'message'):
                        # LiteLLM response object format
                        raw_name = response.choices[0].message.content.strip()
                        logger.info(f"🎯 TITLE_GEN: LiteLLM response object - extracted content: '{raw_name}'")
                    elif hasattr(response, 'choices') and response.choices:
                        # Try to access content directly from choices
                        choice = response.choices[0]
                        logger.info(f"🎯 TITLE_GEN: Choice object: {choice}")
                        logger.info(f"🎯 TITLE_GEN: Choice attributes: {dir(choice)}")
                        
                        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                            raw_name = choice.message.content.strip()
                            logger.info(f"🎯 TITLE_GEN: Direct choice access - extracted content: '{raw_name}'")
                        elif hasattr(choice, 'text'):
                            raw_name = choice.text.strip()
                            logger.info(f"🎯 TITLE_GEN: Choice text access - extracted content: '{raw_name}'")
                        else:
                            logger.warning(f"🎯 TITLE_GEN: Unexpected choice format: {choice}")
                            raw_name = ""
                    else:
                        logger.warning(f"🎯 TITLE_GEN: Unexpected response format from LLM for project {project_id} naming. Response: {response}")
                        raw_name = ""
                    
                    logger.info(f"🎯 TITLE_GEN: Raw extracted name: '{raw_name}'")
                    cleaned_name = raw_name.strip('\'" \n\t')
                    logger.info(f"🎯 TITLE_GEN: Cleaned name: '{cleaned_name}'")
                    
                    if cleaned_name:
                        generated_name = cleaned_name
                        logger.info(f"🎯 TITLE_GEN: ✅ SUCCESS! Generated name '{generated_name}' using model {model_name}")
                        logger.info(f"🎯 TITLE_GEN: Breaking out of model loop after successful generation")
                        break  # Success! Exit the loop
                    else:
                        logger.warning(f"🎯 TITLE_GEN: ❌ Empty name from {model_name}. Raw name was: '{raw_name}'")
                else:
                    logger.warning(f"🎯 TITLE_GEN: ❌ No response from {model_name} for project {project_id}")
                    
            except Exception as e:
                logger.error(f"🎯 TITLE_GEN: ❌ Error calling model {model_name} for project {project_id}: {str(e)}")
                logger.error(f"🎯 TITLE_GEN: Exception type: {type(e)}")
                continue  # Try next model

        if generated_name:
            logger.info(f"🎯 TITLE_GEN: Attempting to update database with generated name: '{generated_name}'")
            update_result = await client.table('projects').update({"name": generated_name}).eq("project_id", project_id).execute()
            
            logger.info(f"🎯 TITLE_GEN: Database update result: {update_result}")
            logger.info(f"🎯 TITLE_GEN: Update result type: {type(update_result)}")
            logger.info(f"🎯 TITLE_GEN: Update result has 'data' attr: {hasattr(update_result, 'data')}")
            
            if hasattr(update_result, 'data') and update_result.data:
                logger.info(f"🎯 TITLE_GEN: ✅ Database update successful! Project {project_id} name set to '{generated_name}'")
                logger.info(f"🎯 TITLE_GEN: Update result data: {update_result.data}")
            else:
                logger.error(f"🎯 TITLE_GEN: ❌ Database update failed for project {project_id}")
                logger.error(f"🎯 TITLE_GEN: Update result: {update_result}")
        else:
            # Final fallback: generate a simple title from the prompt
            logger.warning(f"🎯 TITLE_GEN: ⚠️ No generated name from any model, using fallback for project {project_id}")
            logger.info(f"🎯 TITLE_GEN: Generating fallback title from prompt: '{prompt}'")
            fallback_name = _generate_fallback_title(prompt)
            
            if fallback_name:
                logger.info(f"🎯 TITLE_GEN: Fallback title generated: '{fallback_name}'")
                logger.info(f"🎯 TITLE_GEN: Attempting to update database with fallback name: '{fallback_name}'")
                
                update_result = await client.table('projects').update({"name": fallback_name}).eq("project_id", project_id).execute()
                
                logger.info(f"🎯 TITLE_GEN: Fallback database update result: {update_result}")
                
                if hasattr(update_result, 'data') and update_result.data:
                    logger.info(f"🎯 TITLE_GEN: ✅ Fallback database update successful! Project {project_id} name set to '{fallback_name}'")
                else:
                    logger.error(f"🎯 TITLE_GEN: ❌ Fallback database update failed for project {project_id}")
                    logger.error(f"🎯 TITLE_GEN: Fallback update result: {update_result}")
            else:
                logger.error(f"🎯 TITLE_GEN: ❌ Failed to generate any name for project {project_id}")

    except Exception as e:
        logger.error(f"🎯 TITLE_GEN: ❌ CRITICAL ERROR in title generation for project {project_id}: {str(e)}")
        logger.error(f"🎯 TITLE_GEN: Exception type: {type(e)}")
        logger.error(f"🎯 TITLE_GEN: Full traceback:\n{traceback.format_exc()}")
    finally:
        # No need to disconnect DBConnection singleton instance here
        logger.info(f"🎯 TITLE_GEN: Finished title generation task for project: {project_id}")

def _generate_fallback_title(prompt: str) -> str:
    """Generate a simple fallback title from the prompt when LLM fails."""
    logger.info(f"🎯 FALLBACK: Starting fallback title generation for prompt: '{prompt}'")
    
    try:
        # Extract key words from the prompt
        words = prompt.lower().split()
        logger.info(f"🎯 FALLBACK: Original words: {words}")
        logger.info(f"🎯 FALLBACK: Total words: {len(words)}")
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'help', 'me', 'my', 'i', 'you', 'we', 'they', 'this', 'that', 'these', 'those'}
        
        # Filter out stop words and keep only meaningful words
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
        logger.info(f"🎯 FALLBACK: Stop words filtered out: {stop_words}")
        logger.info(f"🎯 FALLBACK: Meaningful words: {meaningful_words}")
        logger.info(f"🎯 FALLBACK: Meaningful words count: {len(meaningful_words)}")
        
        # Take first 2-4 meaningful words
        if len(meaningful_words) >= 2:
            title_words = meaningful_words[:min(4, len(meaningful_words))]
            fallback_title = ' '.join(title_words).title()
            logger.info(f"🎯 FALLBACK: Using meaningful words path - title_words: {title_words}")
        else:
            # If not enough meaningful words, just take first few words
            title_words = words[:min(3, len(words))]
            fallback_title = ' '.join(title_words).title()
            logger.info(f"🎯 FALLBACK: Using fallback words path - title_words: {title_words}")
        
        # Ensure title is not too long
        if len(fallback_title) > 50:
            fallback_title = fallback_title[:47] + "..."
            logger.info(f"🎯 FALLBACK: Title truncated to 50 chars: '{fallback_title}'")
            
        logger.info(f"🎯 FALLBACK: ✅ Generated fallback title: '{fallback_title}' from prompt: '{prompt}'")
        return fallback_title
        
    except Exception as e:
        logger.error(f"🎯 FALLBACK: ❌ Error generating fallback title: {str(e)}")
        logger.error(f"🎯 FALLBACK: Exception type: {type(e)}")
        return "New Project"

def merge_custom_mcps(existing_mcps: List[Dict[str, Any]], new_mcps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not new_mcps:
        return existing_mcps
    
    merged_mcps = existing_mcps.copy()
    
    for new_mcp in new_mcps:
        new_mcp_name = new_mcp.get('name')
        existing_index = None
        
        for i, existing_mcp in enumerate(merged_mcps):
            if existing_mcp.get('name') == new_mcp_name:
                existing_index = i
                break
        
        if existing_index is not None:
            merged_mcps[existing_index] = new_mcp
        else:
            merged_mcps.append(new_mcp)
    
    return merged_mcps

def initialize(
    _db: DBConnection,
    _instance_id: Optional[str] = None
):
    """Initialize the agent API with resources from the main API."""
    global db, instance_id
    db = _db
    
    # Initialize the versioning module with the same database connection
    from .versioning.api import initialize as initialize_versioning
    initialize_versioning(_db)

    # Use provided instance_id or generate a new one
    if _instance_id:
        instance_id = _instance_id
    else:
        # Generate instance ID
        instance_id = str(uuid.uuid4())[:8]

    logger.debug(f"Initialized agent API with instance ID: {instance_id}")

async def _cleanup_redis_response_list(agent_run_id: str):
    try:
        response_list_key = f"agent_run:{agent_run_id}:responses"
        await rc.delete(response_list_key)
        logger.debug(f"Cleaned up Redis response list for agent run {agent_run_id}")
    except Exception as e:
        logger.warning(f"Failed to clean up Redis response list for {agent_run_id}: {str(e)}")


async def check_for_active_project_agent_run(client, project_id: str):
    project_threads = await client.table('threads').select('thread_id').eq('project_id', project_id).execute()
    project_thread_ids = [t['thread_id'] for t in project_threads.data]

    if project_thread_ids:
        from .utils.query_utils import batch_query_in
        
        active_runs = await batch_query_in(
            client=client,
            table_name='agent_runs',
            select_fields='id',
            in_field='thread_id',
            in_values=project_thread_ids,
            additional_filters={'status': 'running'}
        )
        
        if active_runs:
            return active_runs[0]['id']
    return None


async def stop_agent_run(db, agent_run_id: str, error_message: Optional[str] = None):
    logger.debug(f"Stopping agent run: {agent_run_id}")
    client = await db.client
    final_status = "failed" if error_message else "stopped"

    response_list_key = f"agent_run:{agent_run_id}:responses"
    all_responses = []
    try:
        all_responses_json = await rc.lrange(response_list_key, 0, -1)
        all_responses = [json.loads(r) for r in all_responses_json]
        logger.debug(f"Fetched {len(all_responses)} responses from Redis for DB update on stop/fail: {agent_run_id}")
    except Exception as e:
        logger.error(f"Failed to fetch responses from Redis for {agent_run_id} during stop/fail: {e}")

    update_success = await update_agent_run_status(
        client, agent_run_id, final_status, error=error_message, responses=all_responses
    )

    if not update_success:
        logger.error(f"Failed to update database status for stopped/failed run {agent_run_id}")

    global_control_channel = f"agent_run:{agent_run_id}:control"
    try:
        await rc.publish(global_control_channel, "STOP")
        logger.debug(f"Published STOP signal to global channel {global_control_channel}")
    except Exception as e:
        logger.error(f"Failed to publish STOP signal to global channel {global_control_channel}: {str(e)}")

    try:
        instance_keys = await rc.keys(f"active_run:*:{agent_run_id}")
        logger.debug(f"Found {len(instance_keys)} active instance keys for agent run {agent_run_id}")

        for key in instance_keys:
            parts = key.split(":")
            if len(parts) == 3:
                instance_id_from_key = parts[1]
                instance_control_channel = f"agent_run:{agent_run_id}:control:{instance_id_from_key}"
                try:
                    await rc.publish(instance_control_channel, "STOP")
                    logger.debug(f"Published STOP signal to instance channel {instance_control_channel}")
                except Exception as e:
                    logger.warning(f"Failed to publish STOP signal to instance channel {instance_control_channel}: {str(e)}")
            else:
                logger.warning(f"Unexpected key format found: {key}")

        await _cleanup_redis_response_list(agent_run_id)

    except Exception as e:
        logger.error(f"Failed to find or signal active instances for {agent_run_id}: {str(e)}")

    logger.debug(f"Successfully initiated stop process for agent run: {agent_run_id}")


async def check_agent_run_limit(client, account_id: str) -> Dict[str, Any]:
    """
    Check if the account has reached the limit of 3 parallel agent runs within the past 24 hours.
    
    Returns:
        Dict with 'can_start' (bool), 'running_count' (int), 'running_thread_ids' (list)
        
    Note: This function does not use caching to ensure real-time limit checks.
    """
    try:

        # Calculate 24 hours ago
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        twenty_four_hours_ago_iso = twenty_four_hours_ago.isoformat()
        
        logger.debug(f"Checking agent run limit for account {account_id} since {twenty_four_hours_ago_iso}")
        
        # Get all threads for this account
        threads_result = await client.table('threads').select('thread_id').eq('account_id', account_id).execute()
        
        if not threads_result.data:
            logger.debug(f"No threads found for account {account_id}")
            return {
                'can_start': True,
                'running_count': 0,
                'running_thread_ids': []
            }
        
        thread_ids = [thread['thread_id'] for thread in threads_result.data]
        logger.debug(f"Found {len(thread_ids)} threads for account {account_id}")
        
        # Query for running agent runs within the past 24 hours for these threads
        from .utils.query_utils import batch_query_in
        
        running_runs = await batch_query_in(
            client=client,
            table_name='agent_runs',
            select_fields='id, thread_id, started_at',
            in_field='thread_id',
            in_values=thread_ids,
            additional_filters={
                'status': 'running',
                'started_at_gte': twenty_four_hours_ago_iso
            }
        )
        
        running_count = len(running_runs)
        running_thread_ids = [run['thread_id'] for run in running_runs]
        
        logger.debug(f"Account {account_id} has {running_count} running agent runs in the past 24 hours")
        
        result = {
            'can_start': running_count < config.MAX_PARALLEL_AGENT_RUNS,
            'running_count': running_count,
            'running_thread_ids': running_thread_ids
        }
        return result

    except Exception as e:
        logger.error(f"Error checking agent run limit for account {account_id}: {str(e)}")
        # In case of error, allow the run to proceed but log the error
        return {
            'can_start': True,
            'running_count': 0,
            'running_thread_ids': []
        }


async def check_agent_count_limit(client, account_id: str) -> Dict[str, Any]:
    """
    Check if a user can create more agents based on their subscription tier.
    
    Returns:
        Dict containing:
        - can_create: bool - whether user can create another agent
        - current_count: int - current number of custom agents (excluding Suna defaults)
        - limit: int - maximum agents allowed for this tier
        - tier_name: str - subscription tier name
    
    Note: This function does not use caching to ensure real-time agent counts.
    """
    try:
        # In local mode, allow practically unlimited custom agents
        if config.ENV_MODE.value == "local":
            return {
                'can_create': True,
                'current_count': 0,  # Return 0 to avoid showing any limit warnings
                'limit': 999999,     # Practically unlimited
                'tier_name': 'local'
            }
        
        # Always query fresh data from database to avoid stale cache issues
        agents_result = await client.table('agents').select('agent_id, metadata').eq('account_id', account_id).execute()
        
        non_suna_agents = []
        for agent in agents_result.data or []:
            metadata = agent.get('metadata', {}) or {}
            is_suna_default = metadata.get('is_suna_default', False)
            if not is_suna_default:
                non_suna_agents.append(agent)
                
        current_count = len(non_suna_agents)
        logger.debug(f"Account {account_id} has {current_count} custom agents (excluding Suna defaults)")
        
        try:
            from core.services.billing import get_subscription_tier
            tier_name = await get_subscription_tier(client, account_id)
            logger.debug(f"Account {account_id} subscription tier: {tier_name}")
        except Exception as billing_error:
            logger.warning(f"Could not get subscription tier for {account_id}: {str(billing_error)}, defaulting to free")
            tier_name = 'free'
        
        agent_limit = config.AGENT_LIMITS.get(tier_name, config.AGENT_LIMITS['free'])
        
        can_create = current_count < agent_limit
        
        result = {
            'can_create': can_create,
            'current_count': current_count,
            'limit': agent_limit,
            'tier_name': tier_name
        }
        
        logger.debug(f"Account {account_id} has {current_count}/{agent_limit} agents (tier: {tier_name}) - can_create: {can_create} (real-time count)")
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking agent count limit for account {account_id}: {str(e)}", exc_info=True)
        return {
            'can_create': True,
            'current_count': 0,
            'limit': config.AGENT_LIMITS['free'],
            'tier_name': 'free'
        }


async def check_project_count_limit(client, account_id: str) -> Dict[str, Any]:
    """
    Check if a user can create more projects based on their subscription tier.
    
    Returns:
        Dict containing:
        - can_create: bool - whether user can create another project
        - current_count: int - current number of projects
        - limit: int - maximum projects allowed for this tier
        - tier_name: str - subscription tier name
    
    Note: This function does not use caching to ensure real-time project counts,
    preventing issues where deleted projects aren't immediately reflected in limits.
    """
    try:
        # In local mode, allow practically unlimited projects
        if config.ENV_MODE.value == "local":
            return {
                'can_create': True,
                'current_count': 0,  # Return 0 to avoid showing any limit warnings
                'limit': 999999,     # Practically unlimited
                'tier_name': 'local'
            }
        
        try:
            result = await Cache.get(f"project_count_limit:{account_id}")
            if result:
                logger.debug(f"Cache hit for project count limit: {account_id}")
                return result
        except Exception as cache_error:
            logger.warning(f"Cache read failed for project count limit {account_id}: {str(cache_error)}")

        projects_result = await client.table('projects').select('project_id').eq('account_id', account_id).execute()
        current_count = len(projects_result.data or [])
        logger.debug(f"Account {account_id} has {current_count} projects (real-time count)")
        
        try:
            credit_result = await client.table('credit_accounts').select('tier').eq('account_id', account_id).single().execute()
            tier_name = credit_result.data.get('tier', 'free') if credit_result.data else 'free'
            logger.debug(f"Account {account_id} credit tier: {tier_name}")
        except Exception as credit_error:
            try:
                logger.debug(f"Trying user_id fallback for account {account_id}")
                credit_result = await client.table('credit_accounts').select('tier').eq('user_id', account_id).single().execute()
                tier_name = credit_result.data.get('tier', 'free') if credit_result.data else 'free'
                logger.debug(f"Account {account_id} credit tier (via fallback): {tier_name}")
            except:
                logger.debug(f"No credit account for {account_id}, defaulting to free tier")
                tier_name = 'free'
        
        # Import billing config conditionally
        try:
            from core.settings import settings
            if settings.BILLING_ENABLED:
                from billing.config import get_project_limit
                project_limit = get_project_limit(tier_name)
            else:
                # Default to unlimited when billing is disabled
                project_limit = 999999
        except ImportError:
            # Fallback if billing module is not available
            project_limit = 999999
        can_create = current_count < project_limit
        
        result = {
            'can_create': can_create,
            'current_count': current_count,
            'limit': project_limit,
            'tier_name': tier_name
        }
        
        logger.debug(f"Account {account_id} has {current_count}/{project_limit} projects (tier: {tier_name}) - can_create: {can_create}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking project count limit for account {account_id}: {str(e)}", exc_info=True)
        return {
            'can_create': False,
            'current_count': 0,
            'limit': config.PROJECT_LIMITS['free'],
            'tier_name': 'free'
        }


if __name__ == "__main__":
    import asyncio
    import sys
    import os
    
    # Add the backend directory to the Python path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from core.services.supabase import DBConnection
    from .utils.logger import logger
    
    async def test_large_thread_count():
        """Test the functions with a large number of threads to verify URI limit fixes."""
        print("🧪 Testing URI limit fixes with large thread counts...")
        
        try:
            # Initialize database connection
            db = DBConnection()
            client = await db.client
            
            # Test user ID (replace with actual user ID that has many threads)
            test_user_id = "2558d81e-5008-46d6-b7d3-8cc62d44e4f6"  # The user from the error logs
            
            print(f"📊 Testing with user ID: {test_user_id}")
            
            # Test 1: check_agent_run_limit with many threads
            print("\n1️⃣ Testing check_agent_run_limit...")
            try:
                result = await check_agent_run_limit(client, test_user_id)
                print(f"✅ check_agent_run_limit succeeded:")
                print(f"   - Can start: {result['can_start']}")
                print(f"   - Running count: {result['running_count']}")
                print(f"   - Running thread IDs: {len(result['running_thread_ids'])} threads")
            except Exception as e:
                print(f"❌ check_agent_run_limit failed: {str(e)}")
            
            # Test 2: Get a project ID to test check_for_active_project_agent_run
            print("\n2️⃣ Testing check_for_active_project_agent_run...")
            try:
                # Get a project for this user
                projects_result = await client.table('projects').select('project_id').eq('account_id', test_user_id).limit(1).execute()
                
                if projects_result.data and len(projects_result.data) > 0:
                    test_project_id = projects_result.data[0]['project_id']
                    print(f"   Using project ID: {test_project_id}")
                    
                    result = await check_for_active_project_agent_run(client, test_project_id)
                    print(f"✅ check_for_active_project_agent_run succeeded:")
                    print(f"   - Active run ID: {result}")
                else:
                    print("   ⚠️  No projects found for user, skipping this test")
            except Exception as e:
                print(f"❌ check_for_active_project_agent_run failed: {str(e)}")
            
            # Test 3: check_agent_count_limit (doesn't have URI issues but good to test)
            print("\n3️⃣ Testing check_agent_count_limit...")
            try:
                result = await check_agent_count_limit(client, test_user_id)
                print(f"✅ check_agent_count_limit succeeded:")
                print(f"   - Can create: {result['can_create']}")
                print(f"   - Current count: {result['current_count']}")
                print(f"   - Limit: {result['limit']}")
                print(f"   - Tier: {result['tier_name']}")
            except Exception as e:
                print(f"❌ check_agent_count_limit failed: {str(e)}")

            print("\n🎉 All agent utils tests completed!")
            
        except Exception as e:
            print(f"❌ Test setup failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    async def test_billing_integration():
        """Test the billing integration to make sure it works with the fixed functions."""
        print("\n💰 Testing billing integration...")
        
        try:
            from core.services.billing import calculate_monthly_usage, get_usage_logs
            
            db = DBConnection()
            client = await db.client
            
            test_user_id = "2558d81e-5008-46d6-b7d3-8cc62d44e4f6"
            
            print(f"📊 Testing billing functions with user: {test_user_id}")
            
            # Test calculate_monthly_usage (which uses get_usage_logs internally)
            print("\n1️⃣ Testing calculate_monthly_usage...")
            try:
                usage = await calculate_monthly_usage(client, test_user_id)
                print(f"✅ calculate_monthly_usage succeeded: ${usage:.4f}")
            except Exception as e:
                print(f"❌ calculate_monthly_usage failed: {str(e)}")
            
            # Test get_usage_logs directly with pagination
            print("\n2️⃣ Testing get_usage_logs with pagination...")
            try:
                logs = await get_usage_logs(client, test_user_id, page=0, items_per_page=10)
                print(f"✅ get_usage_logs succeeded:")
                print(f"   - Found {len(logs.get('logs', []))} log entries")
                print(f"   - Has more: {logs.get('has_more', False)}")
                print(f"   - Subscription limit: ${logs.get('subscription_limit', 0)}")
            except Exception as e:
                print(f"❌ get_usage_logs failed: {str(e)}")
                
        except ImportError as e:
            print(f"⚠️  Could not import billing functions: {str(e)}")
        except Exception as e:
            print(f"❌ Billing test failed: {str(e)}")
    
    async def test_api_functions():
        """Test the API functions that were also fixed for URI limits."""
        print("\n🔧 Testing API functions...")
        
        try:
            # Import the API functions we fixed
            import sys
            sys.path.append('/app')  # Add the app directory to path
            
            db = DBConnection()
            client = await db.client
            
            test_user_id = "2558d81e-5008-46d6-b7d3-8cc62d44e4f6"
            
            print(f"📊 Testing API functions with user: {test_user_id}")
            
            # Test 1: get_user_threads (which has the project batching fix)
            print("\n1️⃣ Testing get_user_threads simulation...")
            try:
                # Get threads for the user
                threads_result = await client.table('threads').select('*').eq('account_id', test_user_id).order('created_at', desc=True).execute()
                
                if threads_result.data:
                    print(f"   - Found {len(threads_result.data)} threads")
                    
                    # Extract unique project IDs (this is what could cause URI issues)
                    project_ids = [
                        thread['project_id'] for thread in threads_result.data[:1000]  # Limit to first 1000
                        if thread.get('project_id')
                    ]
                    unique_project_ids = list(set(project_ids)) if project_ids else []
                    
                    print(f"   - Found {len(unique_project_ids)} unique project IDs")
                    
                    if unique_project_ids:
                        # Test the batching logic we implemented
                        if len(unique_project_ids) > 100:
                            print(f"   - Would use batching for {len(unique_project_ids)} project IDs")
                        else:
                            print(f"   - Would use direct query for {len(unique_project_ids)} project IDs")
                        
                        # Actually test a small batch to verify it works
                        test_batch = unique_project_ids[:min(10, len(unique_project_ids))]
                        projects_result = await client.table('projects').select('*').in_('project_id', test_batch).execute()
                        print(f"✅ Project query test succeeded: found {len(projects_result.data or [])} projects")
                    else:
                        print("   - No project IDs to test")
                else:
                    print("   - No threads found for user")
                    
            except Exception as e:
                print(f"❌ get_user_threads test failed: {str(e)}")
            
            # Test 2: Template service simulation
            print("\n2️⃣ Testing template service simulation...")
            try:
                from core.templates.template_service import TemplateService
                
                # This would test the creator ID batching, but we'll just verify the import works
                print("✅ Template service import succeeded")
                
            except ImportError as e:
                print(f"⚠️  Could not import template service: {str(e)}")
            except Exception as e:
                print(f"❌ Template service test failed: {str(e)}")
                
        except Exception as e:
            print(f"❌ API functions test failed: {str(e)}")
    
    async def main():
        """Main test function."""
        print("🚀 Starting URI limit fix tests...\n")
        
        await test_large_thread_count()
        await test_billing_integration()
        await test_api_functions()
        
        print("\n✨ Test suite completed!")
    
    # Run the tests
    asyncio.run(main())
