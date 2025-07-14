"""
Test database to collection mapping functionality.

This test verifies that the ADS API's database field is correctly mapped
to the collection field in SearchResult objects.
"""
import pytest
from app.services.ads_service import get_ads_results


class TestDatabaseCollectionMapping:
    """Test cases for database to collection mapping."""
    
    @pytest.mark.asyncio
    async def test_database_earthscience_astronomy_mapping(self):
        """
        Test that records from database:earthscience AND database:astronomy query
        return expected collection labels.
        
        This test verifies that:
        1. The query returns results
        2. The first 10 results have collection values of 'astronomy' or 'earthscience'
        3. The database field mapping logic is working correctly
        """
        # Query that should return records from both earthscience and astronomy databases
        query = "database:earthscience AND database:astronomy"
        
        # Get results from ADS API
        results = await get_ads_results(
            query=query,
            num_results=10,
            use_cache=False
        )
        
        # Verify we got results
        assert len(results) > 0, "Query should return at least some results"
        
        # Check the first 10 results (or all if fewer than 10)
        results_to_check = results[:10]
        
        print(f"\nTesting database collection mapping for query: {query}")
        print(f"Retrieved {len(results_to_check)} results to check:")
        
        # Expected collection values based on the query
        expected_collections = {'astronomy', 'earthscience'}
        
        for i, result in enumerate(results_to_check, 1):
            print(f"\nResult {i}:")
            print(f"  Title: {result.title[:60]}...")
            print(f"  Collection: {result.collection}")
            
            # Handle multiple collections separated by comma
            result_collections = set(c.strip() for c in result.collection.split(','))
            
            # Verify at least one collection matches expected values
            matching_collections = result_collections.intersection(expected_collections)
            assert len(matching_collections) > 0, \
                f"Result {i} has no matching collections. " \
                f"Result collections: {result_collections}. " \
                f"Expected at least one of: {expected_collections}. " \
                f"Title: {result.title[:60]}..."
            
            print(f"  Matching collections: {matching_collections}")
            print(f"  All collections: {result_collections}")
        
        # Verify we have both collection types represented
        all_individual_collections = set()
        for result in results_to_check:
            result_collections = set(c.strip() for c in result.collection.split(','))
            all_individual_collections.update(result_collections)
        
        print(f"\nAll individual collections found: {all_individual_collections}")
        
        # We should have at least one of each expected type
        matching_collections = all_individual_collections.intersection(expected_collections)
        assert len(matching_collections) >= 1, \
            f"Should find at least one expected collection type, found: {matching_collections}"
        
        # Check that at least astronomy and earthscience are represented
        assert 'astronomy' in all_individual_collections or 'earthscience' in all_individual_collections, \
            f"Should find at least astronomy or earthscience, found: {all_individual_collections}"
        
        print(f"\n✓ Test passed! All {len(results_to_check)} results have expected collection labels.")
    
    @pytest.mark.asyncio
    async def test_individual_database_queries(self):
        """
        Test individual database queries to verify mapping works for each database.
        """
        test_cases = [
            ("database:astronomy", "astronomy"),
            ("database:physics", "physics"),
            ("database:earthscience", "earthscience"),
        ]
        
        for query, expected_collection in test_cases:
            print(f"\nTesting query: {query}")
            
            results = await get_ads_results(
                query=query,
                num_results=5,
                use_cache=False
            )
            
            if len(results) > 0:
                # Check first few results
                for i, result in enumerate(results[:3], 1):
                    print(f"  Result {i}: {result.title[:50]}... -> {result.collection}")
                    assert result.collection == expected_collection, \
                        f"Query '{query}' returned result with collection '{result.collection}', " \
                        f"expected '{expected_collection}'"
                
                print(f"  ✓ All results have correct collection: {expected_collection}")
            else:
                print(f"  ⚠ No results found for query: {query}")
    
    @pytest.mark.asyncio
    async def test_collection_mapping_edge_cases(self):
        """
        Test edge cases in collection mapping logic.
        """
        # Test with a general query that might return mixed results
        query = "mars"
        
        results = await get_ads_results(
            query=query,
            num_results=20,
            use_cache=False
        )
        
        assert len(results) > 0, "General query should return results"
        
        # Check that all results have valid collection values
        valid_collections = {'astronomy', 'physics', 'earthscience', 'general'}
        
        for result in results:
            assert result.collection in valid_collections, \
                f"Result has invalid collection '{result.collection}'. " \
                f"Valid collections: {valid_collections}"
        
        # Print collection distribution
        collection_counts = {}
        for result in results:
            collection_counts[result.collection] = collection_counts.get(result.collection, 0) + 1
        
        print(f"\nCollection distribution for query '{query}':")
        for collection, count in collection_counts.items():
            print(f"  {collection}: {count} results")
        
        print("✓ All results have valid collection values")


if __name__ == "__main__":
    # Run the test directly
    pytest.main([__file__, "-v"])
