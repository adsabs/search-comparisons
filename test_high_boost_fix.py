#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.boost_service import calculate_doctype_boost, _is_rank_mapping, _convert_ranks_to_boosts

def test_high_boost_values_not_converted():
    """Test that high boost values are not converted from ranks"""
    
    # Test case 1: High boost values should NOT be treated as ranks
    # Using book with high boost and article with 0 (filtered out)
    mapping_high = {"book": 300000, "article": 0, "phdthesis": 5}
    print(f"Testing high boost mapping: {mapping_high}")
    
    # Should not be detected as rank mapping due to high values
    is_rank = _is_rank_mapping(mapping_high)
    print(f"Is rank mapping: {is_rank}")
    assert not is_rank, "High boost values should not be detected as ranks"
    
    # Should return boost values as-is
    book_boost = calculate_doctype_boost("book", mapping_high)
    print(f"Book boost: {book_boost}")
    assert book_boost == 300000.0, f"Expected 300000.0, got {book_boost}"
    
    # Test filtering out with 0 boost
    article_boost = calculate_doctype_boost("article", mapping_high)
    print(f"Article boost (should be filtered): {article_boost}")
    assert article_boost == 0.0, f"Expected 0.0 (filtered), got {article_boost}"
    
    phdthesis_boost = calculate_doctype_boost("phdthesis", mapping_high)
    print(f"PhD thesis boost: {phdthesis_boost}")
    assert phdthesis_boost == 5.0, f"Expected 5.0, got {phdthesis_boost}"

def test_legacy_ranks_still_converted():
    """Test that legacy rank values are still converted correctly"""
    
    # Test case 2: Small integer values should be treated as ranks
    mapping_ranks = {"article": 1, "phdthesis": 5, "book": 3}
    print(f"\nTesting legacy rank mapping: {mapping_ranks}")
    
    # Should be detected as rank mapping
    is_rank = _is_rank_mapping(mapping_ranks)
    print(f"Is rank mapping: {is_rank}")
    assert is_rank, "Small integer values should be detected as ranks"
    
    # Should convert ranks to boosts
    article_boost = calculate_doctype_boost("article", mapping_ranks)
    print(f"Article boost (from rank 1): {article_boost}")
    assert article_boost > 0.8, f"Rank 1 should give high boost, got {article_boost}"
    
    phdthesis_boost = calculate_doctype_boost("phdthesis", mapping_ranks)
    print(f"PhD thesis boost (from rank 5): {phdthesis_boost}")
    assert phdthesis_boost < article_boost, "Higher rank should give lower boost"

def test_mixed_values():
    """Test boundary cases"""
    
    # Test case 3: Values at the boundary (20 is the limit)
    mapping_boundary = {"article": 20, "book": 21}
    print(f"\nTesting boundary mapping: {mapping_boundary}")
    
    is_rank = _is_rank_mapping(mapping_boundary)
    print(f"Is rank mapping: {is_rank}")
    assert not is_rank, "Values > 20 should not be treated as ranks"
    
    article_boost = calculate_doctype_boost("article", mapping_boundary)
    print(f"Article boost: {article_boost}")
    assert article_boost == 20.0, f"Expected 20.0, got {article_boost}"

def test_zero_boost_filtering():
    """Test that 0 boost values filter out that doctype"""
    
    # Test case 4: Zero boost should filter out results
    mapping_filter = {"book": 2.0, "article": 0, "phdthesis": 1.5}
    print(f"\nTesting filtering with zero boost: {mapping_filter}")
    
    article_boost = calculate_doctype_boost("article", mapping_filter)
    print(f"Article boost (should be 0): {article_boost}")
    assert article_boost == 0.0, "Zero boost should remain zero"
    
    book_boost = calculate_doctype_boost("book", mapping_filter)
    print(f"Book boost: {book_boost}")
    assert book_boost == 2.0, "Non-zero boost should remain as-is"

if __name__ == "__main__":
    test_high_boost_values_not_converted()
    test_legacy_ranks_still_converted()
    test_mixed_values()
    test_zero_boost_filtering()
    print("\n✅ All tests passed! High boost values will now work correctly.")
