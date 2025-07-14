"""
Comparison service for analyzing search results from different sources.

This module provides functionality to compare search results using various
similarity metrics and compute overlap statistics.
"""
import logging
from typing import Dict, List, Any, Set, Tuple
from abc import ABC, abstractmethod

from ..api.models import SearchResult
from ..utils.text_processing import preprocess_text
from ..utils.similarity import calculate_jaccard_similarity, calculate_rank_based_overlap, calculate_cosine_similarity

logger = logging.getLogger(__name__)


class SimilarityMetric(ABC):
    """Abstract base class for similarity metrics."""
    
    @abstractmethod
    def calculate(self, results1: List[SearchResult], results2: List[SearchResult], fields: List[str]) -> float:
        """Calculate similarity between two result sets."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this metric."""
        pass


class JaccardSimilarity(SimilarityMetric):
    """Jaccard similarity metric implementation."""
    
    def calculate(self, results1: List[SearchResult], results2: List[SearchResult], fields: List[str]) -> float:
        """Calculate Jaccard similarity between two result sets."""
        try:
            # Extract text from specified fields
            text1 = self._extract_text_from_results(results1, fields)
            text2 = self._extract_text_from_results(results2, fields)
            
            if not text1 or not text2:
                return 0.0
            
            return calculate_jaccard_similarity(text1, text2)
        except Exception as e:
            logger.error(f"Error calculating Jaccard similarity: {e}")
            return 0.0
    
    def get_name(self) -> str:
        return "jaccard"
    
    def _extract_text_from_results(self, results: List[SearchResult], fields: List[str]) -> str:
        """Extract text from search results for specified fields."""
        texts = []
        for result in results:
            result_text = []
            for field in fields:
                if hasattr(result, field):
                    value = getattr(result, field)
                    if isinstance(value, list):
                        result_text.extend(str(v) for v in value)
                    elif value:
                        result_text.append(str(value))
            texts.append(" ".join(result_text))
        return " ".join(texts)


class RankBasedOverlap(SimilarityMetric):
    """Rank-based overlap metric implementation."""
    
    def calculate(self, results1: List[SearchResult], results2: List[SearchResult], fields: List[str]) -> float:
        """Calculate rank-based overlap between two result sets."""
        try:
            # Create ranked lists based on identifiers
            list1 = self._create_ranked_list(results1)
            list2 = self._create_ranked_list(results2)
            
            if not list1 or not list2:
                return 0.0
            
            return calculate_rank_based_overlap(list1, list2)
        except Exception as e:
            logger.error(f"Error calculating rank-based overlap: {e}")
            return 0.0
    
    def get_name(self) -> str:
        return "rank_based_overlap"
    
    def _create_ranked_list(self, results: List[SearchResult]) -> List[str]:
        """Create a ranked list of identifiers from search results."""
        identifiers = []
        for result in results:
            # Use DOI if available, otherwise use title
            doi = getattr(result, 'doi', None)
            if doi and isinstance(doi, list):
                doi = doi[0] if doi else None
            
            if doi:
                identifiers.append(doi)
            else:
                title = getattr(result, 'title', '')
                if isinstance(title, list):
                    title = title[0] if title else ''
                if title:
                    identifiers.append(preprocess_text(title))
        
        return identifiers


class CosineSimilarity(SimilarityMetric):
    """Cosine similarity metric implementation."""
    
    def calculate(self, results1: List[SearchResult], results2: List[SearchResult], fields: List[str]) -> float:
        """Calculate cosine similarity between two result sets."""
        try:
            # Extract text from specified fields
            text1 = self._extract_text_from_results(results1, fields)
            text2 = self._extract_text_from_results(results2, fields)
            
            if not text1 or not text2:
                return 0.0
            
            return calculate_cosine_similarity(text1, text2)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def get_name(self) -> str:
        return "cosine"
    
    def _extract_text_from_results(self, results: List[SearchResult], fields: List[str]) -> str:
        """Extract text from search results for specified fields."""
        texts = []
        for result in results:
            result_text = []
            for field in fields:
                if hasattr(result, field):
                    value = getattr(result, field)
                    if isinstance(value, list):
                        result_text.extend(str(v) for v in value)
                    elif value:
                        result_text.append(str(value))
            texts.append(" ".join(result_text))
        return " ".join(texts)


