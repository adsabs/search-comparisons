"""
Test fixes for boost experiment issues.
"""
from app.services.boost_service import calculate_collection_boost
from app.api.models import SearchResult


class TestCollectionBoostFixes:
    """Test the collection boost fixes."""
    
    def test_zero_boost_filters_out_single_collection(self):
        """Test that 0 boost filters out records with that collection."""
        # Should return 0 for earthscience when boost is 0
        result = calculate_collection_boost("earthscience", {"earthscience": 0.0})
        assert result == 0.0
        
    def test_zero_boost_filters_out_multi_collection(self):
        """Test that 0 boost filters out records even with multiple collections."""
        # Should return 0 even if paper has astronomy AND earthscience
        result = calculate_collection_boost("astronomy,earthscience", {"earthscience": 0.0, "astronomy": 2.0})
        assert result == 0.0
        
    def test_positive_boost_works_correctly(self):
        """Test that positive boosts work correctly."""
        # Should return the maximum boost
        result = calculate_collection_boost("astronomy,physics", {"astronomy": 2.0, "physics": 1.5})
        assert result == 2.0
        
    def test_default_boost_behavior(self):
        """Test default behavior when no boost config provided."""
        result = calculate_collection_boost("astronomy", {})
        assert result == 1.0
        
    def test_unknown_collection_gets_default(self):
        """Test that unknown collections get default boost of 1.0."""
        result = calculate_collection_boost("unknown", {"astronomy": 2.0})
        assert result == 1.0
        
    def test_empty_collection_returns_default(self):
        """Test that empty collection returns default boost."""
        result = calculate_collection_boost("", {"astronomy": 2.0})
        assert result == 1.0
        
    def test_collection_normalization(self):
        """Test that collection names are normalized properly."""
        # Should handle whitespace and case
        result = calculate_collection_boost(" ASTRONOMY , Physics ", {"astronomy": 2.0, "physics": 1.5})
        assert result == 2.0


class TestBoostFiltering:
    """Test that boost filtering works in the full pipeline."""
    
    def test_zero_boost_removes_results(self):
        """Test that results with 0 boost are removed from final results."""
        # Create test results with different collections
        results = [
            SearchResult(
                title="Astronomy Paper",
                author=["Author 1"],
                collection="astronomy",
                rank=1,
                source="ads"
            ),
            SearchResult(
                title="Earth Science Paper", 
                author=["Author 2"],
                collection="earthscience",
                rank=2,
                source="ads"
            ),
            SearchResult(
                title="Multi-discipline Paper",
                author=["Author 3"], 
                collection="astronomy,earthscience",
                rank=3,
                source="ads"
            )
        ]
        
        # Apply boost config that sets earthscience to 0
        
        boost_config = {"earthscience": 0.0, "astronomy": 2.0}
        
        # Filter results based on collection boost
        filtered_results = []
        for result in results:
            boost = calculate_collection_boost(result.collection, boost_config)
            if boost > 0:
                filtered_results.append(result)
        
        # Should only have the astronomy-only paper
        assert len(filtered_results) == 1
        assert filtered_results[0].title == "Astronomy Paper"
        
    def test_collection_labels_are_preserved(self):
        """Test that collection labels are preserved correctly."""
        result = SearchResult(
            title="Test Paper",
            author=["Author"],
            collection="astronomy,physics",
            rank=1,
            source="ads"
        )
        
        # Collection should be preserved as-is
        assert result.collection == "astronomy,physics"
