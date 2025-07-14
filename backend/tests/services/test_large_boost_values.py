"""
Test large boost values to demonstrate the weighting issue
"""
import pytest
import math
from app.services.boost_service import combine_boost_factors, DEFAULT_BOOST_WEIGHTS


class TestLargeBoostValues:
    """Test how large boost values are handled"""
    
    def test_large_collection_boost_with_default_weights(self):
        """Test that large collection boost values are heavily diminished by default weights"""
        boosts = {
            'collection': 3000.0,
            'citation': 0.0,
            'recency': 0.0,
            'doctype': 0.0,
            'refereed': 0.0
        }
        
        # With default weights, collection gets 0.1 weight
        final_boost = combine_boost_factors(boosts, DEFAULT_BOOST_WEIGHTS, 'weighted_sum')
        
        # Should be 3000 * 0.1 = 300
        assert final_boost == 300.0
        
        # The final score multiplier would be exp(300) which is enormous
        score_multiplier = math.exp(final_boost)
        assert score_multiplier > 1e100  # This is huge!
        
    def test_collection_boost_with_equal_weights(self):
        """Test collection boost with equal weights"""
        boosts = {
            'collection': 3000.0,
            'citation': 0.0,
            'recency': 0.0,
            'doctype': 0.0,
            'refereed': 0.0
        }
        
        # With equal weights (0.2 each)
        equal_weights = {
            'citation': 0.2,
            'recency': 0.2,
            'doctype': 0.2,
            'collection': 0.2,
            'refereed': 0.2
        }
        
        final_boost = combine_boost_factors(boosts, equal_weights, 'weighted_sum')
        
        # Should be 3000 * 0.2 = 600
        assert final_boost == 600.0
        
    def test_collection_boost_with_full_weight(self):
        """Test collection boost with full weight"""
        boosts = {
            'collection': 3000.0,
            'citation': 0.0,
            'recency': 0.0,
            'doctype': 0.0,
            'refereed': 0.0
        }
        
        # With full weight for collection
        full_weight = {
            'citation': 0.0,
            'recency': 0.0,
            'doctype': 0.0,
            'collection': 1.0,
            'refereed': 0.0
        }
        
        final_boost = combine_boost_factors(boosts, full_weight, 'weighted_sum')
        
        # Should be 3000 * 1.0 = 3000
        assert final_boost == 3000.0
        
    def test_moderate_boost_values(self):
        """Test more moderate boost values that should work well with default weights"""
        boosts = {
            'collection': 10.0,  # More reasonable boost
            'citation': 0.0,
            'recency': 0.0,
            'doctype': 0.0,
            'refereed': 0.0
        }
        
        final_boost = combine_boost_factors(boosts, DEFAULT_BOOST_WEIGHTS, 'weighted_sum')
        
        # Should be 10 * 0.1 = 1.0
        assert final_boost == 1.0
        
        # Score multiplier would be exp(1) ≈ 2.718
        score_multiplier = math.exp(final_boost)
        assert abs(score_multiplier - 2.718281828459045) < 0.001
        
    def test_simple_product_method(self):
        """Test simple product method which doesn't use weights"""
        boosts = {
            'collection': 3000.0,
            'citation': 1.0,  # Need non-zero values for product
            'recency': 1.0,
            'doctype': 1.0,
            'refereed': 1.0
        }
        
        final_boost = combine_boost_factors(boosts, None, 'simple_product')
        
        # Should be 3000 * 1 * 1 * 1 * 1 = 3000
        assert final_boost == 3000.0
        
    def test_simple_sum_method(self):
        """Test simple sum method which doesn't use weights"""
        boosts = {
            'collection': 3000.0,
            'citation': 0.0,
            'recency': 0.0,
            'doctype': 0.0,
            'refereed': 0.0
        }
        
        final_boost = combine_boost_factors(boosts, None, 'simple_sum')
        
        # Should be 3000 + 0 + 0 + 0 + 0 = 3000
        assert final_boost == 3000.0
