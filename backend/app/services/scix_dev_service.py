"""
SciX Development service module.

This module provides implementation for the SciX Development
search engine endpoint using the ADS Solr development instance.
"""
import logging
import os
import base64
from typing import List, Optional, Dict, Any

import httpx

from ..api.models import SearchResult
from ..utils.http import safe_api_request

logger = logging.getLogger(__name__)

# SciX Development API Constants
SCIX_DEV_API_URL = "https://playground.adsabs.harvard.edu/dev/solr/collection1/select"
SCIX_DEV_USERNAME = "ads"
SCIX_DEV_PASSWORD = "$kw7Thr&nUNBZ!"
TIMEOUT_SECONDS = 15

def _get_default_fields() -> List[str]:
    """
    Get the default fields to retrieve from SciX Development API.
    
    Returns:
        List[str]: List of default field names
    """
    return [
        "bibcode", "title", "author", "year", "citation_count",
        "abstract", "doctype", "property", "pub", "volume", "page",
        "doi", "keyword", "database", "pubdate", "scix_id"
    ]

def _ensure_list(value):
    """Convert value to list if it's not already a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

def _create_search_result(doc: Dict[str, Any], rank: int) -> SearchResult:
    """
    Create a SearchResult object from a SciX Development API document.
    
    Args:
        doc: Document from SciX Development API
        rank: Rank of the result
        
    Returns:
        SearchResult: Processed search result
    """
    # Handle fields that might be arrays
    title = doc.get("title", "")
    if isinstance(title, list):
        title = title[0] if title else ""
    
    doi = doc.get("doi", "")
    if isinstance(doi, list):
        doi = doi[0] if doi else ""
    
    # Ensure list fields are properly formatted
    authors = _ensure_list(doc.get("author"))
    properties = _ensure_list(doc.get("property"))
    
    # Process database field to determine collection
    database = doc.get("database", [])
    collection = "general"  # default
    
    if isinstance(database, list) and database:
        db_values = [db.lower() for db in database]
        collections = []
        for db in db_values:
            if "earth" in db:
                collections.append("earthscience")
            elif "astronomy" in db:
                collections.append("astronomy")
            elif "physics" in db:
                collections.append("physics")
        
        collections = sorted(list(set(collections)))
        if not collections:
            collections = ["general"]
        collection = ",".join(collections)
    elif isinstance(database, str) and database:
        db_lower = database.lower()
        if "astronomy" in db_lower:
            collection = "astronomy"
        elif "physics" in db_lower:
            collection = "physics"
        elif "earth" in db_lower:
            collection = "earthscience"
        else:
            collection = "general"
    
    return SearchResult(
        title=title,
        author=authors,
        abstract=doc.get("abstract", ""),
        doi=doi,
        year=doc.get("year"),
        url=f"https://ui.adsabs.harvard.edu/abs/{doc.get('bibcode')}/abstract" if doc.get('bibcode') else None,
        source="sciXDev",
        rank=rank,
        citation_count=doc.get("citation_count", 0),
        doctype=doc.get("doctype", ""),
        property=properties,
        collection=collection,
        pubdate=doc.get("pubdate", "")
    )

async def get_scix_dev_results(
    query: str,
    fields: Optional[List[str]] = None,
    num_results: int = 20
) -> List[SearchResult]:
    """
    Get search results from SciX Development API.
    
    Args:
        query: Search query string
        fields: List of fields to retrieve (optional)
        num_results: Maximum number of results to return
        
    Returns:
        List[SearchResult]: List of search results from SciX Development API
    """
    logger.info(f"[SciXDev] Query: '{query}', num_results: {num_results}")
    
    # Get configuration from environment variables or fallback to hardcoded values
    dev_endpoint = os.getenv('SCIX_DEV_ENDPOINT', SCIX_DEV_API_URL)
    username = os.getenv('SCIX_DEV_USERNAME', SCIX_DEV_USERNAME)
    password = os.getenv('SCIX_DEV_PASSWORD', SCIX_DEV_PASSWORD)
    
    try:
        # Set default fields if not provided
        fields = fields or _get_default_fields()
        
        # Create basic auth header
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        async with httpx.AsyncClient() as client:
            # Set headers with basic auth
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json",
            }
            
            # Prepare query parameters (same structure as ADS API)
            params = {
                "q": query,
                "fl": ",".join(fields),
                "rows": num_results,
                "wt": "json"  # Ensure JSON response format
            }
            
            logger.debug(f"SciX Dev API request - URL: {dev_endpoint}")
            logger.debug(f"SciX Dev API request - Params: {params}")
            
            # Make request
            response_data = await safe_api_request(
                client,
                "GET",
                dev_endpoint,
                headers=headers,
                params=params,
                timeout=TIMEOUT_SECONDS
            )
            
            # Check if we got a response
            docs = response_data.get("response", {}).get("docs", [])
            if not docs:
                logger.warning(f"No results found from SciX Development API for query: {query}")
                return []
            
            # Process results
            results = [_create_search_result(doc, rank) for rank, doc in enumerate(docs, 1)]
            
            logger.info(f"Retrieved {len(results)} results from SciX Development API")
            return results
            
    except Exception as e:
        logger.error(f"Error retrieving results from SciX Development API: {str(e)}")
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
