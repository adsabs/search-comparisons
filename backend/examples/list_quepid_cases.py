"""
Example script for listing all available Quepid cases.

This script retrieves and lists all Quepid cases accessible with the provided API key.
"""
import os
import sys
import asyncio
import json
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.quepid_service import get_quepid_cases


async def list_all_cases() -> None:
    """List all available Quepid cases."""
    print("Retrieving Quepid cases...")
    
    # Get all cases
    cases_response = await get_quepid_cases()
    
    if not cases_response:
        print("No cases found or error retrieving cases.")
        return
    
    # Print the raw response for debugging
    print("\nRaw response from Quepid API:")
    print(json.dumps(cases_response, indent=2))
    
    # Handle different response formats
    if isinstance(cases_response, list):
        cases = cases_response
    elif isinstance(cases_response, dict) and "cases" in cases_response:
        cases = cases_response["cases"]
    else:
        print(f"Unexpected response format: {type(cases_response)}")
        return
    
    print(f"\nFound {len(cases)} cases:\n")
    
    # Print case details with error handling
    for case in cases:
        if isinstance(case, dict):
            case_id = case.get("id", "Unknown")
            name = case.get("name", "Unnamed Case")
            query_count = len(case.get("queries", []))
            
            print(f"Case ID: {case_id}")
            print(f"Name: {name}")
            print(f"Number of queries: {query_count}")
        else:
            print(f"Unexpected case format: {case}")
        print("-" * 40)


if __name__ == "__main__":
    # Run the async function
    asyncio.run(list_all_cases()) 