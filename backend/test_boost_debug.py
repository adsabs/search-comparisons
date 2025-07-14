#!/usr/bin/env python3
"""
Debug boost experiment issues
"""
import requests
import json
import logging

# Enable debug logging
logging.basicConfig(level=logging.INFO)

# Test the boost experiment endpoint
def test_boost_experiment():
    url = "http://localhost:8000/api/experiments/boost"
    
    # Test data matching what the user is doing
    payload = {
        "query": "Triton",
        "boost_config": {
            "collection_boosts": {
                "astronomy": 0.0,
                "physics": 300.0,
                "earthscience": 1.0
            }
        }
    }
    
    print(f"Testing boost experiment with payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n=== ORIGINAL RESULTS ===")
            for i, result in enumerate(data['original_results'][:3]):
                print(f"{i+1}. {result['title'][:50]}...")
                print(f"   Collection: {result.get('collection', 'N/A')}")
                print(f"   Source: {result.get('source', 'N/A')}")
                print()
            
            print("\n=== BOOSTED RESULTS ===")
            for i, result in enumerate(data['boosted_results'][:3]):
                print(f"{i+1}. {result['title'][:50]}...")
                print(f"   Collection: {result.get('collection', 'N/A')}")
                print(f"   Final boost: {result.get('final_boost', 'N/A')}")
                print(f"   Boost factors: {result.get('boost_factors', {})}")
                print()
                
            print(f"Original count: {len(data['original_results'])}")
            print(f"Boosted count: {len(data['boosted_results'])}")
            
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_boost_experiment()
