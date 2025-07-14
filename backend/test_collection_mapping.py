#!/usr/bin/env python3
"""
Test collection mapping specifically
"""
import asyncio
from app.services.ads_service import get_ads_results

async def test_collection_mapping():
    """Test what collections are being assigned to Triton papers"""
    
    print("=== Testing Collection Mapping ===")
    
    # Get results
    query = "Triton"
    fields = ["title", "author", "abstract", "doi", "year", "citation_count", "doctype", "property", "url", "database", "pubdate", "collection"]
    
    try:
        results = await get_ads_results(query=query, fields=fields, num_results=20)
        print(f"Retrieved {len(results)} results")
        
        # Check collection distribution
        collections = {}
        for result in results:
            collection = result.collection
            if collection not in collections:
                collections[collection] = []
            collections[collection].append(result.title[:50])
        
        print(f"\nCollection Distribution:")
        for collection, papers in collections.items():
            print(f"\n{collection.upper()} ({len(papers)} papers):")
            for paper in papers[:3]:  # Show first 3 papers
                print(f"  - {paper}...")
            if len(papers) > 3:
                print(f"  ... and {len(papers) - 3} more")
        
        # Check if any papers are marked as "general"
        general_papers = [r for r in results if r.collection == "general"]
        if general_papers:
            print(f"\nPapers marked as 'general': {len(general_papers)}")
            for paper in general_papers[:3]:
                print(f"  - {paper.title[:50]}...")
        else:
            print("\nNo papers marked as 'general'")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_collection_mapping())
