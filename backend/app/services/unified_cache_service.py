"""
Unified cache service that consolidates file-based and in-memory caching.

This module provides a single interface for caching that can be configured
for different backends (file-based, in-memory LRU, Redis in future).
"""
import os
import json
import time
import hashlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from collections import OrderedDict

from ..api.models import SearchResult

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DIR = os.environ.get('CACHE_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'cache'))
CACHE_EXPIRY = int(os.environ.get('CACHE_EXPIRY', 86400))  # Default: 1 day


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from the cache."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory LRU cache backend."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        logger.info(f"Initialized MemoryCacheBackend with max_size={max_size}, ttl={default_ttl}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        if key not in self.cache:
            return None
            
        item = self.cache[key]
        if time.time() - item['timestamp'] > item['ttl']:
            logger.debug(f"Cache entry expired for key: {key}")
            del self.cache[key]
            return None
            
        # Move to end to mark as recently used
        self.cache.move_to_end(key)
        return item['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        try:
            # Remove oldest item if cache is full
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
                
            self.cache[key] = {
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl or self.default_ttl
            }
            logger.debug(f"Cached value for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        self.cache.clear()
        logger.info("Memory cache cleared")


class FileCacheBackend(CacheBackend):
    """File-based cache backend."""
    
    def __init__(self, cache_dir: str = CACHE_DIR, default_ttl: int = CACHE_EXPIRY):
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized FileCacheBackend with cache_dir={cache_dir}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        try:
            cache_path = self.cache_dir / f"{key}.json"
            
            if not cache_path.exists():
                logger.debug(f"Cache miss: No cache file found for key {key}")
                return None
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_content = json.load(f)
            
            # Check if cache has expired
            timestamp = cache_content.get("timestamp", 0)
            ttl = cache_content.get("ttl", self.default_ttl)
            
            if time.time() - timestamp > ttl:
                logger.debug(f"Cache expired for key {key}")
                return None
            
            # Handle SearchResult objects
            data = cache_content.get("data")
            if isinstance(data, list) and data and isinstance(data[0], dict) and "title" in data[0]:
                return [SearchResult(**item) for item in data]
            
            return data
            
        except Exception as e:
            logger.error(f"Error loading from cache: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        try:
            cache_path = self.cache_dir / f"{key}.json"
            
            # Convert SearchResult objects to dictionaries
            if isinstance(value, list) and value and hasattr(value[0], 'dict'):
                serializable_data = [item.dict() for item in value]
            else:
                serializable_data = value
            
            cache_content = {
                "timestamp": time.time(),
                "ttl": ttl or self.default_ttl,
                "data": serializable_data
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_content, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Cached value for key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
            return False
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("File cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")


class UnifiedCacheService:
    """Unified cache service with configurable backend."""
    
    def __init__(self, backend: Optional[CacheBackend] = None):
        """
        Initialize the cache service.
        
        Args:
            backend: Cache backend to use. Defaults to MemoryCacheBackend.
        """
        self.backend = backend or MemoryCacheBackend()
        logger.info(f"Initialized UnifiedCacheService with backend: {type(self.backend).__name__}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        return self.backend.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        return self.backend.set(key, value, ttl)
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        self.backend.clear()
    
    def get_cache_key(
        self,
        source: str,
        query: str,
        fields: List[str],
        num_results: Optional[int] = None,
        qf: Optional[str] = None,
        field_boosts: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Generate a cache key for storing search results.
        
        Args:
            source: The search engine source
            query: The search query string
            fields: List of requested fields
            num_results: Maximum number of results
            qf: Query field weights
            field_boosts: Dictionary mapping field names to boost values
        
        Returns:
            str: A unique cache key as a hex string
        """
        # Handle the case when query is a list
        if isinstance(query, list):
            query = " ".join(str(item) for item in query)
        
        # Create a string to hash
        results_str = f":{num_results}" if num_results is not None else ""
        qf_str = f":{qf}" if qf is not None else ""
        
        # Add field_boosts to the hash input if provided
        field_boosts_str = ""
        if field_boosts:
            sorted_boosts = sorted(field_boosts.items())
            field_boosts_str = ":" + ":".join(f"{field}^{weight}" for field, weight in sorted_boosts)
        
        hash_input = f"{source}:{query}:{':'.join(sorted(fields))}{results_str}{qf_str}{field_boosts_str}"
        
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the cache service.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            'status': 'ok',
            'backend': type(self.backend).__name__,
            'cache_dir': getattr(self.backend, 'cache_dir', None),
            'max_size': getattr(self.backend, 'max_size', None),
            'default_ttl': getattr(self.backend, 'default_ttl', None)
        }


# Global cache instance - can be configured at startup
_cache_instance = None

def get_cache_service() -> UnifiedCacheService:
    """Get the global cache service instance."""
    global _cache_instance
    if _cache_instance is None:
        # Default to memory cache for development, file cache for production
        backend = MemoryCacheBackend() if os.environ.get('ENVIRONMENT') == 'development' else FileCacheBackend()
        _cache_instance = UnifiedCacheService(backend)
    return _cache_instance

def configure_cache(backend: CacheBackend) -> None:
    """Configure the global cache service with a specific backend."""
    global _cache_instance
    _cache_instance = UnifiedCacheService(backend)
