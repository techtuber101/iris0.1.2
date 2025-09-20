import dotenv
dotenv.load_dotenv(".env")

# Configure logging first to reduce spam
from core.logging_config import configure_logging
configure_logging()

import sentry
import asyncio
import json
import traceback
from datetime import datetime, timezone
from typing import Optional
from core.services import redis_client as rc
from core.run import run_agent
from core.utils.logger import logger, structlog
import dramatiq
import uuid
from core.agentpress.thread_manager import ThreadManager
from core.services.supabase import DBConnection
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO
import os
from core.services.langfuse import langfuse
from core.utils.retry import retry

import sentry_sdk
from typing import Dict, Any

# Build sync client for broker
_sync_client = rc.build_sync_client()

# Attach broker (works across dramatiq versions)
broker = RedisBroker(client=_sync_client)
middleware = []
# Use AsyncIO middleware only if you have async actors; it's fine to keep.
middleware.append(AsyncIO())
for m in middleware:
    broker.add_middleware(m)

dramatiq.set_broker(broker)

# ---- app init helpers ----
_initialized = False
db = DBConnection()
instance_id = "single"
_ASYNC_REDIS = None

async def initialize():
    """Initialize the agent API with resources from the main API."""
    global db, instance_id, _initialized, _ASYNC_REDIS

    if not instance_id:
        instance_id = str(uuid.uuid4())[:8]
    
    # Build and warm up an async client for any async paths in your app
    _ASYNC_REDIS = rc.build_async_client()
    await rc.initialize_async_client(_ASYNC_REDIS)
    
    await db.initialize()

    _initialized = True
    logger.debug(f"Initialized agent API with instance ID: {instance_id}")

# Your actor(s) should import from this module or be listed in the dramatiq CLI
@dramatiq.actor
async def check_health(key: str):
    """Run the agent in the background using Redis for state."""
    structlog.contextvars.clear_contextvars()
    await _ASYNC_REDIS.set(key, "healthy", ex=rc.REDIS_KEY_TTL)

