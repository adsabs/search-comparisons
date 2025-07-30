"""
Rate limiting configuration and decorators for API endpoints.

This module provides rate limiting functionality using SlowAPI with
different limits for different types of endpoints.
"""
import logging
from functools import wraps
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .logging import log_security_event, get_request_id

logger = logging.getLogger(__name__)

# Rate limiting configurations for different endpoint types
RATE_LIMITS = {
    # High-cost operations (search, LLM transforms)
    "search": "10/minute",
    "llm_transform": "5/minute",
    "experiment": "8/minute",
    
    # Medium-cost operations
    "api_moderate": "30/minute",
    "debug": "20/minute",
    
    # Low-cost operations
    "health": "60/minute",
    "info": "60/minute",
    
    # Bulk operations
    "batch": "3/minute",
    
    # Very restrictive for expensive operations
    "paper_lookup": "15/minute",
    "log_analysis": "5/minute",
}

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute", "2000/hour"]  # Global fallback limits
)


def get_client_identifier(request: Request) -> str:
    """
    Get client identifier for rate limiting.
    
    Uses IP address as primary identifier, with fallback to other headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client identifier
    """
    # Try to get real IP from headers (for reverse proxy setups)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    # Fallback to remote address
    return get_remote_address(request)


def create_rate_limit_handler():
    """
    Create custom rate limit exceeded handler with security logging.
    
    Returns:
        Callable: Rate limit handler function
    """
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        """
        Handle rate limit exceeded with security logging.
        
        Args:
            request: FastAPI request object
            exc: Rate limit exceeded exception
            
        Returns:
            HTTPException: Rate limit exceeded response
        """
        client_ip = get_client_identifier(request)
        request_id = get_request_id()
        
        # Log security event
        log_security_event(
            logger=logger,
            event_type="rate_limit_exceeded",
            details={
                "client_ip": client_ip,
                "path": str(request.url.path),
                "method": request.method,
                "user_agent": request.headers.get("User-Agent"),
                "limit_detail": str(exc.detail)
            },
            request_id=request_id
        )
        
        response = HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": getattr(exc, 'retry_after', 60),
                "request_id": request_id
            }
        )
        
        return response
    
    return rate_limit_exceeded_handler


# Rate limiting decorators for different endpoint types
def rate_limit_search(func):
    """Rate limiting decorator for search endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["search"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_llm(func):
    """Rate limiting decorator for LLM transform endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["llm_transform"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_experiment(func):
    """Rate limiting decorator for experiment endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["experiment"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_moderate(func):
    """Rate limiting decorator for moderate-cost endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["api_moderate"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_debug(func):
    """Rate limiting decorator for debug endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["debug"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_health(func):
    """Rate limiting decorator for health check endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["health"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_info(func):
    """Rate limiting decorator for info endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["info"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_batch(func):
    """Rate limiting decorator for batch operation endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["batch"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_paper_lookup(func):
    """Rate limiting decorator for paper lookup endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["paper_lookup"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_log_analysis(func):
    """Rate limiting decorator for log analysis endpoints."""
    @wraps(func)
    @limiter.limit(RATE_LIMITS["log_analysis"])
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def custom_rate_limit(limit: str):
    """
    Custom rate limiting decorator with specified limit.
    
    Args:
        limit: Rate limit string (e.g., "5/minute", "100/hour")
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        @limiter.limit(limit)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Middleware for request logging and monitoring
class RateLimitingMiddleware:
    """
    Middleware for rate limiting monitoring and logging.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """
        Process request through rate limiting middleware.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Log rate limiting status for monitoring
            client_ip = get_client_identifier(request)
            logger.debug(f"Processing request from {client_ip}: {request.method} {request.url.path}")
        
        await self.app(scope, receive, send)


def get_rate_limit_status(client_ip: str, endpoint_type: str) -> Dict[str, Any]:
    """
    Get current rate limit status for a client and endpoint type.
    
    Args:
        client_ip: Client IP address
        endpoint_type: Type of endpoint (search, llm_transform, etc.)
        
    Returns:
        Dict[str, Any]: Rate limit status information
    """
    try:
        # This would require accessing the limiter's internal state
        # For now, return basic configuration info
        return {
            "client_ip": client_ip,
            "endpoint_type": endpoint_type,
            "limit": RATE_LIMITS.get(endpoint_type, "unknown"),
            "configured": True
        }
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        return {
            "client_ip": client_ip,
            "endpoint_type": endpoint_type,
            "error": str(e),
            "configured": False
        }


# Export the limiter instance for use in main app
__all__ = [
    'limiter',
    'RATE_LIMITS',
    'rate_limit_search',
    'rate_limit_llm',
    'rate_limit_experiment',
    'rate_limit_moderate',
    'rate_limit_debug',
    'rate_limit_health',
    'rate_limit_info',
    'rate_limit_batch',
    'rate_limit_paper_lookup',
    'rate_limit_log_analysis',
    'custom_rate_limit',
    'create_rate_limit_handler',
    'RateLimitingMiddleware',
    'get_rate_limit_status'
]
