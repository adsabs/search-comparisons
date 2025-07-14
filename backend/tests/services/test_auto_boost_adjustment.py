"""
Test auto-adjustment of boost combination method for large collection boosts
"""
import pytest
from app.services.boost_service import apply_all_boosts
from app.api.models import SearchResult


class TestAutoBoostAdjustment:
    """Test automatic adjustment of boost combination method"""
    
    def create_test_result(self, title: str, collection: str, rank: int = 1):
        """Create a test search result"""
        return SearchResult(
            title=title,
            author=["Test Author"],
            source="test",
            rank=rank,
            collection=collection,
            citation_count=0,
            year=2023,
            pubdate="2023-01-01",
            doctype="article",
            is_refereed=False
        )
    
    @pytest.mark.asyncio
    async def test_small_collection_boost_uses_weighted_sum(self):
        """Test that small collection boosts use weighted_sum method"""
        results = [
            self.create_test_result("Earth Science Paper", "earthscience", 1),
            self.create_test_result("Astronomy Paper", "astronomy", 2),
        ]
        
        boost_config = {
            'collection_boosts': {
                'earthscience': 2.0,  # Small boost
                'astronomy': 1.0
            },
            'boost_combination_method': 'weighted_sum'
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # Should have 2 results (no filtering)
        assert len(boosted_results) == 2
        
        # Earth science should be boosted but not dramatically due to weighting
        earth_result = next((r for r in boosted_results if r.collection == "earthscience"), None)
        astronomy_result = next((r for r in boosted_results if r.collection == "astronomy"), None)
        
        assert earth_result is not None
        assert astronomy_result is not None
        assert earth_result._score > astronomy_result._score
    
    @pytest.mark.asyncio
    async def test_large_collection_boost_auto_adjusts_to_simple_sum(self):
        """Test that large collection boosts automatically switch to simple_sum"""
        results = [
            self.create_test_result("Earth Science Paper", "earthscience", 1),
            self.create_test_result("Astronomy Paper", "astronomy", 2),
        ]
        
        boost_config = {
            'collection_boosts': {
                'earthscience': 3000.0,  # Large boost should trigger auto-adjustment
                'astronomy': 1.0
            },
            'boost_combination_method': 'weighted_sum'  # Should be overridden
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # Should have 2 results
        assert len(boosted_results) == 2
        
        # Earth science should be dramatically boosted
        earth_result = next((r for r in boosted_results if r.collection == "earthscience"), None)
        astronomy_result = next((r for r in boosted_results if r.collection == "astronomy"), None)
        
        assert earth_result is not None
        assert astronomy_result is not None
        
        # With simple_sum and large boost, earthscience should be much higher
        assert earth_result._score > astronomy_result._score * 10  # Much larger difference
        
        # Earth science should be ranked first
        assert earth_result.rank == 1
        assert astronomy_result.rank == 2
    
    @pytest.mark.asyncio
    async def test_threshold_value_for_auto_adjustment(self):
        """Test the threshold value (10) for auto-adjustment"""
        results = [
            self.create_test_result("Test Paper", "test", 1),
        ]
        
        # Test with boost exactly at threshold (10) - should NOT auto-adjust
        boost_config_at_threshold = {
            'collection_boosts': {'test': 10.0},
            'boost_combination_method': 'weighted_sum'
        }
        
        boosted_results = await apply_all_boosts(results, boost_config_at_threshold)
        result = boosted_results[0]
        score_at_threshold = result._score
        
        # Test with boost just above threshold (10.1) - should auto-adjust
        boost_config_above_threshold = {
            'collection_boosts': {'test': 10.1},
            'boost_combination_method': 'weighted_sum'
        }
        
        boosted_results = await apply_all_boosts(results, boost_config_above_threshold)
        result = boosted_results[0]
        score_above_threshold = result._score
        
        # Score above threshold should be much higher due to simple_sum
        assert score_above_threshold > score_at_threshold * 10
    
    @pytest.mark.asyncio
    async def test_explicit_combination_method_not_overridden(self):
        """Test that explicitly set combination methods other than weighted_sum are not overridden"""
        results = [
            self.create_test_result("Test Paper", "test", 1),
        ]
        
        # Test with explicit simple_product method
        boost_config = {
            'collection_boosts': {'test': 3000.0},
            'boost_combination_method': 'simple_product'  # Should NOT be overridden
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # Should work without issues (no exception should be thrown)
        assert len(boosted_results) == 1
        assert boosted_results[0]._score > 0
    
    @pytest.mark.asyncio
    async def test_multiple_large_collection_boosts(self):
        """Test with multiple large collection boosts"""
        results = [
            self.create_test_result("Earth Science Paper", "earthscience", 1),
            self.create_test_result("Physics Paper", "physics", 2),
            self.create_test_result("Astronomy Paper", "astronomy", 3),
        ]
        
        boost_config = {
            'collection_boosts': {
                'earthscience': 5000.0,  # Very large boost
                'physics': 2000.0,       # Large boost
                'astronomy': 0.0         # Should be filtered out
            },
            'boost_combination_method': 'weighted_sum'
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # Should have 2 results (astronomy filtered out)
        assert len(boosted_results) == 2
        
        # Earth science should be ranked first, physics second
        assert boosted_results[0].collection == "earthscience"
        assert boosted_results[1].collection == "physics"
        
        # Earth science should have higher score than physics
        assert boosted_results[0]._score > boosted_results[1]._score
