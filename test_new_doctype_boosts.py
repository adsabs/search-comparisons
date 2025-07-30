#!/usr/bin/env python3
"""
Test the new direct doctype boost system.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.boost_service import calculate_doctype_boost, DEFAULT_DOCTYPE_BOOSTS

def test_new_direct_boosts():
    """Test the new direct boost value system."""
    print("=== Testing New Direct Boost System ===\n")
    
    # Test with new boost configuration
    new_boost_config = {
        'article': 1.0,
        'book': 0.9,
        'abstract': 0.5,
        'other': 0.2
    }
    
    print("Direct Boost Configuration:")
    for doctype, boost in new_boost_config.items():
        print(f"  {doctype}: {boost}")
    
    print(f"\nCalculated Boost Values:")
    for doctype in ['article', 'book', 'abstract', 'other', 'unknown']:
        boost = calculate_doctype_boost(doctype, new_boost_config)
        print(f"  {doctype}: {boost:.3f}")

def test_backward_compatibility():
    """Test backward compatibility with rank-based system."""
    print("\n=== Testing Backward Compatibility ===\n")
    
    # Test with old rank configuration (integers)
    old_rank_config = {
        'article': 1,
        'book': 2,
        'abstract': 5,
        'other': 8
    }
    
    print("Legacy Rank Configuration:")
    for doctype, rank in old_rank_config.items():
        print(f"  {doctype}: rank {rank}")
    
    print(f"\nCalculated Boost Values (converted from ranks):")
    for doctype in ['article', 'book', 'abstract', 'other', 'unknown']:
        boost = calculate_doctype_boost(doctype, old_rank_config)
        print(f"  {doctype}: {boost:.3f}")

def test_default_behavior():
    """Test default behavior when no config is provided."""
    print("\n=== Testing Default Behavior ===\n")
    
    print("Using DEFAULT_DOCTYPE_BOOSTS:")
    for doctype in ['article', 'book', 'eprint', 'abstract', 'other', 'unknown']:
        boost = calculate_doctype_boost(doctype)
        print(f"  {doctype}: {boost:.3f}")

def test_mixed_types():
    """Test error handling with mixed types."""
    print("\n=== Testing Edge Cases ===\n")
    
    # Test with empty config
    empty_boost = calculate_doctype_boost('article', {})
    print(f"Empty config - article boost: {empty_boost:.3f}")
    
    # Test with missing doctype
    missing_boost = calculate_doctype_boost('nonexistent', {'article': 1.0, 'other': 0.5})
    print(f"Missing doctype - falls back to 'other': {missing_boost:.3f}")
    
    # Test with None doctype
    none_boost = calculate_doctype_boost(None, {'article': 1.0, 'other': 0.5})
    print(f"None doctype - falls back to 'other': {none_boost:.3f}")

if __name__ == "__main__":
    test_new_direct_boosts()
    test_backward_compatibility()
    test_default_behavior()
    test_mixed_types()
