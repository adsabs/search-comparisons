"""
Tests for database boost averaging functionality
"""
import pytest
from app.services.boost_service import calculate_collection_boost


class TestDatabaseBoostAveraging:
    """Test the database boost averaging logic"""
    
    def test_single_database_boost(self):
        """Test boost calculation for single database"""
        collection_boosts = {
            'astronomy': 5.0,
            'physics': 2.0,
            'earthscience': 10.0
        }
        
        # Single database should return the boost directly
        assert calculate_collection_boost('astronomy', collection_boosts) == 5.0
        assert calculate_collection_boost('physics', collection_boosts) == 2.0
        assert calculate_collection_boost('earthscience', collection_boosts) == 10.0
    
    def test_multiple_database_boost_averaging(self):
        """Test boost calculation for multiple databases (averaging)"""
        collection_boosts = {
            'astronomy': 0.0,
            'earthscience': 10.0,
            'physics': 5.0
        }
        
        # For astronomy (0) and earthscience (10): (0 + 10) / 2 = 5.0
        # Multi-collection papers get averaged boost, not filtered out
        assert calculate_collection_boost('astronomy,earthscience', collection_boosts) == 5.0
        
        # For earthscience (10) and physics (5): (10 + 5) / 2 = 7.5
        assert calculate_collection_boost('earthscience,physics', collection_boosts) == 7.5
        
        # For all three: (0 + 10 + 5) / 3 = 5.0
        assert abs(calculate_collection_boost('astronomy,earthscience,physics', collection_boosts) - 5.0) < 0.001
    
    def test_user_scenario_example(self):
        """Test the specific user scenario: astronomy=0, earthscience=10"""
        collection_boosts = {
            'astronomy': 0.0,
            'earthscience': 10.0
        }
        
        # Paper with both databases gets averaged boost: (0 + 10) / 2 = 5.0
        assert calculate_collection_boost('astronomy,earthscience', collection_boosts) == 5.0
        
        # Paper with only earthscience should get full boost
        assert calculate_collection_boost('earthscience', collection_boosts) == 10.0
        
        # Paper with only astronomy should be filtered out (single collection with 0.0)
        assert calculate_collection_boost('astronomy', collection_boosts) == 0.0
    
    def test_no_zero_boost_averaging(self):
        """Test averaging when no database has zero boost"""
        collection_boosts = {
            'astronomy': 2.0,
            'earthscience': 8.0,
            'physics': 4.0
        }
        
        # For astronomy (2) and earthscience (8): (2 + 8) / 2 = 5
        assert calculate_collection_boost('astronomy,earthscience', collection_boosts) == 5.0
        
        # For all three: (2 + 8 + 4) / 3 = 4.67 (approximately)
        result = calculate_collection_boost('astronomy,earthscience,physics', collection_boosts)
        assert abs(result - 4.666666666666667) < 0.0001
    
    def test_default_values(self):
        """Test behavior with default values (1.0)"""
        collection_boosts = {
            'astronomy': 1.0,
            'earthscience': 1.0,
            'physics': 1.0
        }
        
        # All default values should result in 1.0 (no boost)
        assert calculate_collection_boost('astronomy', collection_boosts) == 1.0
        assert calculate_collection_boost('astronomy,earthscience', collection_boosts) == 1.0
        assert calculate_collection_boost('astronomy,earthscience,physics', collection_boosts) == 1.0
    
    def test_mixed_default_and_custom_values(self):
        """Test behavior with mix of default and custom values"""
        collection_boosts = {
            'astronomy': 1.0,  # default (no boost)
            'earthscience': 5.0,  # custom boost
            'physics': 1.0  # default (no boost)
        }
        
        # astronomy (1) + earthscience (5) = 6 / 2 = 3.0
        assert calculate_collection_boost('astronomy,earthscience', collection_boosts) == 3.0
        
        # all three: (1 + 5 + 1) / 3 = 2.33 (approximately)
        result = calculate_collection_boost('astronomy,earthscience,physics', collection_boosts)
        assert abs(result - 2.333333333333333) < 0.0001
    
    def test_case_insensitive_multiple_databases(self):
        """Test case insensitive behavior with multiple databases"""
        collection_boosts = {
            'astronomy': 2.0,
            'earthscience': 6.0
        }
        
        # Test various case combinations
        assert calculate_collection_boost('Astronomy,EarthScience', collection_boosts) == 4.0
        assert calculate_collection_boost('ASTRONOMY,earthscience', collection_boosts) == 4.0
        assert calculate_collection_boost('astronomy,EARTHSCIENCE', collection_boosts) == 4.0
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in collection names"""
        collection_boosts = {
            'astronomy': 3.0,
            'earthscience': 9.0
        }
        
        # Test with various whitespace configurations
        assert calculate_collection_boost('astronomy, earthscience', collection_boosts) == 6.0
        assert calculate_collection_boost(' astronomy , earthscience ', collection_boosts) == 6.0
        assert calculate_collection_boost('astronomy,  earthscience', collection_boosts) == 6.0
