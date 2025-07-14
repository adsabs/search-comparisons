"""
ADS (Astrophysics Data System) search engine implementation.

This module implements the BaseEngine interface for the ADS API.
"""
import os
import logging
from typing import List, Dict, Any, Optional

from ..api.models import SearchResult
from .base_engine import BaseEngine
from .query_transformation import transform_query_with_boosts

logger = logging.getLogger(__name__)

# API Constants
ADS_API_URL = "https://api.adsabs.harvard.edu/v1/search/query"
DEFAULT_FIELDS = ["title", "author", "abstract", "year", "bibcode", "doi", "database", "citation_count"]

# Field mappings for ADS API
ADS_FIELD_MAPPING = {
    "title": "title",
    "author": "author",
    "abstract": "abstract",
    "year": "year",
    "bibcode": "bibcode",
    "doi": "doi",
    "citation_count": "citation_count",
    "database": "database"
}


class ADSEngine(BaseEngine):
    """ADS search engine implementation."""
    
    def __init__(self, **kwargs):
        """Initialize the ADS engine."""
        super().__init__(name="ads", **kwargs)
        self.api_key = self._get_api_key()
    
    def _get_api_key(self) -> Optional[str]:
        """Get the ADS API key from environment variables."""
        api_key = os.environ.get("ADS_API_KEY")
        if not api_key:
            logger.error("ADS_API_KEY environment variable not set")
        return api_key
    
    def build_query(self, query: str, **kwargs) -> str:
        """
        Build ADS-specific query string.
        
        Args:
            query: Original search query
            **kwargs: ADS-specific parameters (field_boosts, intent, etc.)
            
        Returns:
            str: ADS-specific query string
        """
        # Apply field boosts if provided
        field_boosts = kwargs.get('field_boosts')
        if field_boosts:
            return transform_query_with_boosts(query, field_boosts)
        
        return query
    
    def build_request_params(
        self, 
        query: str, 
        fields: List[str], 
        num_results: int, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build request parameters for the ADS API.
        
        Args:
            query: Search query
            fields: List of fields to retrieve
            num_results: Number of results to return
            **kwargs: ADS-specific parameters
            
        Returns:
            Dict[str, Any]: Request parameters
        """
        # Map fields to ADS field names
        ads_fields = [ADS_FIELD_MAPPING.get(field, field) for field in fields]
        
        params = {
            "q": query,
            "fl": ",".join(ads_fields),
            "rows": num_results,
            "sort": self._get_sort_parameter(kwargs.get('intent'), kwargs.get('sort'))
        }
        
        # Add query field weights if provided
        qf = kwargs.get('qf')
        if qf:
            params["qf"] = self._process_qf_parameter(qf)
        
        return params
    
    def build_headers(self) -> Dict[str, str]:
        """
        Build request headers for the ADS API.
        
        Returns:
            Dict[str, str]: Request headers
        """
        if not self.api_key:
            raise ValueError("ADS API key not available")
        
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def parse_response(self, response_data: Dict[str, Any]) -> List[SearchResult]:
        """
        Parse ADS API response into SearchResult objects.
        
        Args:
            response_data: Raw ADS API response data
            
        Returns:
            List[SearchResult]: Parsed search results
        """
        docs = response_data.get("response", {}).get("docs", [])
        if not docs:
            logger.warning("No results found in ADS API response")
            return []
        
        results = []
        for rank, doc in enumerate(docs, 1):
            try:
                result = self._create_search_result(doc, rank)
                results.append(result)
            except Exception as e:
                logger.error(f"Error parsing ADS result: {e}")
                continue
        
        return results
    
    def get_api_url(self) -> str:
        """
        Get the ADS API URL.
        
        Returns:
            str: ADS API URL
        """
        return ADS_API_URL
    
    def get_default_fields(self) -> List[str]:
        """
        Get the default fields for ADS searches.
        
        Returns:
            List[str]: Default fields
        """
        return DEFAULT_FIELDS.copy()
    
    def _get_sort_parameter(self, intent: Optional[str], sort: Optional[str]) -> str:
        """
        Get the sort parameter based on intent or explicit sort.
        
        Args:
            intent: Query intent (e.g., "influential", "recent")
            sort: Explicit sort parameter
            
        Returns:
            str: Sort parameter
        """
        if sort:
            return sort
        
        if intent == "influential":
            return "citation_count desc"
        elif intent == "recent":
            return "date desc"
        else:
            return "score desc"
    
    def _process_qf_parameter(self, qf: str) -> str:
        """
        Process and validate the qf (query field) parameter.
        
        Args:
            qf: Query field weights string
            
        Returns:
            str: Processed qf parameter
        """
        try:
            field_weights = []
            for fw in qf.split():
                if "^" in fw:
                    field, weight = fw.split("^")
                    field = field.lower()
                    
                    if field in ADS_FIELD_MAPPING:
                        mapped_field = ADS_FIELD_MAPPING[field]
                        weight_float = float(weight)
                        if weight_float > 0:
                            field_weights.append(f"{mapped_field}^{weight}")
                        else:
                            logger.warning(f"Invalid weight value: {weight} for field {field}")
                    else:
                        logger.warning(f"Invalid field name: {field}")
                else:
                    logger.warning(f"Invalid field weight format: {fw}")
            
            return " ".join(field_weights)
        except Exception as e:
            logger.error(f"Error processing qf parameter: {e}")
            return ""
    
    def _create_search_result(self, doc: Dict[str, Any], rank: int) -> SearchResult:
        """
        Create a SearchResult from an ADS document.
        
        Args:
            doc: ADS document data
            rank: Result rank
            
        Returns:
            SearchResult: Parsed search result
        """
        # Map database to collection
        collection = self._map_database_to_collection(doc.get("database", []))
        
        return SearchResult(
            title=self._extract_field(doc, "title"),
            author=doc.get("author", []),
            abstract=doc.get("abstract", ""),
            doi=self._extract_field(doc, "doi"),
            year=doc.get("year"),
            url=f"https://ui.adsabs.harvard.edu/abs/{doc.get('bibcode')}/abstract" if doc.get('bibcode') else None,
            source="ads",
            rank=rank,
            citation_count=doc.get("citation_count", 0),
            collection=collection,
            bibcode=doc.get("bibcode", ""),
            database=doc.get("database", [])
        )
    
    def _extract_field(self, doc: Dict[str, Any], field: str) -> str:
        """
        Extract a field value from an ADS document.
        
        Args:
            doc: ADS document data
            field: Field name
            
        Returns:
            str: Field value
        """
        value = doc.get(field)
        if isinstance(value, list):
            return value[0] if value else ""
        return value or ""
    
    def _map_database_to_collection(self, database: List[str]) -> str:
        """
        Map ADS database to collection.
        
        Args:
            database: List of database names
            
        Returns:
            str: Collection name
        """
        if not database:
            return "general"
        
        # Handle list of databases
        if isinstance(database, list):
            collections = []
            for db in database:
                if isinstance(db, str):
                    db_lower = db.lower()
                    if "astronomy" in db_lower:
                        collections.append("astronomy")
                    elif "physics" in db_lower:
                        collections.append("physics")
                    elif "earth" in db_lower:
                        collections.append("earthscience")
                    else:
                        collections.append("general")
            
            # Remove duplicates and sort
            collections = sorted(list(set(collections)))
            if not collections:
                collections = ["general"]
            
            return ",".join(collections)
        
        # Handle single database value
        if isinstance(database, str):
            db_lower = database.lower()
            if "astronomy" in db_lower:
                return "astronomy"
            elif "physics" in db_lower:
                return "physics"
            elif "earth" in db_lower:
                return "earthscience"
        
        return "general"
