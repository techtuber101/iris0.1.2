from typing import Optional, Union
import os
import asyncio
import logging
from urllib.parse import urlparse
import redis
import redis.asyncio as redis_async

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = float(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
HEALTH_CHECK_INTERVAL = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
MAX_INIT_RETRIES = int(os.getenv("REDIS_INIT_MAX_RETRIES", "5"))

def _normalize_url(url: str) -> str:
    if not url:
        # Return a default URL instead of raising an error
        return "redis://localhost:6379/0"
    # Upstash and most cloud Redis require TLS; prefer rediss when host looks like Upstash
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host.endswith(".upstash.io") and parsed.scheme != "rediss":
        # coerce to TLS; keep auth/db/port
        url = url.replace("redis://", "rediss://", 1)
    return url

def build_sync_client():
    try:
        url = _normalize_url(os.getenv("REDIS_URL", "").strip())
        # Parse URL manually for redis 5.2.1 compatibility
        parsed = urlparse(url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        password = parsed.password or ''
        db = int(parsed.path.lstrip('/')) if parsed.path.lstrip('/') else 0
        
        return redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=False,  # Keep as bytes for Dramatiq compatibility
            socket_timeout=DEFAULT_TIMEOUT,
            socket_connect_timeout=DEFAULT_TIMEOUT,
            socket_keepalive=True,
            health_check_interval=HEALTH_CHECK_INTERVAL,
            retry_on_timeout=True,
        )
    except Exception as e:
        log.error(f"Failed to build sync Redis client: {e}")
        # Return a dummy client that will fail gracefully
        return redis.Redis(host='localhost', port=6379, decode_responses=False)

def build_async_client():
    try:
        url = _normalize_url(os.getenv("REDIS_URL", "").strip())
        # Parse URL manually for redis 5.2.1 compatibility
        parsed = urlparse(url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        password = parsed.password or ''
        db = int(parsed.path.lstrip('/')) if parsed.path.lstrip('/') else 0
        
        return redis_async.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True,
            socket_timeout=DEFAULT_TIMEOUT,
            socket_connect_timeout=DEFAULT_TIMEOUT,
            socket_keepalive=True,
            health_check_interval=HEALTH_CHECK_INTERVAL,
            retry_on_timeout=True,
        )
    except Exception as e:
        log.error(f"Failed to build async Redis client: {e}")
        # Return a dummy client that will fail gracefully
        return redis_async.Redis(host='localhost', port=6379, decode_responses=True)

async def initialize_async_client(client: "redis_async.Redis"):
    # bounded exponential backoff: 0.5s → 1s → 2s → 4s → 8s
    delay = 0.5
    last_exc = None
    for attempt in range(1, MAX_INIT_RETRIES + 1):
        try:
            await asyncio.wait_for(client.ping(), timeout=DEFAULT_TIMEOUT + 1)
            log.info("Redis async client connected and ping OK.")
            return
        except Exception as e:
            last_exc = e
            log.warning("Redis PING failed (attempt %s/%s): %s", attempt, MAX_INIT_RETRIES, repr(e))
            await asyncio.sleep(delay)
            delay = min(delay * 2, 8.0)
    # Give a more actionable message
    raise RuntimeError(
        "Unable to connect to Redis after retries. "
        "Check REDIS_URL (scheme, host, port, username/password, TLS). "
        f"Last error: {last_exc}"
    )

# Legacy compatibility - keep existing interface
client: Optional[redis_async.Redis] = None
pool: Optional[redis_async.ConnectionPool] = None
_initialized = False
_init_lock = asyncio.Lock()

# Constants
REDIS_KEY_TTL = 3600 * 24  # 24 hour TTL as safety mechanism

def initialize():
    """Initialize Redis connection pool and client using environment variables."""
    global client, pool

    # Load environment variables if not already loaded
    from dotenv import load_dotenv
    load_dotenv()

    # Get Redis configuration
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_password = os.getenv("REDIS_PASSWORD", "")
    
    # Try using REDIS_URL first, fallback to individual parameters
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        # Use the new robust client builder
        try:
            client = build_async_client()
            log.info("Redis client initialized using REDIS_URL")
            return
        except Exception as e:
            log.error(f"Failed to initialize Redis with REDIS_URL: {e}")
            raise
    
    # Fallback to individual parameters
    pool = redis_async.ConnectionPool(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        decode_responses=True,
        socket_timeout=DEFAULT_TIMEOUT,
        socket_connect_timeout=DEFAULT_TIMEOUT,
        socket_keepalive=True,
        retry_on_timeout=True,
        health_check_interval=HEALTH_CHECK_INTERVAL,
        max_connections=20,
    )
    client = redis_async.Redis(connection_pool=pool)
    log.info(f"Redis client initialized: {redis_host}:{redis_port}")

async def initialize_async():
    """Initialize Redis connection asynchronously with retry logic."""
    global client, pool, _initialized
    
    async with _init_lock:
        if _initialized:
            return
            
        try:
            # Use the new robust client builder
            client = build_async_client()
            await initialize_async_client(client)
            _initialized = True
            log.info("Redis async client initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize Redis async client: {e}")
            raise

async def get_client():
    """Get the Redis client, initializing if necessary."""
    if not _initialized:
        await initialize_async()
    return client

# Redis operations
async def set(key: str, value: str, ex: int = None, nx: bool = False):
    redis = await get_client()
    return await redis.set(key, value, ex=ex, nx=nx)

async def get(key: str):
    redis = await get_client()
    return await redis.get(key)

async def delete(key: str):
    redis = await get_client()
    return await redis.delete(key)

async def publish(channel: str, message: str):
    redis = await get_client()
    return await redis.publish(channel, message)

async def create_pubsub():
    redis = await get_client()
    return redis.pubsub()

async def rpush(key: str, value: str):
    redis = await get_client()
    return await redis.rpush(key, value)

async def lrange(key: str, start: int, end: int):
    redis = await get_client()
    return await redis.lrange(key, start, end)

async def keys(pattern: str):
    redis = await get_client()
    return await redis.keys(pattern)

async def expire(key: str, time: int):
    redis = await get_client()
    return await redis.expire(key, time)

# Dedicated Redis clients for pub/sub operations
async def get_publisher():
    """Get a dedicated Redis client for publishing messages."""
    client = build_async_client()
    return client

async def get_subscriber():
    """Get a dedicated Redis client for subscribing to channels."""
    client = build_async_client()
    return client

async def publish_to_channel(channel: str, message: str):
    """Publish a message to a specific channel using a dedicated publisher."""
    publisher = await get_publisher()
    try:
        # Ensure message is properly encoded as UTF-8 string
        if isinstance(message, bytes):
            message = message.decode('utf-8')
        return await publisher.publish(channel, message)
    finally:
        await publisher.close()

async def create_dedicated_pubsub():
    """Create a dedicated pubsub connection for streaming."""
    subscriber = await get_subscriber()
    return subscriber.pubsub()