@dramatiq.actor
async def run_agent_background(
    agent_run_id: str,
    thread_id: str,
    instance_id: str,
    project_id: str,
    model_name: str = "gemini/gemini-2.5-flash",
    enable_thinking: bool = False,
    reasoning_effort: str = "low",
    stream: bool = True,
    enable_context_manager: bool = False,
    agent_config: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
):
    """Run the agent in the background using Redis for state."""
    structlog.contextvars.clear_contextvars()
    
    try:
        await initialize()
        
        # Use the async Redis client for all operations
        redis = _ASYNC_REDIS
        
        # Create unique keys for this run
        run_lock_key = f"agent_run_lock:{agent_run_id}"
        instance_active_key = f"agent_instance_active:{instance_id}"
        response_list_key = f"agent_responses:{agent_run_id}"
        response_channel = f"agent_responses:{agent_run_id}"
        global_control_channel = f"agent_control:{agent_run_id}"
        
        # Try to acquire lock
        lock_acquired = await redis.set(run_lock_key, instance_id, nx=True, ex=rc.REDIS_KEY_TTL)
        
        if not lock_acquired:
            existing_instance = await redis.get(run_lock_key)
            logger.warning(f"Agent run {agent_run_id} is already being processed by instance {existing_instance}")
            return
        
        # Double-check lock acquisition
        if not lock_acquired:
            lock_acquired = await redis.set(run_lock_key, instance_id, nx=True, ex=rc.REDIS_KEY_TTL)
            if not lock_acquired:
                logger.warning(f"Failed to acquire lock for agent run {agent_run_id}")
                return
        
        logger.info(f"Starting agent run {agent_run_id} with instance {instance_id}")
        
        # Set instance as active
        try:
            await redis.expire(instance_active_key, rc.REDIS_KEY_TTL)
        except Exception as e:
            logger.warning(f"Failed to set instance active key: {e}")
        
        # Create pubsub for real-time updates
        pubsub = await redis.pubsub()
        await pubsub.subscribe(response_channel)
        
        # Set instance as running
        await redis.set(instance_active_key, "running", ex=rc.REDIS_KEY_TTL)
        
        # Run the agent
        try:
            # Create thread manager
            thread_manager = ThreadManager()
            
            # Run the agent and collect responses
            responses = []
            pending_redis_operations = []
            
            async for response in run_agent(
                agent_run_id=agent_run_id,
                thread_id=thread_id,
                instance_id=instance_id,
                project_id=project_id,
                model_name=model_name,
                enable_thinking=enable_thinking,
                reasoning_effort=reasoning_effort,
                stream=stream,
                enable_context_manager=enable_context_manager,
                agent_config=agent_config,
                request_id=request_id,
            ):
                responses.append(response)
                response_json = json.dumps(response)
                
                # Store response in Redis list and publish notification
                pending_redis_operations.append(asyncio.create_task(redis.rpush(response_list_key, response_json)))
                pending_redis_operations.append(asyncio.create_task(redis.publish(response_channel, "new")))
            
            # Wait for all Redis operations to complete
            if pending_redis_operations:
                await asyncio.gather(*pending_redis_operations, return_exceptions=True)
            
            # Send completion message
            completion_message = {
                "type": "completion",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_responses": len(responses)
            }
            await redis.rpush(response_list_key, json.dumps(completion_message))
            await redis.publish(response_channel, "new") # Notify about the completion message
            
            logger.info(f"Agent run {agent_run_id} completed successfully with {len(responses)} responses")
            
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Get all responses so far
            all_responses_json = await redis.lrange(response_list_key, 0, -1)
            all_responses = [json.loads(r) for r in all_responses_json] if all_responses_json else []
            
            # Send error response
            error_response = {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "responses_so_far": len(all_responses)
            }
            await redis.rpush(response_list_key, json.dumps(error_response))
            await redis.publish(response_channel, "new")
            
            # Send control signal
            control_signal = {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await redis.publish(global_control_channel, json.dumps(control_signal))
            
            # Get final responses
            all_responses_json = await redis.lrange(response_list_key, 0, -1)
            all_responses = [json.loads(r) for r in all_responses_json] if all_responses_json else []
            
            logger.error(f"Agent run {agent_run_id} failed with {len(all_responses)} responses before error")
            
            # Send final error control signal
            await redis.publish(global_control_channel, "ERROR")
            
            raise e
        
        finally:
            # Clean up
            try:
                await pubsub.unsubscribe(response_channel)
                await pubsub.close()
            except Exception as e:
                logger.warning(f"Error closing pubsub: {e}")
            
            # Clean up Redis keys
            try:
                await redis.delete(run_lock_key)
            except Exception as e:
                logger.warning(f"Error deleting run lock key: {e}")
            
            # Set response list to expire
            REDIS_RESPONSE_LIST_TTL = 3600 * 24  # 24 hours
            try:
                await redis.expire(response_list_key, REDIS_RESPONSE_LIST_TTL)
            except Exception as e:
                logger.warning(f"Error setting response list expiry: {e}")
    
    except Exception as e:
        logger.error(f"Critical error in run_agent_background: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise e

def update_agent_run_status(agent_run_id: str, status: str, error_message: Optional[str] = None):
    """Update the status of an agent run."""
    try:
        # This is a sync function for compatibility
        # In practice, this should be called from the main API, not the worker
        logger.info(f"Agent run {agent_run_id} status updated to {status}")
        if error_message:
            logger.error(f"Agent run {agent_run_id} error: {error_message}")
    except Exception as e:
        logger.error(f"Error updating agent run status: {e}")

def _cleanup_redis_response_list(response_list_key: str):
    """Clean up Redis response list."""
    try:
        # This is a sync function for compatibility
        logger.info(f"Cleaning up Redis response list: {response_list_key}")
    except Exception as e:
        logger.error(f"Error cleaning up Redis response list: {e}")