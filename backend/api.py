from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Response, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from core.services import redis
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
        from core.services import redis
        try:
            await redis.initialize_async()
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
            await redis.close()
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
        client = await redis.get_client()
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

# Add a test agents endpoint to verify routing
@app.get("/debug/test-agents")
async def test_agents():
    """Test endpoint to verify agents routing works."""
    return {"message": "Agents routing test", "status": "ok", "note": "This should work without /api prefix"}

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
app.include_router(transcription_api.router)

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
        loop="asyncio"
    )