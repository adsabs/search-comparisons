"""
Base engine interface for search engines.

This module defines the abstract base class that all search engines should inherit from,
providing a consistent interface for querying different search APIs.
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from ..api.models import SearchResult
from .unified_cache_service import get_cache_service

logger = logging.getLogger(__name__)


class BaseEngine(ABC):
    """Abstract base class for search engines."""
    
    def __init__(self, name: str, timeout: int = 15, use_cache: bool = True):
        """
        Initialize the base engine.
        
        Args:
            name: Name of the search engine
            timeout: Timeout for API requests in seconds
            use_cache: Whether to use caching
        """
        self.name = name
        self.timeout = timeout
        self.use_cache = use_cache
        self.cache_service = get_cache_service()
        logger.info(f"Initialized {name} engine with timeout={timeout}, cache={use_cache}")
    
    @abstractmethod
    def build_query(self, query: str, **kwargs) -> str:
        """
        Build engine-specific query string.
        
        Args:
            query: Original search query
            **kwargs: Engine-specific parameters
            
        Returns:
            str: Engine-specific query string
        """
        pass
    
    @abstractmethod
    def build_request_params(
        self, 
        query: str, 
        fields: List[str], 
        num_results: int, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build request parameters for the engine's API.
        
        Args:
            query: Search query
            fields: List of fields to retrieve
            num_results: Number of results to return
            **kwargs: Engine-specific parameters
            
        Returns:
            Dict[str, Any]: Request parameters
        """
        pass
    
    @abstractmethod
    def build_headers(self) -> Dict[str, str]:
        """
        Build request headers for the engine's API.
        
        Returns:
            Dict[str, str]: Request headers
        """
        pass
    
    @abstractmethod
    def parse_response(self, response_data: Dict[str, Any]) -> List[SearchResult]:
        """
        Parse API response into SearchResult objects.
        
        Args:
            response_data: Raw API response data
            
        Returns:
            List[SearchResult]: Parsed search results
        """
        pass
    
    @abstractmethod
    def get_api_url(self) -> str:
        """
        Get the API URL for this engine.
        
        Returns:
            str: API URL
        """
        pass
    
    def get_cache_key(
        self, 
        query: str, 
        fields: List[str], 
        num_results: int, 
        **kwargs
    ) -> str:
        """
        Generate a cache key for the search request.
        
        Args:
            query: Search query
            fields: List of fields to retrieve
            num_results: Number of results to return
            **kwargs: Engine-specific parameters
            
        Returns:
            str: Cache key
        """
        return self.cache_service.get_cache_key(
            source=self.name,
            query=query,
            fields=fields,
            num_results=num_results,
            **kwargs
        )
    
    async def search(
        self, 
        query: str, 
        fields: Optional[List[str]] = None, 
        num_results: int = 20, 
        **kwargs
    ) -> List[SearchResult]:
        """
        Perform a search using this engine.
        
        Args:
            query: Search query
            fields: List of fields to retrieve
            num_results: Number of results to return
            **kwargs: Engine-specific parameters
            
        Returns:
            List[SearchResult]: Search results
        """
        try:
            # Set default fields if not provided
            fields = fields or self.get_default_fields()
            
            # Build the query
            processed_query = self.build_query(query, **kwargs)
            
            # Check cache first if enabled
            if self.use_cache:
                cache_key = self.get_cache_key(processed_query, fields, num_results, **kwargs)
                cached_results = self.cache_service.get(cache_key)
                
                if cached_results is not None:
                    logger.debug(f"Retrieved {len(cached_results)} results from cache for {self.name}")
                    return cached_results
            
            # Make the API request
            results = await self._make_request(processed_query, fields, num_results, **kwargs)
            
            # Save to cache if enabled
            if self.use_cache and results:
                self.cache_service.set(cache_key, results)
            
            logger.info(f"Retrieved {len(results)} results from {self.name}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching {self.name}: {str(e)}")
            return []
    
    async def _make_request(
        self, 
        query: str, 
        fields: List[str], 
        num_results: int, 
        **kwargs
    ) -> List[SearchResult]:
        """
        Make the actual API request.
        
        Args:
            query: Processed search query
            fields: List of fields to retrieve
            num_results: Number of results to return
            **kwargs: Engine-specific parameters
            
        Returns:
            List[SearchResult]: Search results
        """
        import httpx
        
        # Build request parameters
        params = self.build_request_params(query, fields, num_results, **kwargs)
        headers = self.build_headers()
        url = self.get_api_url()
        
        # Make the request
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            return self.parse_response(response_data)
    
    @abstractmethod
    def get_default_fields(self) -> List[str]:
        """
        Get the default fields for this engine.
        
        Returns:
            List[str]: Default fields
        """
        pass
    
    def get_min_results(self) -> int:
        """
        Get the minimum number of results this engine should return.
        
        Returns:
            int: Minimum results
        """
        return 5
    
    def get_timeout(self) -> int:
        """
        Get the timeout for this engine.
        
        Returns:
            int: Timeout in seconds
        """
        return self.timeout
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of this engine.
        
        Returns:
            Dict[str, Any]: Health status
        """
        return {
            'name': self.name,
            'status': 'ok',
            'timeout': self.timeout,
            'use_cache': self.use_cache,
            'cache_backend': type(self.cache_service.backend).__name__
        }
