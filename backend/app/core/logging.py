"""
Secure logging configuration with redaction filters for sensitive data.

This module provides structured logging with automatic redaction of API keys,
passwords, tokens, and other sensitive information.
"""
import logging
import re
import uuid
from typing import Any, Dict, Optional, Set
from contextvars import ContextVar

# Context variable for request ID correlation
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

class SensitiveDataRedactionFilter(logging.Filter):
    """
    Logging filter that redacts sensitive data from log messages.
    
    Automatically detects and redacts:
    - API keys and tokens
    - Passwords
    - Email addresses
    - Credit card numbers
    - Phone numbers
    - URLs with credentials
    - Query parameters with sensitive values
    """
    
    def __init__(self):
        super().__init__()
        
        # Patterns for sensitive data detection
        self.redaction_patterns = [
            # API keys and tokens (various formats)
            (re.compile(r'\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{8,})["\']?', re.IGNORECASE), '[REDACTED:API_KEY]'),
            (re.compile(r'\b(?:bearer\s+)?([a-zA-Z0-9_\-]{20,})\b', re.IGNORECASE), '[REDACTED:TOKEN]'),
            
            # Common API key patterns
            (re.compile(r'\b[a-f0-9]{32}\b'), '[REDACTED:MD5_HASH]'),
            (re.compile(r'\b[a-f0-9]{40}\b'), '[REDACTED:SHA1_HASH]'),
            (re.compile(r'\b[a-zA-Z0-9]{64}\b'), '[REDACTED:LONG_TOKEN]'),
            
            # ADS API key pattern (specific to our app)
            (re.compile(r'\bADS_API_KEY["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]+)["\']?', re.IGNORECASE), 'ADS_API_KEY=[REDACTED:ADS_KEY]'),
            
            # Web of Science API key
            (re.compile(r'\bWEB_OF_SCIENCE_API_KEY["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]+)["\']?', re.IGNORECASE), 'WEB_OF_SCIENCE_API_KEY=[REDACTED:WOS_KEY]'),
            
            # Password patterns
            (re.compile(r'\bpassword\s*[:=]\s*["\']?([^"\s]+)["\']?', re.IGNORECASE), 'password=[REDACTED:PASSWORD]'),
            
            # Email addresses
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[REDACTED:EMAIL]'),
            
            # Credit card numbers
            (re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'), '[REDACTED:CREDIT_CARD]'),
            
            # Phone numbers
            (re.compile(r'\b\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'), '[REDACTED:PHONE]'),
            
            # URLs with credentials
            (re.compile(r'://([^:]+):([^@]+)@'), '://[REDACTED:USER]:[REDACTED:PASS]@'),
            
            # Query parameters that might contain sensitive data
            (re.compile(r'[?&](token|key|secret|password|auth)=([^&\s]+)', re.IGNORECASE), r'\1=[REDACTED:QUERY_PARAM]'),
        ]
        
        # Additional sensitive field names to redact
        self.sensitive_fields: Set[str] = {
            'api_key', 'token', 'secret', 'password', 'auth_token',
            'authorization', 'x-api-key', 'access_token', 'refresh_token',
            'client_secret', 'private_key', 'ssh_key', 'gpg_key'
        }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record by redacting sensitive information.
        
        Args:
            record: The log record to filter
            
        Returns:
            bool: Always True (we don't drop records, just redact them)
        """
        # Redact message
        if hasattr(record, 'msg') and record.msg:
            record.msg = self._redact_sensitive_data(str(record.msg))
        
        # Redact args if present
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._redact_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            record.request_id = request_id
        
        return True
    
    def _redact_sensitive_data(self, text: str) -> str:
        """
        Apply redaction patterns to text.
        
        Args:
            text: Text to redact
            
        Returns:
            str: Text with sensitive data redacted
        """
        if not isinstance(text, str):
            return text
            
        result = text
        for pattern, replacement in self.redaction_patterns:
            result = pattern.sub(replacement, result)
        
        return result


class StructuredFormatter(logging.Formatter):
    """
    Structured JSON formatter for logs with request correlation.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON.
        
        Args:
            record: The log record to format
            
        Returns:
            str: Formatted log message
        """
        # Get request ID from context
        request_id = getattr(record, 'request_id', request_id_var.get())
        
        # Create structured log entry
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request ID if available
        if request_id:
            log_entry['request_id'] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info', 'request_id'):
                log_entry[key] = value
        
        return str(log_entry)


def setup_secure_logging(app_name: str = "search-comparisons", 
                        log_level: str = "INFO",
                        log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up secure logging with redaction filters.
    
    Args:
        app_name: Name of the application
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create redaction filter
    redaction_filter = SensitiveDataRedactionFilter()
    
    # Create structured formatter
    structured_formatter = StructuredFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with redaction
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.addFilter(redaction_filter)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    root_logger.addHandler(console_handler)
    
    # File handler with structured logging if log file specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.addFilter(redaction_filter)
        file_handler.setFormatter(structured_formatter)
        root_logger.addHandler(file_handler)
    
    # Get application logger
    app_logger = logging.getLogger(app_name)
    
    return app_logger


def get_request_id() -> str:
    """
    Get or generate a request ID for log correlation.
    
    Returns:
        str: Request ID
    """
    request_id = request_id_var.get()
    if not request_id:
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
    return request_id


def set_request_id(request_id: str) -> None:
    """
    Set the request ID for log correlation.
    
    Args:
        request_id: The request ID to set
    """
    request_id_var.set(request_id)


def clear_request_id() -> None:
    """
    Clear the request ID from context.
    """
    request_id_var.set(None)


# Security-focused logging utilities
def log_security_event(logger: logging.Logger, event_type: str, details: Dict[str, Any], 
                      request_id: Optional[str] = None) -> None:
    """
    Log a security-related event with structured data.
    
    Args:
        logger: Logger instance
        event_type: Type of security event (e.g., 'rate_limit_exceeded', 'auth_failure')
        details: Event details
        request_id: Optional request ID
    """
    if request_id:
        set_request_id(request_id)
    
    logger.warning(f"SECURITY_EVENT: {event_type}", extra={
        'security_event': True,
        'event_type': event_type,
        'details': details
    })


def log_api_access(logger: logging.Logger, method: str, path: str, status_code: int,
                   response_time_ms: float, client_ip: str, user_agent: str = None,
                   request_id: str = None) -> None:
    """
    Log API access with structured data.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        client_ip: Client IP address
        user_agent: User agent string
        request_id: Optional request ID
    """
    if request_id:
        set_request_id(request_id)
    
    logger.info(f"API_ACCESS: {method} {path} {status_code}", extra={
        'api_access': True,
        'method': method,
        'path': path,
        'status_code': status_code,
        'response_time_ms': response_time_ms,
        'client_ip': client_ip,
        'user_agent': user_agent
    })
