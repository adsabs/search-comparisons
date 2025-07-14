"""
Test suite for collection boosting functionality.

This module tests the collection boosting feature which allows users to apply
numerical multipliers to search results based on their database/collection type.
"""
import pytest

from app.services.boost_service import (
    calculate_collection_boost,
    apply_all_boosts,
    combine_boost_factors
)
from app.api.models import SearchResult


class TestCollectionBoostCalculation:
    """Test the collection boost calculation logic."""

    def test_calculate_collection_boost_basic(self):
        """Test basic collection boost calculation."""
        # Test normal boost (1.0 = no change)
        assert calculate_collection_boost("astronomy", {"astronomy": 1.0}) == 1.0
        
        # Test positive boost
        assert calculate_collection_boost("astronomy", {"astronomy": 1.5}) == 1.5
        
        # Test reduction boost
        assert calculate_collection_boost("earthscience", {"earthscience": 0.8}) == 0.8
        
        # Test ignore boost (0.0 = filter out)
        assert calculate_collection_boost("general", {"general": 0.0}) == 0.0

    def test_calculate_collection_boost_case_insensitive(self):
        """Test that collection names are case insensitive."""
        collection_boosts = {"astronomy": 1.5, "physics": 1.2}
        
        assert calculate_collection_boost("Astronomy", collection_boosts) == 1.5
        assert calculate_collection_boost("PHYSICS", collection_boosts) == 1.2
        assert calculate_collection_boost("Physics", collection_boosts) == 1.2

    def test_calculate_collection_boost_missing_collection(self):
        """Test behavior when collection is not in boost config."""
        collection_boosts = {"astronomy": 1.5, "physics": 1.2}
        
        # Should return 1.0 (normal) for unknown collections
        assert calculate_collection_boost("unknown", collection_boosts) == 1.0
        assert calculate_collection_boost("", collection_boosts) == 1.0
        assert calculate_collection_boost(None, collection_boosts) == 1.0

    def test_calculate_collection_boost_empty_config(self):
        """Test behavior with empty or None boost config."""
        assert calculate_collection_boost("astronomy", {}) == 1.0
        assert calculate_collection_boost("astronomy", None) == 1.0

    def test_calculate_collection_boost_edge_cases(self):
        """Test edge cases for collection boosting."""
        collection_boosts = {"astronomy": 2.0, "physics": 0.5, "general": 0.0}
        
        # Test high boost
        assert calculate_collection_boost("astronomy", collection_boosts) == 2.0
        
        # Test low boost
        assert calculate_collection_boost("physics", collection_boosts) == 0.5
        
        # Test zero boost (should filter out)
        assert calculate_collection_boost("general", collection_boosts) == 0.0


