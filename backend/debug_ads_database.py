#!/usr/bin/env python3
"""
Debug ADS database field values directly
"""
import asyncio
import aiohttp

async def test_ads_database_field():
    """Test what database values ADS returns for Triton search"""
    
    # ADS API endpoint
    url = "https://api.adsabs.harvard.edu/v1/search/query"
    
    # Headers
    # Use the emergency fallback key that main.py sets
    api_key = "F6pHGICMXXy4aiAWBR4gaFL4Ta72xdM8jVhHDOsm"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Query parameters
    params = {
        "q": "Triton",
        "fl": "title,database,bibcode",
        "rows": 10,
        "sort": "citation_count desc"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                
                print("=== ADS Database Field Analysis ===")
                print(f"Total results: {data['response']['numFound']}")
                print()
                
                for i, doc in enumerate(data['response']['docs']):
                    print(f"{i+1}. {doc.get('title', ['No Title'])[0] if isinstance(doc.get('title'), list) else doc.get('title', 'No Title')}")
                    database_value = doc.get('database', 'No Database')
                    print(f"   Database: {database_value}")
                    print(f"   Type: {type(database_value)}")
                    
                    # Test our mapping logic
                    if isinstance(database_value, list) and database_value:
                        db_values = [db.lower() for db in database_value]
                        print(f"   Normalized: {db_values}")
                        
                        collections = []
                        for db in db_values:
                            if "earth" in db:
                                collections.append("earthscience")
                            elif "astronomy" in db:
                                collections.append("astronomy")
                            elif "physics" in db:
                                collections.append("physics")
                        
                        if not collections:
                            collections = ["general"]
                        
                        print(f"   Mapped to: {collections}")
                    elif isinstance(database_value, str):
                        db_lower = database_value.lower()
                        print(f"   Normalized: {db_lower}")
                        if "astronomy" in db_lower:
                            mapped = "astronomy"
                        elif "physics" in db_lower:
                            mapped = "physics"
                        elif "earth" in db_lower:
                            mapped = "earthscience"
                        else:
                            mapped = "general"
                        print(f"   Mapped to: {mapped}")
                    
                    print()
                    
            else:
                print(f"Error: {response.status}")
                print(await response.text())

if __name__ == "__main__":
    asyncio.run(test_ads_database_field())
