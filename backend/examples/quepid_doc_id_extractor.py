"""
Quepid Document ID Extractor

This script extracts document IDs from a Quepid case and prepares them for
title lookup from an external source.

Based on our investigation, Quepid case 8835 does not directly store title metadata,
but provides document IDs that can be used to look up titles elsewhere.
"""
import os
import sys
import asyncio
import json
from pathlib import Path
import httpx
from urllib.parse import urljoin
from typing import Dict, List, Set, Optional, Any


async def extract_doc_ids_from_quepid(case_id: int, api_key: str) -> Set[str]:
    """
    Extract document IDs from a Quepid case.
    
    Args:
        case_id: The Quepid case ID to retrieve document IDs from
        api_key: The Quepid API key
        
    Returns:
        Set[str]: A set of document IDs from the case
    """
    # API Constants
    api_url = "https://app.quepid.com/api/"
    doc_ids = set()
    
    print(f"Extracting document IDs from Quepid case {case_id}...")
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Get the ratings data which contains document IDs
            ratings_url = urljoin(api_url, f"export/ratings/{case_id}")
            print(f"Getting ratings data: {ratings_url}")
            
            ratings_response = await client.get(ratings_url, headers=headers, timeout=30)
            
            if ratings_response.status_code != 200:
                print(f"Error getting ratings: HTTP {ratings_response.status_code}")
                return doc_ids
            
            ratings_data = ratings_response.json()
            
            # Extract document IDs from the ratings
            if "ratings" in ratings_data:
                # The flat ratings format
                ratings = ratings_data["ratings"]
                for rating in ratings:
                    doc_id = rating.get("doc_id")
                    if doc_id:
                        doc_ids.add(doc_id)
            elif "queries" in ratings_data:
                # The nested queries format
                for query in ratings_data["queries"]:
                    ratings_dict = query.get("ratings", {})
                    if ratings_dict:
                        doc_ids.update(ratings_dict.keys())
            
            print(f"Found {len(doc_ids)} unique document IDs")
            return doc_ids
            
    except Exception as e:
        print(f"Error accessing Quepid API: {str(e)}")
        return doc_ids


def lookup_titles_from_external_source(doc_ids: Set[str]) -> Dict[str, str]:
    """
    Mock function to demonstrate how to look up titles from an external source.
    
    In a real implementation, this would query your database, API, or other source
    to get titles based on document IDs.
    
    Args:
        doc_ids: Set of document IDs to look up
        
    Returns:
        Dict[str, str]: A dictionary mapping document IDs to titles
    """
    print(f"Looking up titles for {len(doc_ids)} document IDs from external source...")
    
    # This is where you would implement your actual title lookup
    # For demonstration purposes, we're just creating mock titles
    titles = {}
    
    # Example of how you might implement this with ADS
    # Replace this with your actual implementation
    """
    import ads
    
    for doc_id in doc_ids:
        try:
            # Query ADS for the document
            papers = list(ads.SearchQuery(identifier=doc_id, fl=['title']))
            
            if papers and len(papers) > 0 and hasattr(papers[0], 'title'):
                titles[doc_id] = papers[0].title
        except Exception as e:
            print(f"Error looking up title for {doc_id}: {str(e)}")
    """
    
    # Placeholder code for demonstration
    for doc_id in doc_ids:
        titles[doc_id] = f"Mock title for document {doc_id}"
    
    return titles


async def main(case_id: int, api_key: str) -> None:
    """
    Main function to extract document IDs and look up titles.
    
    Args:
        case_id: The Quepid case ID to process
        api_key: The Quepid API key
    """
    # Extract document IDs from Quepid
    doc_ids = await extract_doc_ids_from_quepid(case_id, api_key)
    
    if not doc_ids:
        print("No document IDs found. Exiting.")
        return
    
    # Save document IDs to a file
    doc_ids_file = f"quepid_case_{case_id}_doc_ids.json"
    with open(doc_ids_file, "w") as f:
        json.dump(list(doc_ids), f, indent=2)
    
    print(f"Document IDs saved to {doc_ids_file}")
    
    # Look up titles from external source
    titles = lookup_titles_from_external_source(doc_ids)
    
    if titles:
        print(f"Found titles for {len(titles)} document IDs")
        
        # Print some example titles
        print("\nExample titles:")
        for i, (doc_id, title) in enumerate(titles.items()):
            if i < 5:  # Print only first 5 titles
                print(f"Doc ID: {doc_id}")
                print(f"Title: {title}")
                print()
            else:
                break
        
        # Save titles to a JSON file
        titles_file = f"quepid_case_{case_id}_titles.json"
        with open(titles_file, "w") as f:
            json.dump(titles, f, indent=2)
        
        print(f"Titles saved to {titles_file}")
    else:
        print("No titles found from external source")


if __name__ == "__main__":
    # Get case ID from command line argument or use default
    case_id = int(sys.argv[1]) if len(sys.argv) > 1 else 8835
    
    # Get API key from environment or prompt user
    api_key = os.environ.get("QUEPID_API_KEY")
    if not api_key:
        api_key = input("Enter your Quepid API key: ")
    
    # Run the async function
    asyncio.run(main(case_id, api_key)) 