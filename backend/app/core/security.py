"""
Security utilities and middleware for the search-comparisons application.

This module provides authentication, authorization, and security utilities.
"""
import os
import logging
from typing import List, Optional
from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import ipaddress

logger = logging.getLogger(__name__)

# Security configuration
DEBUG_ENDPOINTS_ENABLED = os.getenv("DEBUG_ENDPOINTS_ENABLED", "false").lower() in ("true", "1", "yes")
DEBUG_API_KEY = os.getenv("DEBUG_API_KEY", "")
DEBUG_ALLOWED_IPS = os.getenv("DEBUG_ALLOWED_IPS", "127.0.0.1,::1").split(",")

# Security helper
security = HTTPBearer(auto_error=False)


def is_ip_allowed(client_ip: str, allowed_ips: List[str]) -> bool:
    """
    Check if the client IP is in the allowed IP list.
    
    Args:
        client_ip: The client's IP address
        allowed_ips: List of allowed IP addresses/ranges
        
    Returns:
        bool: True if IP is allowed, False otherwise
    """
    try:
        client_addr = ipaddress.ip_address(client_ip)
        
        for allowed_ip in allowed_ips:
            allowed_ip = allowed_ip.strip()
            try:
                # Try as single IP first
                if client_addr == ipaddress.ip_address(allowed_ip):
                    return True
            except ValueError:
                # Try as network range
                try:
                    network = ipaddress.ip_network(allowed_ip, strict=False)
                    if client_addr in network:
                        return True
                except ValueError:
                    continue
                    
        return False
    except ValueError:
        logger.warning(f"Invalid client IP address: {client_ip}")
        return False


async def verify_debug_access(request: Request) -> bool:
    """
    Verify that the request has permission to access debug endpoints.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        bool: True if access is allowed
        
    Raises:
        HTTPException: If access is denied
    """
    # Check if debug endpoints are enabled
    if not DEBUG_ENDPOINTS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are disabled"
        )
    
    # Get client IP
    client_ip = None
    if request.client:
        client_ip = request.client.host
    
    # Check for forwarded IP headers (for reverse proxies)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        client_ip = real_ip.strip()
    
    if not client_ip:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to determine client IP address"
        )
    
    # Check IP whitelist
    if not is_ip_allowed(client_ip, DEBUG_ALLOWED_IPS):
        logger.warning(f"Debug endpoint access denied for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: IP address not in whitelist"
        )
    
    # Check API key if configured
    if DEBUG_API_KEY:
        credentials: Optional[HTTPAuthorizationCredentials] = await security(request)
        if not credentials or credentials.credentials != DEBUG_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing debug API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    logger.info(f"Debug endpoint access granted for IP: {client_ip}")
    return True


def get_allowed_origins() -> List[str]:
    """
    Get the list of allowed CORS origins.
    
    Returns:
        List[str]: List of allowed origins
    """
    # Default allowed origins
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:8000",
    ]
    
    # Add production domains
    production_origins = [
        "https://search.sjarmak.ai",
        "https://search-tool-api.onrender.com", 
        "https://search-tool.onrender.com"
    ]
    allowed_origins.extend(production_origins)
    
    # Add environment-specific origin if set
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url and frontend_url not in allowed_origins:
        allowed_origins.append(frontend_url)
    
    return allowed_origins


def get_allowed_hosts() -> List[str]:
    """
    Get the list of allowed hosts for TrustedHostMiddleware.
    
    Returns:
        List[str]: List of allowed host patterns
    """
    # Default allowed hosts
    allowed_hosts = [
        "localhost",
        "127.0.0.1",
        "::1",
    ]
    
    # Add production domains
    production_hosts = [
        "search.sjarmak.ai",
        "search-tool-api.onrender.com",
        "search-tool.onrender.com"
    ]
    allowed_hosts.extend(production_hosts)
    
    # Add environment-specific hosts if set
    if os.getenv("ENVIRONMENT") == "production":
        # Add any additional production hosts from environment
        extra_hosts = os.getenv("ALLOWED_HOSTS", "").split(",")
        for host in extra_hosts:
            host = host.strip()
            if host and host not in allowed_hosts:
                allowed_hosts.append(host)
    
    return allowed_hosts


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "frame-src 'none';"
        )
        
        # Only add HSTS in production with HTTPS
        if os.getenv("ENVIRONMENT") == "production" and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