class TestCollectionBoostIntegration:
    """Test integration of collection boosting with the main boost system."""

    def create_test_results(self):
        """Create test search results with different collections."""
        return [
            SearchResult(
                title="Astronomy Paper 1",
                author=["Author 1"],
                source="ads",
                rank=1,
                collection="astronomy",
                citation_count=10,
                year=2023,
                pubdate="2023-01-01",
                doctype="article"
            ),
            SearchResult(
                title="Physics Paper 1",
                author=["Author 2"],
                source="ads",
                rank=2,
                collection="physics",
                citation_count=5,
                year=2022,
                pubdate="2022-01-01",
                doctype="article"
            ),
            SearchResult(
                title="Earth Science Paper 1",
                author=["Author 3"],
                source="ads",
                rank=3,
                collection="earthscience",
                citation_count=8,
                year=2023,
                pubdate="2023-06-01",
                doctype="article"
            ),
            SearchResult(
                title="General Paper 1",
                author=["Author 4"],
                source="ads",
                rank=4,
                collection="general",
                citation_count=3,
                year=2021,
                pubdate="2021-01-01",
                doctype="article"
            )
        ]

    @pytest.mark.asyncio
    async def test_apply_all_boosts_with_collection_boost(self):
        """Test that collection boosting is applied correctly in the main boost function."""
        results = self.create_test_results()
        
        boost_config = {
            "citation_boost": 0.0,
            "recency_boost": 0.0,
            "doctype_boosts": {},
            "collection_boosts": {
                "astronomy": 2.0,    # Double the score
                "physics": 1.0,      # Normal score
                "earthscience": 0.5, # Half the score
                "general": 0.0       # Should be filtered out
            },
            "boost_combination_method": "weighted_sum",
            "boost_weights": {
                "citation": 0.0,
                "recency": 0.0,
                "doctype": 0.0,
                "collection": 1.0,  # Only collection boost active
                "refereed": 0.0
            }
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # Should only have 3 results (general collection filtered out)
        assert len(boosted_results) == 3
        
        # Find results by collection
        astronomy_result = next(r for r in boosted_results if r.collection == "astronomy")
        physics_result = next(r for r in boosted_results if r.collection == "physics")
        earthscience_result = next(r for r in boosted_results if r.collection == "earthscience")
        
        # Check that collection boost factors are applied correctly
        assert astronomy_result.boost_factors["collection"] == 2.0
        assert physics_result.boost_factors["collection"] == 1.0
        assert earthscience_result.boost_factors["collection"] == 0.5
        
        # Check that scores are affected correctly
        # Astronomy should have the highest score due to 2.0 boost
        # Physics should have normal score (1.0 boost)
        # Earth science should have lowest score due to 0.5 boost
        astronomy_score = astronomy_result._score
        physics_score = physics_result._score
        earthscience_score = earthscience_result._score
        
        assert astronomy_score > physics_score > earthscience_score

    @pytest.mark.asyncio
    async def test_collection_boost_with_other_boosts(self):
        """Test collection boosting combined with other boost types."""
        results = self.create_test_results()
        
        boost_config = {
            "citation_boost": 0.1,
            "recency_boost": 0.1,
            "doctype_boosts": {"article": 1.0, "other": 0.5},
            "collection_boosts": {
                "astronomy": 1.5,
                "physics": 1.2,
                "earthscience": 0.8,
                "general": 1.0
            },
            "boost_combination_method": "weighted_sum",
            "boost_weights": {
                "citation": 0.25,
                "recency": 0.25,
                "doctype": 0.25,
                "collection": 0.25,
                "refereed": 0.0
            }
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # All results should be present
        assert len(boosted_results) == 4
        
        # Check that all boost factors are calculated
        for result in boosted_results:
            assert "collection" in result.boost_factors
            assert "citation" in result.boost_factors
            assert "recency" in result.boost_factors
            assert "doctype" in result.boost_factors

    @pytest.mark.asyncio
    async def test_collection_boost_filtering(self):
        """Test that 0.0 collection boost effectively filters out results."""
        results = self.create_test_results()
        
        boost_config = {
            "citation_boost": 0.0,
            "recency_boost": 0.0,
            "doctype_boosts": {},
            "collection_boosts": {
                "astronomy": 1.0,
                "physics": 0.0,      # Filter out physics
                "earthscience": 0.0, # Filter out earth science
                "general": 1.0
            },
            "boost_combination_method": "weighted_sum",
            "boost_weights": {
                "citation": 0.0,
                "recency": 0.0,
                "doctype": 0.0,
                "collection": 1.0,
                "refereed": 0.0
            }
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # Should only have astronomy and general results
        assert len(boosted_results) == 2
        
        collections = [r.collection for r in boosted_results]
        assert "astronomy" in collections
        assert "general" in collections
        assert "physics" not in collections
        assert "earthscience" not in collections

    @pytest.mark.asyncio
    async def test_collection_boost_ranking_changes(self):
        """Test that collection boosting affects ranking correctly."""
        results = self.create_test_results()
        
        # Give a high boost to the last result (general) to test ranking change
        boost_config = {
            "citation_boost": 0.0,
            "recency_boost": 0.0,
            "doctype_boosts": {},
            "collection_boosts": {
                "astronomy": 1.0,
                "physics": 1.0,
                "earthscience": 1.0,
                "general": 3.0       # High boost should move it to top
            },
            "boost_combination_method": "weighted_sum",
            "boost_weights": {
                "citation": 0.0,
                "recency": 0.0,
                "doctype": 0.0,
                "collection": 1.0,
                "refereed": 0.0
            }
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # General result should now be ranked higher due to boost
        general_result = next(r for r in boosted_results if r.collection == "general")
        
        # Check that ranking changed (original rank was 4, should be better now)
        assert general_result.rank < general_result.original_rank
        assert general_result.rank_change > 0  # Positive change means moved up


class TestCollectionBoostCombination:
    """Test collection boost combination with other boost methods."""

    def test_combine_boost_factors_with_collection(self):
        """Test combining collection boost with other boost factors."""
        boosts = {
            "citation": 0.5,
            "recency": 0.3,
            "doctype": 0.2,
            "collection": 1.5,
            "refereed": 0.1
        }
        
        weights = {
            "citation": 0.2,
            "recency": 0.2,
            "doctype": 0.2,
            "collection": 0.3,
            "refereed": 0.1
        }
        
        # Test weighted sum combination
        result = combine_boost_factors(boosts, weights, "weighted_sum")
        expected = (0.5 * 0.2) + (0.3 * 0.2) + (0.2 * 0.2) + (1.5 * 0.3) + (0.1 * 0.1)
        assert abs(result - expected) < 0.001

    def test_combine_boost_factors_collection_only(self):
        """Test combination when only collection boost is active."""
        boosts = {
            "citation": 0.0,
            "recency": 0.0,
            "doctype": 0.0,
            "collection": 2.0,
            "refereed": 0.0
        }
        
        weights = {
            "citation": 0.0,
            "recency": 0.0,
            "doctype": 0.0,
            "collection": 1.0,
            "refereed": 0.0
        }
        
        result = combine_boost_factors(boosts, weights, "weighted_sum")
        assert result == 2.0


class TestCollectionBoostEdgeCases:
    """Test edge cases and error conditions for collection boosting."""

    @pytest.mark.asyncio
    async def test_missing_collection_field(self):
        """Test behavior when search results don't have collection field."""
        results = [
            SearchResult(
                title="Test Paper",
                author=["Author 1"],
                source="ads",
                rank=1,
                # No collection field
                citation_count=10,
                year=2023,
                pubdate="2023-01-01",
                doctype="article"
            )
        ]
        
        boost_config = {
            "collection_boosts": {
                "astronomy": 2.0,
                "physics": 1.5
            },
            "boost_combination_method": "weighted_sum",
            "boost_weights": {
                "citation": 0.0,
                "recency": 0.0,
                "doctype": 0.0,
                "collection": 1.0,
                "refereed": 0.0
            }
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # Should still have the result, with default collection boost
        assert len(boosted_results) == 1
        assert boosted_results[0].boost_factors["collection"] == 1.0

    @pytest.mark.asyncio
    async def test_empty_collection_boosts_config(self):
        """Test behavior when collection_boosts config is empty."""
        results = [
            SearchResult(
                title="Test Paper",
                author=["Author 1"],
                source="ads",
                rank=1,
                collection="astronomy",
                citation_count=10,
                year=2023,
                pubdate="2023-01-01",
                doctype="article"
            )
        ]
        
        boost_config = {
            "collection_boosts": {},  # Empty config
            "boost_combination_method": "weighted_sum",
            "boost_weights": {
                "citation": 0.0,
                "recency": 0.0,
                "doctype": 0.0,
                "collection": 1.0,
                "refereed": 0.0
            }
        }
        
        boosted_results = await apply_all_boosts(results, boost_config)
        
        # Should still have the result, with default collection boost
        assert len(boosted_results) == 1
        assert boosted_results[0].boost_factors["collection"] == 1.0
