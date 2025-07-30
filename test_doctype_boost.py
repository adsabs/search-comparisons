#!/usr/bin/env python3
"""
Test script to verify doctype boost calculation and ranking changes.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.boost_service import calculate_doctype_boost, apply_boosts, DEFAULT_DOCTYPE_RANKS
from backend.app.api.models import SearchResult
from copy import deepcopy

def create_test_result(title: str, doctype: str, score: float = 1.0) -> SearchResult:
    """Create a test search result."""
    return SearchResult(
        title=title,
        authors=["Test Author"],
        abstract="Test abstract",
        url="http://test.com",
        source="test",
        doctype=doctype,
        _score=score,
        original_score=score,
        boost_factors={},
        year=2023,
        collection="astronomy"
    )

def test_current_doctype_boosts():
    """Test current doctype boost calculation."""
    print("=== Current Doctype Boost Calculation ===")
    
    # Test article vs book with current ranks
    article_boost = calculate_doctype_boost('article', DEFAULT_DOCTYPE_RANKS)
    book_boost = calculate_doctype_boost('book', DEFAULT_DOCTYPE_RANKS)
    abstract_boost = calculate_doctype_boost('abstract', DEFAULT_DOCTYPE_RANKS)
    
    print(f"Article boost (rank 1): {article_boost:.4f}")
    print(f"Book boost (rank 1): {book_boost:.4f}")
    print(f"Abstract boost (rank 5): {abstract_boost:.4f}")
    
    # Create test results
    results = [
        create_test_result("Article Paper", "article", 10.0),
        create_test_result("Book Publication", "book", 8.0),  # Lower initial score
        create_test_result("Abstract Only", "abstract", 12.0)  # Higher initial score
    ]
    
    print(f"\nBefore boost:")
    for r in results:
        print(f"  {r.title}: {r.doctype}, score={r._score}")
    
    # Apply boosts
    boost_config = {
        'doctype_boosts': DEFAULT_DOCTYPE_RANKS,
        'combination_method': 'weighted_sum'
    }
    
    boosted_results = apply_boosts(results, boost_config)
    
    print(f"\nAfter boost (current ranks):")
    for r in boosted_results:
        doctype_boost = r.boost_factors.get('doctype', 0)
        print(f"  {r.title}: {r.doctype}, score={r._score:.4f}, doctype_boost={doctype_boost:.4f}, rank={getattr(r, 'rank', 'N/A')}")

def test_modified_doctype_boosts():
    """Test with book having better rank than article."""
    print("\n\n=== Modified Doctype Boost (Book > Article) ===")
    
    # Create modified ranks where book is better than article
    modified_ranks = deepcopy(DEFAULT_DOCTYPE_RANKS)
    modified_ranks['book'] = 0  # Better than article (rank 1)
    modified_ranks['article'] = 2  # Worse than book
    
    article_boost = calculate_doctype_boost('article', modified_ranks)
    book_boost = calculate_doctype_boost('book', modified_ranks)
    abstract_boost = calculate_doctype_boost('abstract', modified_ranks)
    
    print(f"Article boost (rank 2): {article_boost:.4f}")
    print(f"Book boost (rank 0): {book_boost:.4f}")
    print(f"Abstract boost (rank 5): {abstract_boost:.4f}")
    
    # Create same test results
    results = [
        create_test_result("Article Paper", "article", 10.0),
        create_test_result("Book Publication", "book", 8.0),  # Lower initial score
        create_test_result("Abstract Only", "abstract", 12.0)  # Higher initial score
    ]
    
    print(f"\nBefore boost:")
    for r in results:
        print(f"  {r.title}: {r.doctype}, score={r._score}")
    
    # Apply boosts with modified ranks
    boost_config = {
        'doctype_boosts': modified_ranks,
        'combination_method': 'weighted_sum'
    }
    
    boosted_results = apply_boosts(results, boost_config)
    
    print(f"\nAfter boost (modified ranks - book > article):")
    for r in boosted_results:
        doctype_boost = r.boost_factors.get('doctype', 0)
        print(f"  {r.title}: {r.doctype}, score={r._score:.4f}, doctype_boost={doctype_boost:.4f}, rank={getattr(r, 'rank', 'N/A')}")

def test_ranking_comparison():
    """Compare rankings between current and modified boost factors."""
    print("\n\n=== Ranking Comparison ===")
    
    # Test with same initial scores to see pure boost effect
    results_current = [
        create_test_result("Article Paper", "article", 10.0),
        create_test_result("Book Publication", "book", 10.0),  # Same initial score
    ]
    
    results_modified = [
        create_test_result("Article Paper", "article", 10.0),
        create_test_result("Book Publication", "book", 10.0),  # Same initial score
    ]
    
    # Current boosts
    boost_config_current = {
        'doctype_boosts': DEFAULT_DOCTYPE_RANKS,
        'combination_method': 'weighted_sum'
    }
    boosted_current = apply_boosts(results_current, boost_config_current)
    
    # Modified boosts
    modified_ranks = deepcopy(DEFAULT_DOCTYPE_RANKS)
    modified_ranks['book'] = 0  # Better than article
    modified_ranks['article'] = 2
    
    boost_config_modified = {
        'doctype_boosts': modified_ranks,
        'combination_method': 'weighted_sum'
    }
    boosted_modified = apply_boosts(results_modified, boost_config_modified)
    
    print("Current ranking (both have rank 1):")
    for r in boosted_current:
        print(f"  Rank {getattr(r, 'rank', 'N/A')}: {r.title} ({r.doctype}) - score: {r._score:.4f}")
    
    print("\nModified ranking (book rank 0, article rank 2):")
    for r in boosted_modified:
        print(f"  Rank {getattr(r, 'rank', 'N/A')}: {r.title} ({r.doctype}) - score: {r._score:.4f}")

if __name__ == "__main__":
    test_current_doctype_boosts()
    test_modified_doctype_boosts()
    test_ranking_comparison()
