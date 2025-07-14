"""
Search service module for the search-comparisons application.

This module coordinates search operations across different search engines,
handles fallbacks, and computes similarity metrics between results.
"""
import logging
import asyncio
from typing import Dict, List, Any, Set, Optional

from ..api.models import SearchResult
from .unified_cache_service import get_cache_service
from .comparison_service import ComparisonService

# Import specific search services
from .ads_service import get_ads_results
from .scholar_service import get_scholar_results, get_scholar_results_fallback
from .semantic_scholar_service import get_semantic_scholar_results
from .web_of_science_service import get_web_of_science_results

# Setup logging
logger = logging.getLogger(__name__)


class SearchService:
    """
    Service class for handling search operations across different search engines.
    
    This class provides methods for performing searches, handling fallbacks,
    and computing similarity metrics between results from different sources.
    """
    
    def __init__(self):
        """Initialize the search service with default configuration."""
        self.service_config = SERVICE_CONFIG
        self.default_num_results = DEFAULT_NUM_RESULTS
    
    async def search(
        self,
        query: str,
        sources: List[str],
        fields: List[str],
        max_results: Optional[int] = None,
        attempts: int = 2
    ) -> Dict[str, List[SearchResult]]:
        """
        Perform a search across multiple sources with fallback mechanisms.
        
        Args:
            query: Search query string
            sources: List of search engine sources to query
            fields: List of fields to retrieve
            max_results: Maximum number of results to return per source
            attempts: Maximum number of retry attempts per source
        
        Returns:
            Dict[str, List[SearchResult]]: Dictionary mapping source names to result lists
        """
        return await get_results_with_fallback(
            query=query,
            sources=sources,
            fields=fields,
            max_results=max_results,
            attempts=attempts
        )
    
    def compare(
        self,
        sources_results: Dict[str, List[SearchResult]],
        metrics: List[str],
        fields: List[str]
    ) -> Dict[str, Any]:
        """
        Compare search results from different sources using specified metrics.
        
        Args:
            sources_results: Dictionary mapping source names to result lists
            metrics: List of similarity metrics to compute
            fields: List of fields to use for comparisons
        
        Returns:
            Dict[str, Any]: Dictionary with comparison results
        """
        return compare_results(
            sources_results=sources_results,
            metrics=metrics,
            fields=fields
        )
    
    async def get_paper_details(
        self,
        doi: str,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed information about a paper from multiple sources.
        
        Args:
            doi: Digital Object Identifier of the paper
            sources: Optional list of sources to query
        
        Returns:
            Dict[str, Any]: Dictionary containing paper details from each source
        """
        return await get_paper_details(doi=doi, sources=sources)


# Service configuration with fallback settings
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

# Default number of results if not specified
DEFAULT_NUM_RESULTS = 20


async def get_results_with_fallback(
    query: str, 
    sources: List[str], 
    fields: List[str], 
    max_results: Optional[int] = None,
    attempts: int = 2,
    use_transformed_query: bool = False,
    original_query: Optional[str] = None,
    qf: Optional[str] = None,  # Query field weights for qf parameter
    field_boosts: Optional[Dict[str, float]] = None  # Field boosts for query transformation
) -> Dict[str, List[SearchResult]]:
    """
    Get search results from multiple sources with fallback mechanisms.
    
    Args:
        query: Search query string
        sources: List of search engine sources to query
        fields: List of fields to retrieve
        max_results: Maximum number of results to return per source
        attempts: Maximum number of retry attempts per source
        use_transformed_query: Whether to use the transformed query
        original_query: The original query before transformation
        qf: Query field weights (e.g., "title^50 author^30")
        field_boosts: Dictionary mapping field names to boost values for query transformation
    
    Returns:
        Dict[str, List[SearchResult]]: Dictionary mapping source names to result lists
    """
    results: Dict[str, List[SearchResult]] = {}
    
    # Convert query to string if it's a list
    if isinstance(query, list):
        query = " ".join(str(item) for item in query)
        logger.warning(f"Query was a list, converted to string: {query}")
    
    # Set number of results
    num_results = max_results or DEFAULT_NUM_RESULTS
    
    # Process each source
    for source in sources:
        if source not in SERVICE_CONFIG or not SERVICE_CONFIG[source]["enabled"]:
            logger.warning(f"Source {source} is not enabled or not configured")
            continue
        
        success = False
        attempt_count = 0
        
        while attempt_count < attempts and not success:
            attempt_count += 1
            logger.debug(f"Attempt {attempt_count} for {source}")
            
            try:
                # Determine which query to use based on source and transformation settings
                effective_query = query
                if use_transformed_query:
                    if source == "ads":
                        # For ADS, use the transformed query directly
                        effective_query = query
                        logger.debug(f"Using transformed query for ADS: {effective_query}")
                    else:
                        # For other sources, use the original query
                        effective_query = original_query or query
                        logger.debug(f"Using original query for {source}: {effective_query}")
                
                # Set timeout based on service config
                timeout = SERVICE_CONFIG[source]["timeout"] if source in SERVICE_CONFIG else 15
                
                # Create a task for the source query with timeout
                async def query_source():
                    if source == "ads":
                        return await get_ads_results(
                            effective_query, 
                            fields, 
                            num_results, 
                            qf=qf,  # Pass qf parameter
                            field_boosts=field_boosts  # Pass field boosts
                        )
                    elif source == "scholar":
                        if attempt_count == 1:
                            return await get_scholar_results(effective_query, fields, num_results)
                        else:
                            return await get_scholar_results_fallback(effective_query, num_results)
                    elif source == "semanticScholar":
                        return await get_semantic_scholar_results(effective_query, fields, num_results)
                    elif source == "webOfScience":
                        return await get_web_of_science_results(effective_query, fields, num_results)
                    else:
                        logger.error(f"Unknown source: {source}")
                        return []
                
                # Execute query with timeout
                try:
                    source_results = await asyncio.wait_for(query_source(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.error(f"Timeout after {timeout} seconds for {source}")
                    continue
                
                # Check if we got enough results
                min_results = SERVICE_CONFIG[source]["min_results"] if source in SERVICE_CONFIG else 1
                if len(source_results) >= min_results:
                    success = True
                    logger.debug(f"Successfully retrieved {len(source_results)} results from {source}")
                else:
                    logger.warning(f"Insufficient results from {source}: {len(source_results)} < {min_results}")
            
            except Exception as e:
                logger.error(f"Error fetching results from {source}: {str(e)}")
                if attempt_count == attempts:
                    logger.error(f"All attempts failed for {source}")
        
        # Save results to cache if successful
        if success and source_results:
            # Generate cache key with all parameters
            cache_key = get_cache_service().get_cache_key(
                source=source,
                query=effective_query,  # Use the effective query that was actually used
                fields=fields,
                num_results=num_results,
                qf=qf,
                field_boosts=field_boosts
            )
            get_cache_service().set(cache_key, source_results)
            results[source] = source_results
    
    return results


def compare_results(
    sources_results: Dict[str, List[SearchResult]], 
    metrics: List[str], 
    fields: List[str]
) -> Dict[str, Any]:
    """
    Compare search results from different sources using specified metrics.
    
    Computes similarity scores between results from different sources based
    on various similarity metrics and fields.
    
    Args:
        sources_results: Dictionary mapping source names to result lists
        metrics: List of similarity metrics to compute
        fields: List of fields to use for comparisons
    
    Returns:
        Dict[str, Any]: Dictionary with comparison results
    """
    comparison_service = ComparisonService()
    return comparison_service.compare_results(sources_results, metrics, fields)





async def get_paper_details(doi: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get detailed paper information by DOI from multiple sources.
    
    Retrieves detailed metadata for a paper identified by its DOI from
    multiple search engines and combines the results.
    
    Args:
        doi: Digital Object Identifier for the paper
        sources: List of sources to query (if None, query all available)
    
    Returns:
        Dict[str, Any]: Combined paper details from all sources
    """
    if not doi:
        logger.warning("Empty DOI provided to get_paper_details")
        return {}
    
    # Default to all sources if not specified
    if sources is None:
        sources = ["ads", "semanticScholar", "webOfScience"]
    
    # Filter to only enabled sources
    enabled_sources = [
        source for source in sources
        if source in SERVICE_CONFIG and SERVICE_CONFIG[source]["enabled"]
    ]
    
    # Initialize results
    results: Dict[str, Any] = {
        "doi": doi,
        "sources": {}
    }
    
    # Gather tasks for fetching from all sources
    tasks = []
    
    for source in enabled_sources:
        if source == "ads":
            from .ads_service import get_bibcode_from_doi
            tasks.append(get_bibcode_from_doi(doi))
        elif source == "semanticScholar":
            from .semantic_scholar_service import get_paper_details_by_doi
            tasks.append(get_paper_details_by_doi(doi))
        elif source == "webOfScience":
            from .web_of_science_service import get_wos_paper_details
            tasks.append(get_wos_paper_details(doi))
    
    # Run all tasks concurrently
    source_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for source, source_result in zip(enabled_sources, source_results):
        if isinstance(source_result, Exception):
            logger.error(f"Error getting paper details from {source}: {str(source_result)}")
            results["sources"][source] = {"error": str(source_result)}
        elif source_result:
            results["sources"][source] = source_result
    
    return results 