"""
Example script for retrieving title metadata from Quepid judgments.

This script demonstrates how to load a Quepid case and extract title metadata
from its judgments for display in the application.
"""
import os
import sys
import asyncio
import json
from pathlib import Path
import httpx
from urllib.parse import urljoin

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def get_titles_from_quepid(case_id: int, api_key: str) -> None:
    """
    Function to get titles using Quepid API.
    
    Args:
        case_id: The Quepid case ID to retrieve titles from
        api_key: The Quepid API key
    """
    # API Constants
    api_url = "https://app.quepid.com/api/"
    
    print(f"Accessing Quepid API for case {case_id}...")
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # First get case details to see the queries
            case_url = urljoin(api_url, f"cases/{case_id}")
            print(f"Getting case details: {case_url}")
            
            case_response = await client.get(case_url, headers=headers, timeout=30)
            
            if case_response.status_code != 200:
                print(f"Error getting case: HTTP {case_response.status_code} - {case_response.text}")
                return
            
            case_data = case_response.json()
            
            print("\nCase information:")
            print(f"Name: {case_data.get('name', 'Unknown')}")
            
            # Get the queries from the case
            queries = case_data.get("queries", [])
            print(f"Number of queries in case: {len(queries)}")
            
            # Show sample queries
            print("\nSample queries:")
            for i, query in enumerate(queries[:5]):  # Show first 5 queries
                print(f"{i+1}. {query.get('query_text', 'Unknown query')}")
            
            # Get the ratings data
            ratings_url = urljoin(api_url, f"export/ratings/{case_id}")
            print(f"\nGetting ratings data: {ratings_url}")
            
            ratings_response = await client.get(ratings_url, headers=headers, timeout=30)
            
            if ratings_response.status_code != 200:
                print(f"Error getting ratings: HTTP {ratings_response.status_code} - {ratings_response.text}")
                return
            
            ratings_data = ratings_response.json()
            
            # Try to get the document IDs from the ratings
            all_doc_ids = set()
            if "ratings" in ratings_data:
                # The flat ratings format
                ratings = ratings_data["ratings"]
                for rating in ratings:
                    doc_id = rating.get("doc_id")
                    if doc_id:
                        all_doc_ids.add(doc_id)
            elif "queries" in ratings_data:
                # The nested queries format
                for query in ratings_data["queries"]:
                    ratings_dict = query.get("ratings", {})
                    if ratings_dict:
                        all_doc_ids.update(ratings_dict.keys())
            
            if not all_doc_ids:
                print("No document IDs found in ratings")
                return
            
            print(f"\nFound {len(all_doc_ids)} unique document IDs with ratings")
            print("Sample document IDs:", list(all_doc_ids)[:5])
            
            # Now try to get the book IDs for the case
            book_titles = {}
            books_found = False
            
            # Check if we can find any books associated with this case
            try:
                # First check if the case data has books
                if "books" in case_data:
                    books_found = True
                    books = case_data["books"]
                    print(f"\nFound {len(books)} books in case data")
                    
                    # Process each book
                    for book in books:
                        book_id = book.get("id")
                        if not book_id:
                            continue
                        
                        print(f"\nProcessing book ID: {book_id}")
                        
                        # Get query_doc_pairs for this book
                        qdp_url = urljoin(api_url, f"books/{book_id}/query_doc_pairs")
                        print(f"Getting query_doc_pairs: {qdp_url}")
                        
                        qdp_response = await client.get(qdp_url, headers=headers, timeout=30)
                        
                        if qdp_response.status_code != 200:
                            print(f"Error getting query_doc_pairs: HTTP {qdp_response.status_code}")
                            continue
                        
                        qdp_data = qdp_response.json()
                        
                        # Check for title in the query_doc_pairs
                        if "query_doc_pairs" in qdp_data:
                            pairs = qdp_data["query_doc_pairs"]
                            print(f"Found {len(pairs)} query_doc_pairs")
                            
                            # Extract titles
                            for pair in pairs:
                                doc_id = pair.get("doc_id")
                                title = pair.get("title")
                                
                                if doc_id and title:
                                    book_titles[doc_id] = title
                            
                            print(f"Extracted {len(book_titles)} titles from query_doc_pairs")
                else:
                    print("\nNo books found in case data")
            except Exception as e:
                print(f"Error processing books: {str(e)}")
            
            # If we didn't find books in the case data, try the direct book endpoint
            if not books_found:
                try:
                    # Get a list of all books
                    books_url = urljoin(api_url, "books")
                    print(f"\nGetting all books: {books_url}")
                    
                    books_response = await client.get(books_url, headers=headers, timeout=30)
                    
                    if books_response.status_code == 200:
                        books_data = books_response.json()
                        
                        if isinstance(books_data, list):
                            books = books_data
                        elif isinstance(books_data, dict) and "books" in books_data:
                            books = books_data["books"]
                        else:
                            books = []
                        
                        print(f"Found {len(books)} books total")
                        
                        # Try to find books related to our case
                        for book in books:
                            book_id = book.get("id")
                            book_name = book.get("name", "Unknown")
                            
                            print(f"\nChecking book: {book_name} (ID: {book_id})")
                            
                            # Get judgments for this book
                            judgments_url = urljoin(api_url, f"books/{book_id}/judgements")
                            print(f"Getting judgments: {judgments_url}")
                            
                            try:
                                judgments_response = await client.get(judgments_url, headers=headers, timeout=30)
                                
                                if judgments_response.status_code == 200:
                                    judgments_data = judgments_response.json()
                                    
                                    # Check if any of our document IDs are in the judgments
                                    if "judgements" in judgments_data:
                                        judgments = judgments_data["judgements"]
                                        matching_doc_ids = 0
                                        
                                        for judgment in judgments:
                                            doc_id = judgment.get("doc_id")
                                            if doc_id in all_doc_ids:
                                                matching_doc_ids += 1
                                                
                                                # If title is available in the judgment, store it
                                                if "title" in judgment:
                                                    book_titles[doc_id] = judgment["title"]
                                        
                                        if matching_doc_ids > 0:
                                            print(f"Found {matching_doc_ids} matching document IDs in book {book_id}")
                                            if book_titles:
                                                print(f"Extracted {len(book_titles)} titles from judgments")
                            except Exception as e:
                                print(f"Error getting judgments for book {book_id}: {str(e)}")
                    else:
                        print(f"Error getting books: HTTP {books_response.status_code}")
                except Exception as e:
                    print(f"Error processing books endpoint: {str(e)}")
            
            # If we have any titles, save them
            if book_titles:
                print(f"\nFound titles for {len(book_titles)} document IDs")
                
                # Print some example titles
                print("\nExample titles:")
                for i, (doc_id, title) in enumerate(book_titles.items()):
                    if i < 5:  # Print only first 5 titles
                        print(f"Doc ID: {doc_id}")
                        print(f"Title: {title}")
                        print()
                    else:
                        break
                
                # Save titles to a JSON file for reference
                output_file = f"quepid_case_{case_id}_titles.json"
                with open(output_file, "w") as f:
                    json.dump(book_titles, f, indent=2)
                
                print(f"Titles saved to {output_file}")
            else:
                print("\nNo titles found for any document IDs")
                print("It appears this case or Quepid instance doesn't store title metadata.")
                print("You may need to get titles from an external source using the document IDs.")
                
                # Save document IDs to a file for reference
                doc_ids_file = f"quepid_case_{case_id}_doc_ids.json"
                with open(doc_ids_file, "w") as f:
                    json.dump(list(all_doc_ids), f, indent=2)
                
                print(f"Document IDs saved to {doc_ids_file}")
    
    except Exception as e:
        print(f"Error accessing Quepid API: {str(e)}")


if __name__ == "__main__":
    # Get case ID from command line argument or use default
    case_id = int(sys.argv[1]) if len(sys.argv) > 1 else 8835
    
    # Get API key from environment or prompt user
    api_key = os.environ.get("QUEPID_API_KEY")
    if not api_key:
        api_key = input("Enter your Quepid API key: ")
    
    # Run the async function
    asyncio.run(get_titles_from_quepid(case_id, api_key)) 