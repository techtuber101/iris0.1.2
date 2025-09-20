"""
Centralized settings module for the FastAPI application.

This module provides a centralized way to access configuration settings and
environment variables across the application. It supports different environment
modes and provides validation for required values.

Usage:
    from core.settings import settings
    
    # Access configuration values
    billing_enabled = settings.BILLING_ENABLED
    redis_url = settings.REDIS_URL
"""

import os
from enum import Enum
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class EnvMode(Enum):
    """Environment mode enumeration."""
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings:
    """
    Centralized settings for the FastAPI application.
    
    This class loads environment variables and provides type checking and validation.
    Default values can be specified for optional configuration items.
    """
    
    # Environment mode
    ENV_MODE: EnvMode = EnvMode.LOCAL
    
    # Feature flags
    BILLING_ENABLED: bool = False
    
    # Supabase configuration (optional - don't crash if missing)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    
    # Redis configuration (optional - don't crash if missing)
    REDIS_URL: Optional[str] = None
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = True
    
    # LLM API keys (optional)
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None
    MORPH_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # Stripe configuration (optional - billing disabled by default)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Other API keys (optional)
    TAVILY_API_KEY: Optional[str] = None
    RAPID_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    CLOUDFLARE_API_TOKEN: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    
    # Composio configuration (optional)
    COMPOSIO_API_KEY: Optional[str] = None
    COMPOSIO_WEBHOOK_SECRET: Optional[str] = None
    COMPOSIO_API_BASE: str = "https://backend.composio.dev"
    
    # Sandbox configuration
    SANDBOX_IMAGE_NAME: str = "kortix/suna:0.1.3.16"
    SANDBOX_SNAPSHOT_NAME: str = "kortix/suna:0.1.3.16"
    SANDBOX_ENTRYPOINT: str = "/usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf"
    
    # Admin API key for server-side operations
    KORTIX_ADMIN_API_KEY: Optional[str] = None
    
    # API Keys system configuration
    API_KEY_SECRET: str = "default-secret-key-change-in-production"
    API_KEY_LAST_USED_THROTTLE_SECONDS: int = 900
    
    def __init__(self):
        """Initialize settings by loading from environment variables."""
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        # Set environment mode first
        env_mode_str = os.getenv("ENV_MODE", EnvMode.LOCAL.value)
        try:
            self.ENV_MODE = EnvMode(env_mode_str.lower())
        except ValueError:
            logger.warning(f"Invalid ENV_MODE: {env_mode_str}, defaulting to LOCAL")
            self.ENV_MODE = EnvMode.LOCAL
            
        logger.debug(f"Environment mode: {self.ENV_MODE.value}")
        
        # Load configuration from environment variables
        self._load_from_env()
        
        # Perform validation
        self._validate()
    
    def _load_from_env(self):
        """Load configuration values from environment variables."""
        # Feature flags
        self.BILLING_ENABLED = os.getenv("BILLING_ENABLED", "false").lower() == "true"
        
        # Supabase configuration (optional)
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
        
        # Redis configuration (optional)
        self.REDIS_URL = os.getenv("REDIS_URL")
        self.REDIS_HOST = os.getenv("REDIS_HOST")
        redis_port = os.getenv("REDIS_PORT")
        if redis_port:
            try:
                self.REDIS_PORT = int(redis_port)
            except ValueError:
                logger.warning(f"Invalid REDIS_PORT: {redis_port}, using default 6379")
        self.REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
        self.REDIS_SSL = os.getenv("REDIS_SSL", "true").lower() == "true"
        
        # LLM API keys (optional)
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
        self.XAI_API_KEY = os.getenv("XAI_API_KEY")
        self.MORPH_API_KEY = os.getenv("MORPH_API_KEY")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        # Stripe configuration (optional)
        self.STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
        self.STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        # Other API keys (optional)
        self.TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
        self.RAPID_API_KEY = os.getenv("RAPID_API_KEY")
        self.SERPER_API_KEY = os.getenv("SERPER_API_KEY")
        self.CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
        self.FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
        
        # Composio configuration (optional)
        self.COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
        self.COMPOSIO_WEBHOOK_SECRET = os.getenv("COMPOSIO_WEBHOOK_SECRET")
        composio_base = os.getenv("COMPOSIO_API_BASE")
        if composio_base:
            self.COMPOSIO_API_BASE = composio_base
        
        # Admin API key
        self.KORTIX_ADMIN_API_KEY = os.getenv("KORTIX_ADMIN_API_KEY")
        
        # API Keys system configuration
        api_key_secret = os.getenv("API_KEY_SECRET")
        if api_key_secret:
            self.API_KEY_SECRET = api_key_secret
        
        api_key_throttle = os.getenv("API_KEY_LAST_USED_THROTTLE_SECONDS")
        if api_key_throttle:
            try:
                self.API_KEY_LAST_USED_THROTTLE_SECONDS = int(api_key_throttle)
            except ValueError:
                logger.warning(f"Invalid API_KEY_LAST_USED_THROTTLE_SECONDS: {api_key_throttle}, using default 900")
    
    def _validate(self):
        """Validate configuration based on environment mode."""
        # In production, we might want to require certain settings
        if self.ENV_MODE == EnvMode.PRODUCTION:
            # Add any production-specific validation here
            pass
        
        logger.info(f"Settings initialized - Billing enabled: {self.BILLING_ENABLED}")
        logger.info(f"Settings initialized - Redis URL: {'configured' if self.REDIS_URL else 'not configured'}")
        logger.info(f"Settings initialized - Supabase URL: {'configured' if self.SUPABASE_URL else 'not configured'}")
    
    def get_redis_kwargs(self) -> Dict[str, Any]:
        """Get Redis connection kwargs with proper SSL handling."""
        kwargs = {"decode_responses": True}
        
        if self.REDIS_URL and self.REDIS_URL.startswith("rediss://"):
            kwargs["ssl"] = True
        
        return kwargs
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value with an optional default."""
        return getattr(self, key, default)
    
    def as_dict(self) -> Dict[str, Any]:
        """Return settings as a dictionary."""
        return {
            key: getattr(self, key) 
            for key in dir(self)
            if not key.startswith('_') and not callable(getattr(self, key))
        }

# Create a singleton instance
settings = Settings()
