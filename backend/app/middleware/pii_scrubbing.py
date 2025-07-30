"""
PII (Personally Identifiable Information) scrubbing middleware.

This module provides middleware for detecting and scrubbing PII from 
HTTP requests and responses to prevent sensitive data from being
logged or stored inadvertently.
"""
import json
import re
from typing import Any, Dict, List, Optional, Set, Union
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class PIIScrubber:
    """
    PII detection and scrubbing utility class.
    """
    
    def __init__(self):
        # PII detection patterns
        self.pii_patterns = [
            # Email addresses
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[SCRUBBED:EMAIL]'),
            
            # Phone numbers (various formats)
            (re.compile(r'\b(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'), '[SCRUBBED:PHONE]'),
            (re.compile(r'\b\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'), '[SCRUBBED:PHONE]'),
            
            # Social Security Numbers
            (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SCRUBBED:SSN]'),
            (re.compile(r'\b\d{3}\s\d{2}\s\d{4}\b'), '[SCRUBBED:SSN]'),
            (re.compile(r'\b\d{9}\b'), '[SCRUBBED:SSN]'),
            
            # Credit card numbers
            (re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'), '[SCRUBBED:CREDIT_CARD]'),
            (re.compile(r'\b\d{13,19}\b'), '[SCRUBBED:CREDIT_CARD]'),
            
            # IP addresses (for privacy)
            (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), '[SCRUBBED:IP]'),
            
            # URLs with potentially sensitive query parameters
            (re.compile(r'[?&](email|phone|ssn|social|cc|card)=([^&\s]+)', re.IGNORECASE), r'\1=[SCRUBBED:PARAM]'),
            
            # API keys and tokens in values
            (re.compile(r'\b[a-zA-Z0-9]{32,}\b'), '[SCRUBBED:TOKEN]'),
            
            # Date of birth patterns
            (re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b'), '[SCRUBBED:DATE]'),
            (re.compile(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'), '[SCRUBBED:DATE]'),
        ]
        
        # Sensitive field names that should be scrubbed
        self.sensitive_fields: Set[str] = {
            'email', 'email_address', 'e_mail',
            'phone', 'phone_number', 'mobile', 'tel',
            'ssn', 'social_security_number', 'social',
            'credit_card', 'cc', 'card_number', 'card',
            'password', 'passwd', 'pwd',
            'token', 'api_key', 'secret', 'auth',
            'address', 'home_address', 'street_address',
            'zip', 'zipcode', 'postal_code',
            'date_of_birth', 'dob', 'birth_date',
            'drivers_license', 'license_number',
            'passport', 'passport_number',
        }
    
    def scrub_text(self, text: str) -> str:
        """
        Scrub PII from text content.
        
        Args:
            text: Text to scrub
            
        Returns:
            str: Text with PII scrubbed
        """
        if not isinstance(text, str):
            return text
            
        result = text
        for pattern, replacement in self.pii_patterns:
            result = pattern.sub(replacement, result)
        
        return result
    
    def scrub_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrub PII from dictionary data.
        
        Args:
            data: Dictionary to scrub
            
        Returns:
            Dict[str, Any]: Dictionary with PII scrubbed
        """
        if not isinstance(data, dict):
            return data
            
        scrubbed = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if field name indicates sensitive data
            if any(field in key_lower for field in self.sensitive_fields):
                scrubbed[key] = '[SCRUBBED:SENSITIVE_FIELD]'
            elif isinstance(value, str):
                scrubbed[key] = self.scrub_text(value)
            elif isinstance(value, dict):
                scrubbed[key] = self.scrub_dict(value)
            elif isinstance(value, list):
                scrubbed[key] = self.scrub_list(value)
            else:
                scrubbed[key] = value
                
        return scrubbed
    
    def scrub_list(self, data: List[Any]) -> List[Any]:
        """
        Scrub PII from list data.
        
        Args:
            data: List to scrub
            
        Returns:
            List[Any]: List with PII scrubbed
        """
        if not isinstance(data, list):
            return data
            
        scrubbed = []
        for item in data:
            if isinstance(item, str):
                scrubbed.append(self.scrub_text(item))
            elif isinstance(item, dict):
                scrubbed.append(self.scrub_dict(item))
            elif isinstance(item, list):
                scrubbed.append(self.scrub_list(item))
            else:
                scrubbed.append(item)
                
        return scrubbed
    
    def scrub_json(self, json_str: str) -> str:
        """
        Scrub PII from JSON string.
        
        Args:
            json_str: JSON string to scrub
            
        Returns:
            str: JSON string with PII scrubbed
        """
        try:
            data = json.loads(json_str)
            scrubbed_data = self.scrub_dict(data) if isinstance(data, dict) else self.scrub_list(data)
            return json.dumps(scrubbed_data)
        except (json.JSONDecodeError, TypeError):
            # If not valid JSON, scrub as text
            return self.scrub_text(json_str)


class PIIScrubbingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for scrubbing PII from HTTP requests and responses.
    
    This middleware intercepts HTTP requests and responses to detect and
    scrub personally identifiable information before it can be logged
    or processed by downstream components.
    """
    
    def __init__(self, app: ASGIApp, enabled: bool = True, scrub_responses: bool = False):
        """
        Initialize PII scrubbing middleware.
        
        Args:
            app: ASGI application
            enabled: Whether PII scrubbing is enabled
            scrub_responses: Whether to scrub response bodies (may impact performance)
        """
        super().__init__(app)
        self.enabled = enabled
        self.scrub_responses = scrub_responses
        self.scrubber = PIIScrubber()
        
        if not enabled:
            logger.info("PII scrubbing middleware is disabled")
        else:
            logger.info("PII scrubbing middleware is enabled")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and response through PII scrubbing.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
        """
        if not self.enabled:
            return await call_next(request)
        
        # Scrub request data
        scrubbed_request = await self._scrub_request(request)
        
        # Process request
        response = await call_next(scrubbed_request)
        
        # Scrub response data if enabled
        if self.scrub_responses:
            response = await self._scrub_response(response)
        
        return response
    
    async def _scrub_request(self, request: Request) -> Request:
        """
        Scrub PII from request data.
        
        Args:
            request: HTTP request
            
        Returns:
            Request: Request with PII scrubbed
        """
        # Note: In practice, we don't modify the actual request object
        # but ensure that any logging or processing downstream uses scrubbed data
        
        # Scrub query parameters
        if request.query_params:
            scrubbed_params = {}
            for key, value in request.query_params.items():
                if any(field in key.lower() for field in self.scrubber.sensitive_fields):
                    scrubbed_params[key] = '[SCRUBBED:SENSITIVE_PARAM]'
                else:
                    scrubbed_params[key] = self.scrubber.scrub_text(value)
            
            # Store scrubbed params for logging
            request.state.scrubbed_params = scrubbed_params
        
        # Scrub headers (for logging purposes)
        if request.headers:
            scrubbed_headers = {}
            for key, value in request.headers.items():
                key_lower = key.lower()
                if key_lower in ['authorization', 'x-api-key', 'cookie']:
                    scrubbed_headers[key] = '[SCRUBBED:SENSITIVE_HEADER]'
                else:
                    scrubbed_headers[key] = self.scrubber.scrub_text(value)
            
            # Store scrubbed headers for logging
            request.state.scrubbed_headers = scrubbed_headers
        
        return request
    
    async def _scrub_response(self, response: Response) -> Response:
        """
        Scrub PII from response data.
        
        Args:
            response: HTTP response
            
        Returns:
            Response: Response with PII scrubbed
        """
        # For now, we don't modify response content as it may break clients
        # But we can store scrubbed versions for logging
        
        # Scrub response headers
        if hasattr(response, 'headers'):
            scrubbed_headers = {}
            for key, value in response.headers.items():
                scrubbed_headers[key] = self.scrubber.scrub_text(value)
            
            # Store scrubbed headers for logging
            if hasattr(response, 'state'):
                response.state.scrubbed_headers = scrubbed_headers
        
        return response


def get_scrubbed_request_data(request: Request) -> Dict[str, Any]:
    """
    Get scrubbed request data for safe logging.
    
    Args:
        request: HTTP request
        
    Returns:
        Dict[str, Any]: Scrubbed request data
    """
    scrubber = PIIScrubber()
    
    data = {
        'method': request.method,
        'url': str(request.url),
        'path': request.url.path,
    }
    
    # Add scrubbed query parameters
    if hasattr(request.state, 'scrubbed_params'):
        data['query_params'] = request.state.scrubbed_params
    elif request.query_params:
        data['query_params'] = scrubber.scrub_dict(dict(request.query_params))
    
    # Add scrubbed headers
    if hasattr(request.state, 'scrubbed_headers'):
        data['headers'] = request.state.scrubbed_headers
    elif request.headers:
        headers = {}
        for key, value in request.headers.items():
            if key.lower() in ['authorization', 'x-api-key', 'cookie']:
                headers[key] = '[SCRUBBED:SENSITIVE_HEADER]'
            else:
                headers[key] = scrubber.scrub_text(value)
        data['headers'] = headers
    
    return data


def get_scrubbed_response_data(response: Response) -> Dict[str, Any]:
    """
    Get scrubbed response data for safe logging.
    
    Args:
        response: HTTP response
        
    Returns:
        Dict[str, Any]: Scrubbed response data
    """
    scrubber = PIIScrubber()
    
    data = {
        'status_code': response.status_code,
    }
    
    # Add scrubbed headers
    if hasattr(response, 'state') and hasattr(response.state, 'scrubbed_headers'):
        data['headers'] = response.state.scrubbed_headers
    elif hasattr(response, 'headers'):
        headers = {}
        for key, value in response.headers.items():
            headers[key] = scrubber.scrub_text(value)
        data['headers'] = headers
    
    return data
