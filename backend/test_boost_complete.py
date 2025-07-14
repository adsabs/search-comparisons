#!/usr/bin/env python3
"""
Complete test of boost experiment to debug the issue
"""
import asyncio
from app.services.ads_service import get_ads_results
from app.services.boost_service import apply_all_boosts

async def test_boost_complete():
    """Test the complete boost experiment flow"""
    
    print("=== Testing Complete Boost Experiment Flow ===")
    
    # Step 1: Get original results
    print("\n1. Getting original results...")
    query = "Triton"
    fields = ["title", "author", "abstract", "doi", "year", "citation_count", "doctype", "property", "url", "database", "pubdate", "collection"]
    
    try:
        original_results = await get_ads_results(query=query, fields=fields, num_results=10)
        print(f"Retrieved {len(original_results)} original results")
        
        # Show original results and their collections
        print("\n=== ORIGINAL RESULTS ===")
        for i, result in enumerate(original_results[:5]):
            print(f"{i+1}. {result.title[:50]}...")
            print(f"   Collection: {result.collection}")
            print(f"   Source: {result.source}")
            print()
        
        # Step 2: Apply boosts
        print("\n2. Applying boosts...")
        boost_config = {
            "collection_boosts": {
                "astronomy": 0.0,
                "physics": 300.0,
                "earthscience": 1.0,
                "general": 1.0
            }
        }
        
        print(f"Boost config: {boost_config}")
        
        boosted_results = await apply_all_boosts(original_results, boost_config)
        print(f"After boost filtering: {len(boosted_results)} results")
        
        # Show boosted results
        print("\n=== BOOSTED RESULTS ===")
        for i, result in enumerate(boosted_results[:5]):
            print(f"{i+1}. {result.title[:50]}...")
            print(f"   Collection: {result.collection}")
            print(f"   Original rank: {result.original_rank}")
            print(f"   New rank: {result.rank}")
            print(f"   Boost factors: {result.boost_factors}")
            print(f"   Final boost: {sum(result.boost_factors.values())}")
            print()
            
        # Step 3: Check if any astronomy records survived
        astronomy_results = [r for r in boosted_results if "astronomy" in r.collection]
        print(f"\n3. Astronomy results that survived filtering: {len(astronomy_results)}")
        
        if astronomy_results:
            print("ERROR: Astronomy results should have been filtered out!")
            for result in astronomy_results:
                print(f"   - {result.title[:50]}... (collection: {result.collection})")
        else:
            print("SUCCESS: No astronomy results in boosted results")
            
        # Step 4: Check collection distribution
        print("\n4. Collection distribution in boosted results:")
        collections = {}
        for result in boosted_results:
            collection = result.collection
            if collection not in collections:
                collections[collection] = 0
            collections[collection] += 1
        
        for collection, count in collections.items():
            print(f"   {collection}: {count} results")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_boost_complete())
