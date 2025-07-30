"""
Service module for applying boost factors to search results.

This module provides functionality to apply various boost factors to search results,
including citation count, publication recency, document type, and refereed status boosts.
The boost factors are combined using a weighted sum approach.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from copy import deepcopy
import math
from dateutil.parser import parse

from ..api.models import SearchResult

# Setup logging
logger = logging.getLogger(__name__)

# Default weights for boost combination
DEFAULT_BOOST_WEIGHTS = {
    'citation': 0.3,
    'recency': 0.3,
    'doctype': 0.2,
    'collection': 0.1,
    'refereed': 0.1
}

# Document type boost values (direct boost factors)
DEFAULT_DOCTYPE_BOOSTS = {
    'article': 1.0,      # Journal article - highest priority
    'eprint': 1.0,       # Article preprinted in arXiv - highest priority
    'inbook': 1.0,       # Article appearing in a book - highest priority
    'book': 1.0,         # Book (monograph) - highest priority
    'inproceedings': 0.8,# Article appearing in conference proceedings
    'catalog': 0.8,      # Data catalog
    'software': 0.8,     # Software package
    'circular': 0.7,     # Printed or electronic circular
    'mastersthesis': 0.7,# Masters thesis
    'phdthesis': 0.7,    # PhD thesis
    'proceedings': 0.7,  # Conference proceedings book
    'techreport': 0.7,   # Technical report
    'bookreview': 0.6,   # Published book review
    'proposal': 0.6,     # Observing or funding proposal
    'talk': 0.6,         # Research talk
    'abstract': 0.5,     # Meeting abstract
    'newsletter': 0.5,   # Printed or electronic newsletter
    'obituary': 0.4,     # Obituary
    'pressrelease': 0.3, # Press release
    'misc': 0.2,         # Anything not in the above list
    'other': 0.2         # Default for unknown types
}

# Legacy rank-based configuration (DEPRECATED - for backward compatibility only)
DEFAULT_DOCTYPE_RANKS = {
    'article': 1,      # Journal article
    'eprint': 1,       # Article preprinted in arXiv
    'inproceedings': 2,# Article appearing in conference proceedings
    'inbook': 1,       # Article appearing in a book
    'abstract': 5,     # Meeting abstract
    'book': 1,         # Book (monograph)
    'bookreview': 4,   # Published book review
    'catalog': 2,      # Data catalog
    'circular': 3,     # Printed or electronic circular
    'erratum': 6,      # Erratum to a journal article
    'mastersthesis': 3,# Masters thesis
    'newsletter': 5,   # Printed or electronic newsletter
    'obituary': 6,     # Obituary
    'phdthesis': 3,    # PhD thesis
    'pressrelease': 7, # Press release
    'proceedings': 3,  # Conference proceedings book
    'proposal': 4,     # Observing or funding proposal
    'software': 2,     # Software package
    'talk': 4,         # Research talk
    'techreport': 3,   # Technical report
    'misc': 8,         # Anything not in the above list
    'other': 8         # Default for unknown types
}

def _convert_ranks_to_boosts(rank_map: Dict[str, int]) -> Dict[str, float]:
    """
    Convert legacy rank-based mapping to boost values for backward compatibility.
    
    Args:
        rank_map: Dictionary mapping doctypes to ranks (lower is better)
        
    Returns:
        Dict[str, float]: Dictionary mapping doctypes to boost values
    """
    unique_ranks = sorted(set(rank_map.values()))
    num_unique_ranks = len(unique_ranks)
    
    if num_unique_ranks <= 1:
        return {k: 1.0 for k in rank_map.keys()}
    
    # Create rank to boost mapping using the old formula
    rank_to_boost = {}
    for i, rank in enumerate(unique_ranks):
        rank_to_boost[rank] = 1.0 - (i / (num_unique_ranks - 1))
    
    # Convert rank map to boost map
    return {doctype: rank_to_boost[rank] for doctype, rank in rank_map.items()}

def _is_rank_mapping(mapping: Dict[str, Any]) -> bool:
    """
    Heuristic: treat as 'rank' mapping only if
    1) all entries are ints and
    2) max(rank) is reasonably small (e.g. ≤ 20).
    """
    return (
        mapping
        and all(isinstance(v, int) for v in mapping.values())
        and max(mapping.values()) <= 20
    )

def calculate_doctype_boost(doctype: str, doctype_mapping: Dict[str, Any] = None) -> float:
    """
    Calculate document type boost using direct boost values or legacy ranks.
    
    Args:
        doctype: Document type string
        doctype_mapping: Dictionary mapping doctypes to boost values (floats) or ranks (ints, deprecated)
        
    Returns:
        float: Boost factor for the document type
    """
    doctype_mapping = doctype_mapping or DEFAULT_DOCTYPE_BOOSTS
    doctype = doctype.lower() if doctype else 'other'
    
    # Backward compatibility: detect if we're using legacy rank-based mapping
    if _is_rank_mapping(doctype_mapping):
        logger.info("Converting legacy rank-based doctype mapping to boost values")
        doctype_mapping = _convert_ranks_to_boosts(doctype_mapping)
    
    # Get boost for doctype, default to 'other' if not found
    boost = doctype_mapping.get(doctype, doctype_mapping.get('other', 0.0))
    
    return float(boost)

def calculate_recency_boost(pubdate: str, multiplier: float = 1.0) -> float:
    """
    Calculate recency boost using reciprocal function.
    
    The boost factor is calculated as: 1 / (1 + multiplier * age_months)
    where age_months is the number of months since publication.
    
    Args:
        pubdate: Publication date string (YYYY-MM-DD)
        multiplier: Tuning parameter that controls decay rate
        
    Returns:
        float: Boost factor based on recency
    """
    try:
        # Parse publication date
        pub_date = parse(pubdate)
        now = datetime.now()
        
        # Calculate age in months
        age_months = ((now.year - pub_date.year) * 12 + 
                     (now.month - pub_date.month))
        
        # Apply reciprocal function
        return 1.0 / (1.0 + multiplier * age_months)
        
    except (ValueError, TypeError):
        logger.warning(f"Invalid publication date: {pubdate}")
        return 0.0

def calculate_citation_boost(
    citation_count: int,
    collection: str,
    pub_year: int,
    citation_distributions: Dict[str, Dict[int, Dict[str, float]]]
) -> float:
    """
    Calculate citation boost based on citation count.
    
    Args:
        citation_count: Number of citations
        collection: Collection name (e.g. 'astronomy', 'physics')
        pub_year: Publication year
        citation_distributions: Dictionary of citation distributions by collection and year
        
    Returns:
        float: Boost factor based on citation count
    """
    try:
        # Get distribution for collection and year
        dist = citation_distributions.get(collection, {}).get(pub_year, {})
        if not dist:
            logger.warning(f"No citation distribution for {collection} {pub_year}")
            return 0.0
            
        # Get median citations
        median = dist.get('median', 0)
        
        if median == 0:
            return 0.0
            
        # Calculate boost relative to median using log scale
        return math.log1p(citation_count / median)
            
    except Exception as e:
        logger.error(f"Error calculating citation boost: {str(e)}")
        return 0.0

def calculate_refereed_boost(is_refereed: bool) -> float:
    """
    Calculate boost for refereed papers.
    
    Args:
        is_refereed: Whether the paper is refereed
        
    Returns:
        float: 1.0 for refereed papers, 0.0 for non-refereed
    """
    return 1.0 if is_refereed else 0.0

def calculate_collection_boost(collection: str, collection_boosts: Dict[str, float]) -> float:
    """
    Calculate collection boost based on numerical multipliers.
    
    For records with multiple collections, the boost is calculated as:
    (boost_database1 + boost_database2 + ...) / num_databases_assigned
    
    For records with single collections, the boost is applied multiplicatively.
    
    Args:
        collection: Collection name(s) (e.g., 'astronomy', 'physics', 'earthscience,astronomy', 'general')
        collection_boosts: Dictionary mapping collections to boost multipliers
        
    Returns:
        float: Boost multiplier (0.0 = ignore/filter out, 1.0 = normal, >1.0 = boost)
    """
    if not collection or not collection_boosts:
        return 1.0
    
    # Handle multiple collections separated by comma
    collections = [c.strip().lower() for c in collection.split(',')]
    
    # Calculate boost for each collection - don't filter out for 0.0 in multi-collection papers
    # Only filter out if ALL collections have 0.0 boost or if it's a single collection with 0.0 boost
    
    # Calculate boost for each collection
    total_boost = 0.0
    num_collections = len(collections)
    
    for coll in collections:
        boost = collection_boosts.get(coll, 1.0)
        total_boost += boost
    
    # For single collections, filter out if boost is 0.0
    if num_collections == 1:
        if total_boost == 0.0:
            return 0.0  # Filter out single collection with 0.0 boost
        return total_boost
    
    # For multiple collections, return the average (don't filter out for 0.0 in mix)
    return total_boost / num_collections

def combine_boost_factors(
    boosts: Dict[str, float],
    weights: Dict[str, float] = None,
    combination_method: str = 'weighted_sum'
) -> float:
    """
    Combine boost factors using the specified combination method.
    
    Args:
        boosts: Dictionary of individual boost factors
        weights: Dictionary of weights for each boost factor. Only used for weighted methods.
        combination_method: Method to use for combining boosts:
            - 'simple_product': Multiply all boosts together
            - 'simple_sum': Add all boosts together
            - 'weighted_geometric_mean': Multiply boosts with weights
            - 'weighted_sum': Add boosts with weights (default)
        
    Returns:
        float: Combined boost factor
    """
    if not boosts:
        return 0.0
        
    # Filter out any None or negative boosts
    valid_boosts = {k: v for k, v in boosts.items() if v is not None and v >= 0}
    
    if not valid_boosts:
        return 0.0
        
    if combination_method == 'simple_product':
        # Multiply all boosts together
        return math.prod(valid_boosts.values())
        
    elif combination_method == 'simple_sum':
        # Add all boosts together
        return sum(valid_boosts.values())
        
    elif combination_method == 'weighted_geometric_mean':
        # Use provided weights or defaults
        weights = weights or DEFAULT_BOOST_WEIGHTS
        
        # Calculate weighted geometric mean
        # For each boost: boost^weight, then multiply all together
        weighted_products = [
            math.pow(valid_boosts.get(boost_type, 0.0), weight)
            for boost_type, weight in weights.items()
            if valid_boosts.get(boost_type, 0.0) > 0
        ]
        
        if not weighted_products:
            return 0.0
            
        return math.prod(weighted_products)
        
    else:  # weighted_sum (default)
        # Use provided weights or defaults
        weights = weights or DEFAULT_BOOST_WEIGHTS
        
        # Calculate weighted sum
        return sum(
            valid_boosts.get(boost_type, 0.0) * weight
            for boost_type, weight in weights.items()
        )

async def apply_all_boosts(
    results: List[SearchResult],
    boost_config: Dict[str, Any],
    citation_distributions: Dict[str, Dict[int, Dict[str, float]]] = None
) -> List[SearchResult]:
    """
    Apply all configured boost factors to search results.
    
    Args:
        results: List of search results to boost
        boost_config: Dictionary containing boost configuration including:
            - citation_boost: Overall strength of citation boost
            - recency_boost: Overall strength of recency boost
            - recency_multiplier: Controls decay rate of recency boost
            - doctype_boosts: Document type boost factors
            - field_boosts: Field-specific boost factors
            - boost_combination_method: Method to combine boosts
            - boost_weights: Weights for weighted combination methods
        citation_distributions: Dictionary of citation distributions by collection and year
        
    Returns:
        List[SearchResult]: List of boosted search results
    """
    if not results:
        return []
        
    try:
        # Create a deep copy of results to avoid modifying originals
        boosted_results = [deepcopy(result) for result in results]
        
        # Get boost configuration
        citation_boost = boost_config.get('citation_boost', 0.0)
        recency_boost = boost_config.get('recency_boost', 0.0)
        recency_multiplier = boost_config.get('recency_multiplier', 1.0)
        # Handle both new doctype_boosts and legacy doctype_ranks for backward compatibility
        doctype_boosts = boost_config.get('doctype_boosts', {})
        if not doctype_boosts and 'doctype_ranks' in boost_config:
            logger.info("Using legacy doctype_ranks configuration")
            doctype_boosts = boost_config.get('doctype_ranks', {})
        
        # Check if doctype_boosts is actually a legacy rank mapping
        if _is_rank_mapping(doctype_boosts):
            logger.info("Converting legacy rank-based doctype mapping to boost values in apply_all_boosts")
            doctype_boosts = _convert_ranks_to_boosts(doctype_boosts)
        field_boosts = boost_config.get('field_boosts', {})
        collection_boosts = boost_config.get('collection_boosts', {})
        combination_method = boost_config.get('boost_combination_method', 'weighted_sum')
        boost_weights = boost_config.get('boost_weights', DEFAULT_BOOST_WEIGHTS)
        
        # Auto-adjust combination method for large collection boosts
        # If any collection boost is > 10, use simple_sum to avoid weight dilution
        max_collection_boost = max(collection_boosts.values()) if collection_boosts else 0
        if max_collection_boost > 10 and combination_method == 'weighted_sum':
            combination_method = 'simple_sum'
            logger.info(f"Auto-adjusted combination method to simple_sum due to large collection boost: {max_collection_boost}")
        
        # Debug logging for boost configuration
        logger.info(f"Boost configuration: collection_boosts={collection_boosts}, combination_method={combination_method}")
        
        # Log collection distribution in original results
        collections_in_results = {}
        for result in boosted_results:
            collection = result.collection or 'unknown'
            collections_in_results[collection] = collections_in_results.get(collection, 0) + 1
        logger.info(f"Collections in original results: {collections_in_results}")

        # Initialize scores and source_id for each result
        for i, result in enumerate(boosted_results):
            # Initialize _score based on rank (higher rank = higher score)
            result._score = 1.0 / (i + 1)  # Inverse of rank for initial score
            result.source_id = 'boosted'  # Mark as boosted result
            
            # Initialize boost factors
            result.boost_factors = {
                'citation': 0.0,
                'recency': 0.0,
                'doctype': 0.0,
                'collection': 0.0,
                'refereed': 0.0,
                'field': 0.0
            }
            
            # Store original score and rank
            result.original_score = result._score
            result.original_rank = i + 1
            
            # Calculate individual boost factors
            boosts = {}
            
            # Citation boost
            if citation_boost > 0:
                base_boost = calculate_citation_boost(
                    result.citation_count or 0,
                    result.collection or 'general',
                    result.year,
                    citation_distributions or {}
                )
                boosts['citation'] = base_boost * citation_boost
                result.boost_factors['citation'] = boosts['citation']
            
            # Recency boost
            if recency_boost > 0 and result.pubdate:
                base_boost = calculate_recency_boost(
                    result.pubdate,
                    recency_multiplier
                )
                boosts['recency'] = base_boost * recency_boost
                result.boost_factors['recency'] = boosts['recency']
            
            # Document type boost
            if doctype_boosts:
                base_boost = calculate_doctype_boost(
                    result.doctype,
                    doctype_boosts
                )
                boosts['doctype'] = base_boost
                result.boost_factors['doctype'] = boosts['doctype']
            
            # Collection boost
            base_boost = calculate_collection_boost(
                result.collection,
                collection_boosts
            )
            boosts['collection'] = base_boost
            result.boost_factors['collection'] = boosts['collection']
            
            # Debug logging for collection boost
            if collection_boosts:
                logger.info(f"Collection boost for {result.title[:50]}...: collection={result.collection}, boost={base_boost}, config={collection_boosts}")
            
            # Field boost
            if field_boosts:
                logger.info(f"Processing field_boosts: {field_boosts}")
                field_boost = 0.0
                for field, weight in field_boosts.items():
                    if weight > 0:
                        # Check if this is a field value boost (e.g., "earthscience" for database/collection field)
                        if field in ['earthscience', 'astronomy', 'physics', 'general']:
                            # This is a collection/database value boost
                            logger.info(f"Checking collection boost: field={field}, result.collection={result.collection}, weight={weight}")
                            if result.collection:
                                # Handle multiple collections separated by comma
                                collections = [c.strip().lower() for c in result.collection.split(',')]
                                if field.lower() in collections:
                                    field_boost += weight
                                    logger.info(f"Applied collection boost: {weight} for {field}")
                                else:
                                    logger.info(f"No collection boost applied: field '{field}' not in collections {collections}")
                        elif field in ['article', 'thesis', 'inproceedings', 'book', 'abstract', 'eprint', 'inbook', 'bookreview', 'catalog', 'circular', 'erratum', 'mastersthesis', 'newsletter', 'obituary', 'phdthesis', 'pressrelease', 'proceedings', 'proposal', 'software', 'talk', 'techreport']:
                            # This is a doctype value boost
                            if result.doctype and result.doctype.lower() == field.lower():
                                field_boost += weight
                        else:
                            # Original field boost logic - boost based on field content
                            field_value = getattr(result, field, None)
                            if field_value:
                                # For numeric fields, use the value directly
                                if isinstance(field_value, (int, float)):
                                    field_boost += weight * field_value
                                # For string fields, use length as a proxy for relevance
                                elif isinstance(field_value, str):
                                    field_boost += weight * len(field_value)
                                # For list fields, use length as a proxy for relevance
                                elif isinstance(field_value, list):
                                    field_boost += weight * len(field_value)
                boosts['field'] = field_boost
                result.boost_factors['field'] = field_boost
                logger.info(f"Final field_boost for {result.title[:30]}...: {field_boost}")
            
            # Refereed boost
            if boost_config.get('refereed_boost', 0.0) > 0:
                boosts['refereed'] = calculate_refereed_boost(
                    result.is_refereed or False
                ) * boost_config['refereed_boost']
                result.boost_factors['refereed'] = boosts['refereed']
            
            # Check if collection boost is 0.0 (filter out)
            # Only filter out if it's exactly 0.0 (single collection with 0.0 boost)
            # Multi-collection papers with averaged boost > 0.0 should not be filtered
            if collection_boosts and boosts.get('collection', 1.0) == 0.0:
                # Mark this result for filtering by setting score to 0
                logger.info(f"Filtering out result due to 0.0 collection boost: {result.title[:50]}..., collection={result.collection}")
                result._score = 0.0
                result.boosted_score = 0.0
                continue
            
            # Check if doctype boost is 0.0 (filter out)
            # Only filter if doctype_boosts are configured AND the specific doctype has a 0.0 boost
            if doctype_boosts and result.doctype and result.doctype.lower() in doctype_boosts:
                doctype_boost_value = doctype_boosts.get(result.doctype.lower(), 0.0)
                if doctype_boost_value == 0.0:
                    # Mark this result for filtering by setting score to 0
                    logger.info(f"Filtering out result due to 0.0 doctype boost: {result.title[:50]}..., doctype={result.doctype}")
                    result._score = 0.0
                    result.boosted_score = 0.0
                    continue
            
            # Combine boost factors using the specified method
            final_boost = combine_boost_factors(
                boosts, 
                boost_weights,
                combination_method
            )
            
            # Apply final boost to score with overflow protection
            try:
                # For very large collection boosts, use additive boosting to overcome original score dominance
                collection_boost = boosts.get('collection', 0.0)
                if collection_boost > 5000:
                    # Use additive boosting for large collection boosts
                    # This ensures earthscience papers can beat physics papers regardless of original score
                    boost_multiplier = 1.0 + (final_boost / 100)  # Linear scaling for field/doctype boosts
                    additive_boost = collection_boost / 1000  # Add collection boost directly
                    result._score = result._score * boost_multiplier + additive_boost
                    logger.info(f"Using additive boosting for large collection boost: collection={collection_boost}, additive={additive_boost}, final_score={result._score}")
                elif final_boost > 100:
                    # Linear scaling for very large boosts
                    boost_multiplier = 1.0 + (final_boost / 100)  # Cap exponential effect
                    result._score *= boost_multiplier
                    logger.info(f"Using linear scaling for large boost: {final_boost} -> {boost_multiplier}")
                else:
                    # Normal exponential scaling for reasonable boosts
                    boost_multiplier = math.exp(final_boost)
                    result._score *= boost_multiplier
                    
                result.boosted_score = result._score
                
                # Debug logging for final boost calculation
                if collection_boosts:
                    logger.info(f"Final boost for {result.title[:50]}...: boosts={boosts}, final_boost={final_boost}, boost_multiplier={boost_multiplier}, original_score={result.original_score}, new_score={result._score}")
                    
            except OverflowError:
                # Fallback for extreme values
                logger.warning(f"Boost overflow for {result.title[:50]}..., using maximum multiplier")
                result._score *= 1e10  # Large but not infinite multiplier
                result.boosted_score = result._score
        
        # Filter out results with 0.0 score (collection boost = 0.0)
        filtered_results = [r for r in boosted_results if r._score > 0.0]
        
        # Log filtering results
        filtered_count = len(boosted_results) - len(filtered_results)
        logger.info(f"Filtered out {filtered_count} results due to 0.0 collection boost")
        
        # Log collection distribution after filtering
        collections_after_filtering = {}
        for result in filtered_results:
            collection = result.collection or 'unknown'
            collections_after_filtering[collection] = collections_after_filtering.get(collection, 0) + 1
        logger.info(f"Collections after filtering: {collections_after_filtering}")
        
        # Sort by boosted score and update ranks
        filtered_results.sort(key=lambda x: x._score, reverse=True)
        for i, result in enumerate(filtered_results):
            result.rank = i + 1
            result.rank_change = result.original_rank - result.rank
        
        return filtered_results
        
    except Exception as e:
        logger.error(f"Error applying boosts: {str(e)}", exc_info=True)
        return results


def apply_citation_boost(
    results: List[SearchResult],
    boost_factor: float,
    min_citations: int = 0
) -> List[SearchResult]:
    """
    Apply citation count boost to search results.
    
    Args:
        results: List of search results
        boost_factor: Factor to boost citation counts by
        min_citations: Minimum citations to apply boost
        
    Returns:
        List[SearchResult]: Results with citation boost applied
    """
    for result in results:
        citation_count = getattr(result, 'citation_count', 0) or 0
        if citation_count >= min_citations:
            # Make sure _score exists
            if not hasattr(result, '_score') or result._score is None:
                result._score = 1.0
                
            # Apply logarithmic boost to avoid extreme values
            boost = 1 + (boost_factor * (1 + math.log2(1 + citation_count)))
            result._score *= boost
    
    return results


def apply_recency_boost(
    results: List[SearchResult],
    boost_factor: float,
    reference_year: Optional[int] = None
) -> List[SearchResult]:
    """
    Apply publication recency boost to search results.
    
    Args:
        results: List of search results
        boost_factor: Factor to boost recent publications by
        reference_year: Year to use as reference point (defaults to current year)
        
    Returns:
        List[SearchResult]: Results with recency boost applied
    """
    # Use current year if reference_year is not provided
    current_year = reference_year or datetime.now().year
    
    for result in results:
        year = getattr(result, 'year', None)
        if year and isinstance(year, (int, str)):
            try:
                year = int(year)
                if 1900 <= year <= current_year:
                    # Make sure _score exists
                    if not hasattr(result, '_score') or result._score is None:
                        result._score = 1.0
                        
                    # Calculate years since publication
                    years_old = current_year - year
                    # Apply exponential decay boost
                    boost = 1 + (boost_factor * math.exp(-years_old / 10))
                    result._score *= boost
            except (ValueError, TypeError):
                continue
    
    return results


def apply_doctype_boosts(
    results: List[SearchResult],
    doctype_boosts: Dict[str, float]
) -> List[SearchResult]:
    """
    Apply document type boosts to search results.
    
    Args:
        results: List of search results
        doctype_boosts: Dictionary mapping document types to boost factors
        
    Returns:
        List[SearchResult]: Results with document type boosts applied
    """
    for result in results:
        doctype = getattr(result, 'doctype', '').lower()
        if doctype in doctype_boosts:
            # Make sure _score exists
            if not hasattr(result, '_score') or result._score is None:
                result._score = 1.0
                
            boost = 1 + doctype_boosts[doctype]
            result._score *= boost
    
    return results 