class OverlapCalculator:
    """Calculator for result overlap between sources."""
    
    def calculate_overlap(self, results1: List[SearchResult], results2: List[SearchResult]) -> Dict[str, Any]:
        """
        Calculate overlap between two result sets.
        
        Args:
            results1: First set of results
            results2: Second set of results
            
        Returns:
            Dict[str, Any]: Overlap statistics
        """
        # Build identifiers for both result sets
        identifiers1, results1_with_doi, results1_no_doi = self._build_identifiers(results1)
        identifiers2, results2_with_doi, results2_no_doi = self._build_identifiers(results2)
        
        # Calculate overlap
        overlap_items = identifiers1.intersection(identifiers2)
        overlap_count = len(overlap_items)
        
        # Calculate Jaccard index
        union_size = len(identifiers1.union(identifiers2))
        jaccard_index = overlap_count / union_size if union_size > 0 else 0
        
        # Calculate overlap percentages
        overlap_percentage_1 = (overlap_count / len(identifiers1)) * 100 if identifiers1 else 0
        overlap_percentage_2 = (overlap_count / len(identifiers2)) * 100 if identifiers2 else 0
        
        return {
            "count": overlap_count,
            "items": list(overlap_items),
            "jaccard_index": jaccard_index,
            "percentage_source1": overlap_percentage_1,
            "percentage_source2": overlap_percentage_2,
            "doi_matches": len([item for item in overlap_items if self._is_doi(item)]),
            "title_matches": len([item for item in overlap_items if not self._is_doi(item)])
        }
    
    def _build_identifiers(self, results: List[SearchResult]) -> Tuple[Set[str], Dict[str, Any], Dict[str, Any]]:
        """
        Build identifiers for a result set.
        
        Args:
            results: List of search results
            
        Returns:
            Tuple of (identifiers_set, results_with_doi, results_no_doi)
        """
        identifiers = set()
        results_with_doi = {}
        results_no_doi = {}
        
        for idx, result in enumerate(results):
            # Handle both SearchResult objects and dictionaries
            if isinstance(result, dict):
                doi = result.get('doi')
                title = result.get('title', '')
            else:
                doi = getattr(result, 'doi', None)
                title = getattr(result, 'title', '')
            
            # Normalize doi and title
            if isinstance(doi, list):
                doi = doi[0] if doi else None
            if isinstance(title, list):
                title = title[0] if title else ''
            
            if doi:
                identifiers.add(doi)
                results_with_doi[doi] = result
            else:
                processed_title = preprocess_text(title)
                if processed_title:
                    identifiers.add(processed_title)
                    results_no_doi[processed_title] = result
        
        return identifiers, results_with_doi, results_no_doi
    
    def _is_doi(self, identifier: str) -> bool:
        """Check if an identifier is a DOI."""
        return identifier.startswith('10.') or '/' in identifier


class ComparisonService:
    """Service for comparing search results from different sources."""
    
    def __init__(self):
        """Initialize the comparison service."""
        self.metrics = {
            "jaccard": JaccardSimilarity(),
            "rank_based_overlap": RankBasedOverlap(),
            "cosine": CosineSimilarity()
        }
        self.overlap_calculator = OverlapCalculator()
    
    def compare_results(
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
        comparison_results = {
            "overlap": {},
            "similarity": {},
            "sources": {}
        }
        
        # Process source data
        for source, results in sources_results.items():
            comparison_results["sources"][source] = {
                "count": len(results),
                "results": results
            }
        
        # Check if we have enough sources to compare
        active_sources = [s for s, r in sources_results.items() if r]
        if len(active_sources) < 2:
            logger.warning("Not enough sources with results to compare")
            return comparison_results
        
        # Calculate overlap and similarity for each pair of sources
        for i, source1 in enumerate(active_sources):
            for j, source2 in enumerate(active_sources):
                if i >= j:  # Skip self-comparisons and redundant pairs
                    continue
                
                results1 = sources_results[source1]
                results2 = sources_results[source2]
                
                if not results1 or not results2:
                    continue
                
                pair_key = f"{source1}_vs_{source2}"
                
                # Calculate overlap
                overlap_stats = self.overlap_calculator.calculate_overlap(results1, results2)
                comparison_results["overlap"][pair_key] = overlap_stats
                
                # Calculate similarity metrics
                comparison_results["similarity"][pair_key] = {}
                for metric_name in metrics:
                    if metric_name in self.metrics:
                        similarity = self.metrics[metric_name].calculate(results1, results2, fields)
                        comparison_results["similarity"][pair_key][metric_name] = similarity
                        logger.debug(f"{metric_name.title()} similarity between {source1} and {source2}: {similarity:.4f}")
                    else:
                        logger.warning(f"Unknown metric: {metric_name}")
        
        return comparison_results
    
    def add_metric(self, metric: SimilarityMetric) -> None:
        """Add a custom similarity metric."""
        self.metrics[metric.get_name()] = metric
    
    def get_available_metrics(self) -> List[str]:
        """Get list of available similarity metrics."""
        return list(self.metrics.keys())
