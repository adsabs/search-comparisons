"""
SciX Development service module.

This module provides a placeholder implementation for the SciX Development
search engine endpoint. It's designed to be easily replaceable with the
actual SciX Development API implementation once available.
"""
import logging
import os
from typing import List, Optional

from ..api.models import SearchResult

logger = logging.getLogger(__name__)


async def get_scix_dev_results(
    query: str,
    fields: Optional[List[str]] = None,
    num_results: int = 20
) -> List[SearchResult]:
    """
    Get search results from SciX Development API.
    
    This is currently a placeholder implementation that returns empty results
    until the actual SciX Development API endpoint is available.
    
    Args:
        query: Search query string
        fields: List of fields to retrieve (optional)
        num_results: Maximum number of results to return
        
    Returns:
        List[SearchResult]: List of search results from SciX Development API
    """
    logger.info(f"[SciXDev] Query: '{query}', num_results: {num_results}")
    
    # Check if development endpoint is configured
    dev_endpoint = os.getenv('SCIX_DEV_ENDPOINT')
    if not dev_endpoint:
        logger.warning("SCIX_DEV_ENDPOINT environment variable not set - returning empty results")
        return []
    
    # TODO: Replace this placeholder with actual API call to SciX Development endpoint
    # For now, return empty results to allow testing of the UI integration
    logger.info("SciX Development API not yet implemented - returning empty results")
    return []


async def get_scix_dev_paper_details(doi: str) -> dict:
    """
    Get detailed paper information from SciX Development API by DOI.
    
    Args:
        doi: Digital Object Identifier for the paper
        
    Returns:
        dict: Paper details from SciX Development API
    """
    logger.info(f"[SciXDev] Getting paper details for DOI: {doi}")
    
    dev_endpoint = os.getenv('SCIX_DEV_ENDPOINT')
    if not dev_endpoint:
        logger.warning("SCIX_DEV_ENDPOINT environment variable not set")
        return {}
    
    # TODO: Replace with actual API call
    logger.info("SciX Development paper details API not yet implemented")
    return {}
