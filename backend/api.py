from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Response, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from core.services import redis_client_client
import sentry
from contextlib import asynccontextmanager
from core.agentpress.thread_manager import ThreadManager
from core.services.supabase import DBConnection
from datetime import datetime, timezone
from core.utils.config import config, EnvMode
from core.settings import settings
import asyncio
from core.utils.logger import logger, structlog
import time
from collections import OrderedDict
import os
import json
import sys

from pydantic import BaseModel
import uuid

from core import api as core_api
from core.utils.auth_utils import verify_and_get_user_id_from_jwt

from core.sandbox import api as sandbox_api
from core.billing_stub import router as billing_stub_router
from admin import users_admin
from core.services import transcription as transcription_api
import sys
from core.services import email_api
from core.triggers import api as triggers_api
from core.services import api_keys_api

# Conditionally import billing modules only if enabled
if settings.BILLING_ENABLED:
    from billing.api import router as billing_router
    from billing.admin import router as billing_admin_router
else:
    billing_router = None
    billing_admin_router = None


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

db = DBConnection()
instance_id = "single"

# Rate limiter state
ip_tracker = OrderedDict()
MAX_CONCURRENT_IPS = 25

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"=== STARTING UP FASTAPI APPLICATION ===")
    logger.info(f"Instance ID: {instance_id}")
    logger.info(f"Environment Mode: {config.ENV_MODE.value}")
    logger.info(f"Billing Enabled: {settings.BILLING_ENABLED}")
    logger.info(f"Working Directory: {os.getcwd()}")
    logger.info(f"Static Directory Exists: {os.path.exists(os.path.join(os.getcwd(), 'static'))}")
    
    try:
        await db.initialize()
        logger.info("Database connection initialized")
        
        core_api.initialize(
            db,
            instance_id
        )
        logger.info("Core API initialized")
        
        sandbox_api.initialize(db)
        logger.info("Sandbox API initialized")
        
        # Initialize Redis connection (optional)
        from core.services import redis_client_client
        try:
            await redis_client.initialize_async()
            logger.debug("Redis connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            # Continue without Redis - the application will handle Redis failures gracefully
        
        # Start background tasks
        # asyncio.create_task(core_api.restore_running_agent_runs())
        
        triggers_api.initialize(db)
        
        # Initialize optional modules
        try:
            from core.pipedream import api as pipedream_api
            pipedream_api.initialize(db)
            logger.info("Pipedream API initialized")
        except ImportError:
            logger.warning("Pipedream module not available")
        
        try:
            from core.credentials import api as credentials_api
            credentials_api.initialize(db)
            logger.info("Credentials API initialized")
        except ImportError:
            logger.warning("Credentials module not available")
        
        try:
            from core.templates import api as template_api
            template_api.initialize(db)
            logger.info("Templates API initialized")
        except ImportError:
            logger.warning("Templates module not available")
        
        try:
            from core.composio_integration import api as composio_api
            composio_api.initialize(db)
            logger.info("Composio API initialized")
        except ImportError:
            logger.warning("Composio module not available")
        
        logger.info("=== APPLICATION STARTUP COMPLETE ===")
        
        yield
        
        logger.info("=== SHUTTING DOWN APPLICATION ===")
        logger.debug("Cleaning up agent resources")
        await core_api.cleanup()
        
        try:
            logger.debug("Closing Redis connection")
            await redis_client.close()
            logger.debug("Redis connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")

        logger.debug("Disconnecting from database")
        await db.disconnect()
        logger.info("=== APPLICATION SHUTDOWN COMPLETE ===")
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise

app = FastAPI(lifespan=lifespan)

# Log all routes for debugging
@app.on_event("startup")
async def log_routes():
    """Log all registered routes for debugging purposes."""
    logger.warning("=== REGISTERED ROUTES ===")
    route_count = 0
    agents_routes = []
    composio_routes = []
    
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods) if route.methods else 'N/A'
            logger.warning(f"ROUTE {methods} {route.path}")
            route_count += 1
            
            # Track specific routes we're looking for
            if '/agents' in route.path:
                agents_routes.append(route.path)
            if '/composio' in route.path:
                composio_routes.append(route.path)
                
        elif hasattr(route, 'path'):
            logger.warning(f"ROUTE N/A {route.path}")
            route_count += 1
    
    logger.warning(f"=== END REGISTERED ROUTES ({route_count} total) ===")
    
    # Log specific findings
    logger.warning("=== ROUTE ANALYSIS ===")
    logger.warning(f"Agents routes found: {agents_routes}")
    logger.warning(f"Composio routes found: {composio_routes}")
    
    # Check for exact matches
    exact_matches = {
        '/agents': any(r.path == '/agents' for r in app.routes if hasattr(r, 'path')),
        '/api/agents': any(r.path == '/api/agents' for r in app.routes if hasattr(r, 'path')),
        '/composio/toolkits': any(r.path.startswith('/composio/toolkits') for r in app.routes if hasattr(r, 'path'))
    }
    logger.warning(f"Exact route matches: {exact_matches}")
    logger.warning("=== END ROUTE ANALYSIS ===")
    
    # Log static files info
    static_dir = os.path.join(os.getcwd(), "static")
    if os.path.exists(static_dir):
        logger.info(f"Static directory found: {static_dir}")
        toolkits_dir = os.path.join(static_dir, "toolkits")
        if os.path.exists(toolkits_dir):
            files = os.listdir(toolkits_dir)
            logger.info(f"Toolkit icons available: {files}")
        else:
            logger.warning(f"Toolkits directory not found: {toolkits_dir}")
    else:
        logger.warning(f"Static directory not found: {static_dir}")

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    structlog.contextvars.clear_contextvars()

    request_id = str(uuid.uuid4())
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    query_params = str(request.query_params)

    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        client_ip=client_ip,
        method=method,
        path=path,
        query_params=query_params
    )

    # Log the incoming request
    logger.debug(f"Request started: {method} {path} from {client_ip} | Query: {query_params}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.debug(f"Request completed: {method} {path} | Status: {response.status_code} | Time: {process_time:.2f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {method} {path} | Error: {str(e)} | Time: {process_time:.2f}s")
        raise

# Define allowed origins based on environment
allowed_origins = [
    "https://irisvision.ai",
    "https://www.irisvision.ai", 
    "https://staging.irisvision.ai",
    "https://irisproduction.vercel.app",
    "https://irisproduction-git-main-hahaicarus-projects.vercel.app",
    "http://localhost:3000"
]
allow_origin_regex = None

# Add Vercel preview URLs for staging/development
if config.ENV_MODE == EnvMode.STAGING:
    allow_origin_regex = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a main API router
api_router = APIRouter()

# Include core API routers
api_router.include_router(core_api.router)
api_router.include_router(sandbox_api.router)
api_router.include_router(api_keys_api.router)
api_router.include_router(users_admin.router)

# Include optional modules
try:
    from core.mcp_module import api as mcp_api
    api_router.include_router(mcp_api.router)
except ImportError:
    logger.warning("MCP module not available")

try:
    from core.credentials import api as credentials_api
    api_router.include_router(credentials_api.router, prefix="/secure-mcp")
except ImportError:
    logger.warning("Credentials module not available")

try:
    from core.templates import api as template_api
    api_router.include_router(template_api.router, prefix="/templates")
except ImportError:
    logger.warning("Templates module not available")

api_router.include_router(transcription_api.router)
api_router.include_router(email_api.router)

try:
    from core.knowledge_base import api as knowledge_base_api
    api_router.include_router(knowledge_base_api.router)
except ImportError:
    logger.warning("Knowledge base module not available")

api_router.include_router(triggers_api.router)

try:
    from core.pipedream import api as pipedream_api
    api_router.include_router(pipedream_api.router)
except ImportError:
    logger.warning("Pipedream module not available")

try:
    from core.admin import api as admin_api
    api_router.include_router(admin_api.router)
except ImportError:
    logger.warning("Admin module not available")

try:
    from core.composio_integration import api as composio_api
    # Mount Composio router directly on app (not under /api prefix)
    app.include_router(composio_api.router)
    logger.info("Composio API mounted directly on app")
except ImportError:
    logger.warning("Composio module not available")

try:
    from core.google.google_slides_api import router as google_slides_router
    api_router.include_router(google_slides_router)
except ImportError:
    logger.warning("Google Slides module not available")

@api_router.get("/health")
async def health_check():
    logger.debug("Health check endpoint called")
    return {
        "status": "ok", 
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "instance_id": instance_id
    }

@api_router.get("/health-docker")
async def health_check():
    logger.debug("Health docker check endpoint called")
    try:
        client = await redis_client.get_client()
        await client.ping()
        db = DBConnection()
        await db.initialize()
        db_client = await db.client
        await db_client.table("threads").select("thread_id").limit(1).execute()
        logger.debug("Health docker check complete")
        return {
            "status": "ok", 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "instance_id": instance_id
        }
    except Exception as e:
        logger.error(f"Failed health docker check: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


# Add root endpoint to handle Railway health checks
@app.get("/")
async def root():
    return {"message": "Iris API is running", "status": "ok"}

# Add health endpoint at root level for Railway health checks
@app.get("/health")
async def health():
    return {"status": "ok", "message": "Iris API is healthy"}

# Add a debug endpoint to test routing
@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to list all available routes."""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if route.methods else ['N/A']
            routes.append({
                "path": route.path,
                "methods": methods,
                "name": getattr(route, 'name', 'unnamed')
            })
    return {
        "total_routes": len(routes),
        "routes": routes,
        "important_routes": {
            "agents": any(r["path"].startswith("/agents") for r in routes),
            "threads": any(r["path"].startswith("/threads") for r in routes),
            "composio_toolkits": any(r["path"].startswith("/composio/toolkits") for r in routes),
            "billing": any(r["path"].startswith("/billing") for r in routes)
        }
    }

# Add a test endpoint to check auth behavior
@app.get("/debug/test-auth")
async def test_auth():
    """Test endpoint to check if auth middleware returns 404 or 401."""
    return {"message": "This endpoint works without auth", "status": "ok"}

@app.get("/debug/test-auth-protected")
async def test_auth_protected(user_id: str = Depends(verify_and_get_user_id_from_jwt)):
    """Test endpoint that requires auth."""
    return {"message": "This endpoint requires auth", "user_id": user_id, "status": "ok"}

# Add comprehensive worker debugging endpoints
@app.get("/debug/worker-status")
async def debug_worker_status():
    """Debug endpoint to check worker status and Redis connection."""
    import os
    import psutil
    from core.services import redis_client_client
    import dramatiq
    from dramatiq.brokers.redis import RedisBroker
    
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "python_version": sys.version,
            "working_directory": os.getcwd(),
            "cpu_count": psutil.cpu_count(),
            "memory_usage": psutil.virtual_memory().percent,
        },
        "environment": {
            "PORT": os.getenv("PORT"),
            "REDIS_URL": "***" if os.getenv("REDIS_URL") else None,
            "REDIS_HOST": os.getenv("REDIS_HOST"),
            "REDIS_PORT": os.getenv("REDIS_PORT"),
            "REDIS_PASSWORD": "***" if os.getenv("REDIS_PASSWORD") else None,
        },
        "redis_connection": {},
        "dramatiq_broker": {},
        "worker_processes": [],
        "errors": []
    }
    
    # Check Redis connection
    try:
        await redis_client.initialize_async()
        client = await redis_client.get_client()
        await client.ping()
        debug_info["redis_connection"] = {
            "status": "connected",
            "message": "Redis connection successful"
        }
    except Exception as e:
        debug_info["redis_connection"]["status"] = "error"
        debug_info["redis_connection"]["error"] = str(e)
        debug_info["errors"].append(f"Redis connection failed: {e}")
    
    # Check Dramatiq broker
    try:
        broker = dramatiq.get_broker()
        debug_info["dramatiq_broker"] = {
            "type": type(broker).__name__,
            "is_connected": hasattr(broker, 'client') and broker.client is not None,
        }
        
        # Try to get queue info
        if hasattr(broker, 'get_declared_queues'):
            queues = broker.get_declared_queues()
            debug_info["dramatiq_broker"]["queues"] = list(queues)
    except Exception as e:
        debug_info["dramatiq_broker"]["error"] = str(e)
        debug_info["errors"].append(f"Dramatiq broker error: {e}")
    
    # Check for worker processes
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'dramatiq' in cmdline or 'run_agent_background' in cmdline:
                    debug_info["worker_processes"].append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cmdline": cmdline,
                        "status": proc.status(),
                        "cpu_percent": proc.cpu_percent(),
                        "memory_percent": proc.memory_percent(),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        debug_info["errors"].append(f"Process check failed: {e}")
    
    return debug_info

@app.get("/debug/test-worker")
async def debug_test_worker():
    """Test if worker can process a simple task."""
    import dramatiq
    import uuid
    from core.services import redis_client_client
    
    test_key = f"worker_test_{uuid.uuid4().hex}"
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "test_key": test_key,
        "status": "unknown",
        "errors": []
    }
    
    try:
        # Send a test task
        broker = dramatiq.get_broker()
        
        # Create a simple test task
        @dramatiq.actor
        def test_worker_task(key: str):
            import asyncio
            from core.services import redis_client_client
            
            async def _test():
                await redis_client.initialize_async()
                await redis_client.set(key, "worker_test_passed", ex=60)
                await redis_client.close()
            
            asyncio.run(_test())
        
        # Send the task
        logger.info(f"🧪 Sending test task: {test_key}")
        test_worker_task.send(test_key)
        debug_info["status"] = "task_sent"
        
        # Wait for result
        await redis_client.initialize_async()
        for i in range(10):  # Wait up to 10 seconds
            result = await redis_client.get(test_key)
            if result:
                debug_info["status"] = "success"
                debug_info["result"] = result
                await redis_client.delete(test_key)
                logger.info(f"✅ Test task completed: {test_key}")
                break
            await asyncio.sleep(1)
        
        if debug_info["status"] == "task_sent":
            debug_info["status"] = "timeout"
            debug_info["errors"].append("Worker did not process task within 10 seconds")
            logger.warning(f"⏰ Test task timeout: {test_key}")
        
    except Exception as e:
        debug_info["status"] = "error"
        debug_info["errors"].append(str(e))
        logger.error(f"❌ Test task failed: {e}")
    
    return debug_info

@app.get("/debug/queue-status")
async def debug_queue_status():
    """Debug endpoint to check queue status and Redis connection."""
    import dramatiq
    from core.services import redis_client_client
    
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "redis_status": {},
        "dramatiq_status": {},
        "queue_info": {},
        "errors": []
    }
    
    try:
        # Check Redis connection
        await redis_client.initialize_async()
        client = await redis_client.get_client()
        # Test Redis connection with a simple ping
        await client.ping()
        debug_info["redis_status"] = {
            "connected": True,
            "message": "Redis connection successful"
        }
        
        # Check Dramatiq broker
        broker = dramatiq.get_broker()
        debug_info["dramatiq_status"] = {
            "broker_type": type(broker).__name__,
            "is_connected": hasattr(broker, 'client') and broker.client is not None,
        }
        
        # Check queue info
        if hasattr(broker, 'get_declared_queues'):
            queues = broker.get_declared_queues()
            debug_info["queue_info"]["declared_queues"] = list(queues)
        
        # Check if we can send a message
        try:
            from run_agent_background import check_health
            test_key = f"queue_test_{uuid.uuid4().hex}"
            check_health.send(test_key)
            debug_info["queue_info"]["can_send"] = True
            logger.info(f"✅ Queue test message sent: {test_key}")
        except Exception as e:
            debug_info["queue_info"]["can_send"] = False
            debug_info["errors"].append(f"Cannot send to queue: {e}")
            logger.error(f"❌ Queue send failed: {e}")
        
    except Exception as e:
        debug_info["redis_status"]["connected"] = False
        debug_info["redis_status"]["error"] = str(e)
        debug_info["errors"].append(f"Redis connection failed: {e}")
        logger.error(f"❌ Redis connection failed: {e}")
    
    return debug_info

@app.get("/debug/llm")
async def debug_llm():
    """Debug endpoint to test LLM streaming directly."""
    import os
    from core.ai_models import model_manager
    
    async def gen():
        try:
            yield "event: open\ndata: ok\n\n"
            yield f"data: {json.dumps({'type': 'status', 'status': 'testing_llm', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Get default model
            default_model = os.getenv("DEFAULT_MODEL", "gemini/gemini-2.5-flash")
            logger.info(f"🧪 Testing LLM streaming with model: {default_model}")
            
            # Test with a simple prompt
            test_prompt = "Say 'Hello, this is a test!' and nothing else."
            
            try:
                # Import the LLM service
                from core.services.llm import make_llm_api_call
                
                # Test streaming using the proper LLM service
                logger.info(f"🚀 Starting LLM stream test...")
                first_token = True
                token_count = 0
                
                # Use the proper LLM service for streaming
                stream = await make_llm_api_call(
                    messages=[{"role": "user", "content": test_prompt}],
                    model_name=default_model,
                    max_tokens=50,
                    temperature=0.1,
                    stream=True
                )
                
                async for chunk in stream:
                    if first_token:
                        # Extract content from LiteLLM chunk format
                        content = ""
                        if hasattr(chunk, 'choices') and chunk.choices:
                            delta = chunk.choices[0].delta
                            content = getattr(delta, 'content', '') or ""
                        logger.info(f"🎯 FIRST LLM TOKEN received: {content[:50]}...")
                        first_token = False
                    
                    token_count += 1
                    
                    # Extract content from chunk
                    content = ""
                    if hasattr(chunk, 'choices') and chunk.choices:
                        delta = chunk.choices[0].delta
                        content = getattr(delta, 'content', '') or ""
                    
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content, 'token_count': token_count})}\n\n"
                
                logger.info(f"✅ LLM streaming completed successfully with {token_count} tokens")
                yield f"data: {json.dumps({'type': 'completion', 'token_count': token_count, 'status': 'success'})}\n\n"
                
            except Exception as e:
                logger.error(f"❌ LLM streaming failed: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': f'LLM streaming failed: {str(e)}'})}\n\n"
            
        except Exception as e:
            logger.error(f"❌ Debug LLM endpoint failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': f'Debug endpoint failed: {str(e)}'})}\n\n"
        finally:
            yield "event: done\ndata: {}\n\n"
    
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/debug/test-agents-protected")
async def test_agents_protected(user_id: str = Depends(verify_and_get_user_id_from_jwt)):
    """Test endpoint that mimics agents endpoint auth behavior."""
    return {"message": "Agents routing test with auth", "user_id": user_id, "status": "ok"}

# Mount static files for Composio toolkit icons
static_dir = os.path.join(os.getcwd(), "static")
if os.path.exists(static_dir):
    toolkits_dir = os.path.join(static_dir, "toolkits")
    if os.path.exists(toolkits_dir):
        app.mount("/composio/toolkits", StaticFiles(directory=toolkits_dir), name="toolkits")
        logger.info(f"Mounted static files from {toolkits_dir}")
        # List available files
        files = os.listdir(toolkits_dir)
        logger.info(f"Available toolkit icons: {files}")
    else:
        logger.warning(f"Toolkits directory not found: {toolkits_dir}")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Include billing router (real or stub)
if settings.BILLING_ENABLED and billing_router:
    app.include_router(billing_router)
    if billing_admin_router:
        app.include_router(billing_admin_router)
    logger.info("Billing enabled - using real billing router")
else:
    app.include_router(billing_stub_router)
    logger.info("Billing disabled - using stub billing router")

# Include main API router
app.include_router(api_router, prefix="/api")
# Also include core API routes at root level for backward compatibility
app.include_router(core_api.router)

# Routes are logged in the startup event handler above


if __name__ == "__main__":
    import uvicorn

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    workers = 4
    port = int(os.getenv("PORT", 8000))

    logger.debug(f"Starting server on 0.0.0.0:{port} with {workers} workers")
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        loop="asyncio",
        timeout_keep_alive=75,  # Keep connections alive for 75 seconds
        proxy_headers=True,     # Handle proxy headers properly
        forwarded_allow_ips="*" # Allow forwarded IPs from proxies
    )