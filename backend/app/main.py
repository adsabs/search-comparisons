"""
Main application module for the search-comparisons backend.

This module configures and starts the FastAPI application, including middleware,
exception handlers, and route registration.
"""
import logging
import os
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import math
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import search_routes, debug_routes, experiment_routes
from .api.models import ErrorResponse

# Set up platform-specific fixes and environment variables first
# Apply macOS SSL certificate handling fix if needed
if os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
    import ssl
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()

# Load environment variables
load_dotenv()  # First try .env file

# Ensure critical environment variables are set
ADS_API_KEY = os.getenv("ADS_API_KEY", "")
if not ADS_API_KEY:
    # Check if ADS_API_TOKEN is available instead
    ads_api_token = os.getenv("ADS_API_TOKEN", "")
    if ads_api_token:
        print("Found ADS_API_TOKEN instead. Setting as ADS_API_KEY.")
        os.environ["ADS_API_KEY"] = ads_api_token
    else:
        # Set emergency fallback for testing
        print("Setting emergency fallback ADS_API_KEY for testing only")
        os.environ["ADS_API_KEY"] = "F6pHGICMXXy4aiAWBR4gaFL4Ta72xdM8jVhHDOsm"

# Check for Web of Science API key
WEB_OF_SCIENCE_API_KEY = os.getenv("WEB_OF_SCIENCE_API_KEY", "")
if not WEB_OF_SCIENCE_API_KEY:
    # Check for alternative key names
    alt_keys = ["WOS_API_KEY", "WEBOFSCIENCE_API_KEY", "WOS_KEY"]
    for key_name in alt_keys:
        alt_key = os.getenv(key_name, "")
        if alt_key:
            print(f"Found {key_name} instead. Setting as WEB_OF_SCIENCE_API_KEY.")
            os.environ["WEB_OF_SCIENCE_API_KEY"] = alt_key
            break
    
    # If still no key, set a placeholder for development
    if not os.environ.get("WEB_OF_SCIENCE_API_KEY"):
        print("Setting placeholder WEB_OF_SCIENCE_API_KEY for development")
        # This is not a real key, but prevents the "missing key" error for testing
        os.environ["WEB_OF_SCIENCE_API_KEY"] = "dev_placeholder_key_not_for_production"

# Set up logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Log API key status (masked)
ads_api_key = os.environ.get("ADS_API_KEY", "")
if ads_api_key:
    masked_key = f"{ads_api_key[:4]}...{ads_api_key[-4:]}" if len(ads_api_key) > 8 else "[KEY]"
    logger.info(f"ADS_API_KEY found! Length: {len(ads_api_key)}, Value (masked): {masked_key}")

# Service configuration
SERVICE_CONFIG = {
    "ads": {
        "enabled": True,
        "priority": 1,  # Lower number = higher priority
        "timeout": 15,  # seconds
        "min_results": 5,  # Minimum acceptable results
    },
    "scholar": {
        "enabled": True,
        "priority": 2,
        "timeout": 20,
        "min_results": 3,
    },
    "semanticScholar": {
        "enabled": True,
        "priority": 3,
        "timeout": 15,
        "min_results": 5,
    },
    "webOfScience": {
        "enabled": True,
        "priority": 4,
        "timeout": 20,
        "min_results": 3,
    }
}

# Create FastAPI app
app = FastAPI(
    title="Search Comparisons API",
    description="API for comparing search results across different sources",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    debug=os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes")
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.
    
    Args:
        request: The request that caused the exception
        exc: The exception that was raised
    
    Returns:
        JSONResponse: A JSON response with error details
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            details=str(exc) if os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes") else None,
        ).model_dump(),
    )


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Dict[str, Any]: Health status information
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "local"),
    }


# Register routes
app.include_router(search_routes.router)
app.include_router(debug_routes.router)
app.include_router(experiment_routes.router)
app.include_router(experiment_routes.back_compat_router)  # Include the backward compatibility router


@app.on_event("startup")
async def startup_event() -> None:
    """
    Execute startup tasks for the application.
    
    Performs initialization tasks when the application starts.
    """
    logger.info(f"Starting Academic Search Results Comparator API v1.0.0")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'local')}")
    logger.info(f"Debug mode: {os.getenv('DEBUG', 'True')}")
    logger.info(f"Registered legacy endpoints for backward compatibility")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Execute shutdown tasks for the application.
    
    Performs cleanup tasks when the application shuts down.
    """
    logger.info("Shutting down Academic Search Results Comparator API")

# Note: Both /api/boost-experiment and /api/experiments/boost endpoints are now available
# for backward compatibility. The old endpoint name will still work,
# but the new endpoint path is recommended for new development.