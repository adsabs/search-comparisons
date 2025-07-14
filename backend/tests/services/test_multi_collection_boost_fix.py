"""
Test for the multi-collection boost fix that handles papers in multiple collections
"""
import pytest
from app.services.boost_service import calculate_collection_boost


class TestMultiCollectionBoostFix:
    """Test the fix for multi-collection papers with mixed boost values"""
    
    def test_multi_collection_with_zero_boost_not_filtered(self):
        """Test that multi-collection papers with some 0.0 boost are averaged, not filtered"""
        collection_boosts = {
            'astronomy': 0.0,
            'earthscience': 3000.0,
            'physics': 1.0
        }
        
        # Paper in "astronomy,earthscience,physics" should get average boost
        # (0 + 3000 + 1) / 3 = 1000.33
        result = calculate_collection_boost('astronomy,earthscience,physics', collection_boosts)
        expected = (0 + 3000 + 1) / 3
        assert abs(result - expected) < 0.001
        
        # Paper in "astronomy,earthscience" should get average boost
        # (0 + 3000) / 2 = 1500.0
        result = calculate_collection_boost('astronomy,earthscience', collection_boosts)
        expected = (0 + 3000) / 2
        assert abs(result - expected) < 0.001
        
        # Paper in just "astronomy" should be filtered (single collection with 0.0)
        result = calculate_collection_boost('astronomy', collection_boosts)
        assert result == 0.0
        
        # Paper in just "earthscience" should get full boost
        result = calculate_collection_boost('earthscience', collection_boosts)
        assert result == 3000.0
    
    def test_realistic_particle_collisions_scenario(self):
        """Test the realistic scenario from the user's logs"""
        collection_boosts = {
            'astronomy': 0.0,
            'physics': 1.0,
            'earthscience': 3000.0,
            'general': 1.0
        }
        
        # Paper that was being filtered out: "astronomy,earthscience,physics"
        # Should get (0 + 3000 + 1) / 3 = 1000.33
        result = calculate_collection_boost('astronomy,earthscience,physics', collection_boosts)
        expected = (0 + 3000 + 1) / 3
        assert abs(result - expected) < 0.001
        
        # This should be a significant boost compared to pure physics papers
        physics_result = calculate_collection_boost('physics', collection_boosts)
        assert result > physics_result * 1000  # Much higher boost
    
    def test_edge_cases(self):
        """Test edge cases for the multi-collection logic"""
        collection_boosts = {
            'astronomy': 0.0,
            'physics': 0.0,
            'earthscience': 3000.0
        }
        
        # Two collections with 0.0 and one with high boost
        # (0 + 0 + 3000) / 3 = 1000.0
        result = calculate_collection_boost('astronomy,physics,earthscience', collection_boosts)
        expected = 3000.0 / 3
        assert abs(result - expected) < 0.001
        
        # All collections have 0.0 boost - should get 0.0 (averaged)
        result = calculate_collection_boost('astronomy,physics', collection_boosts)
        expected = (0 + 0) / 2
        assert result == expected
