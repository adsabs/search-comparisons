#!/usr/bin/env python3
"""
Calculate exact doctype boost values for current and modified rankings.
"""

def calculate_doctype_boost(doctype: str, doctype_ranks: dict) -> float:
    """Calculate doctype boost using the same logic as boost_service.py"""
    doctype = doctype.lower() if doctype else 'other'
    
    # Get rank for doctype, default to 'other' if not found
    rank = doctype_ranks.get(doctype, doctype_ranks['other'])
    
    # Get unique ranks and sort them
    unique_ranks = sorted(set(doctype_ranks.values()))
    
    # Calculate boost factor using even distribution
    rank_index = unique_ranks.index(rank)
    num_unique_ranks = len(unique_ranks)
    
    # Avoid division by zero if there's only one rank
    if num_unique_ranks <= 1:
        return 1.0
        
    return 1.0 - (rank_index / (num_unique_ranks - 1))

def analyze_doctype_boosts():
    print("=== Doctype Boost Analysis ===\n")
    
    # Current frontend configuration
    current_ranks = {
        'article': 1,      # Journal article
        'book': 2,         # Book  
        'inbook': 3,       # Book chapter
        'proceedings': 4,  # Conference proceedings
        'inproceedings': 5,# Conference paper
        'phdthesis': 6,    # PhD thesis
        'mastersthesis': 7,# Masters thesis
        'techreport': 8,   # Technical report
        'preprint': 9,     # Preprint
        'abstract': 10,    # Abstract
        'other': 11        # Other/unknown
    }
    
    # Modified ranks - book gets higher priority than article
    modified_ranks = current_ranks.copy()
    modified_ranks['book'] = 0  # Give book the highest rank
    modified_ranks['article'] = 1  # Article gets second place
    
    print("Current Frontend Ranks:")
    print(f"  article: {current_ranks['article']}")
    print(f"  book: {current_ranks['book']}")
    print(f"  unique ranks: {sorted(set(current_ranks.values()))}")
    print(f"  total unique ranks: {len(set(current_ranks.values()))}")
    
    article_boost_current = calculate_doctype_boost('article', current_ranks)
    book_boost_current = calculate_doctype_boost('book', current_ranks)
    
    print(f"\nCurrent Boost Values:")
    print(f"  article boost: {article_boost_current:.6f}")
    print(f"  book boost: {book_boost_current:.6f}")
    print(f"  difference (article - book): {article_boost_current - book_boost_current:.6f}")
    
    print("\n" + "="*50 + "\n")
    
    print("Modified Ranks (book > article):")
    print(f"  book: {modified_ranks['book']}")
    print(f"  article: {modified_ranks['article']}")
    print(f"  unique ranks: {sorted(set(modified_ranks.values()))}")
    print(f"  total unique ranks: {len(set(modified_ranks.values()))}")
    
    article_boost_modified = calculate_doctype_boost('article', modified_ranks)
    book_boost_modified = calculate_doctype_boost('book', modified_ranks)
    
    print(f"\nModified Boost Values:")
    print(f"  book boost: {book_boost_modified:.6f}")
    print(f"  article boost: {article_boost_modified:.6f}")
    print(f"  difference (book - article): {book_boost_modified - article_boost_modified:.6f}")
    
    print("\n" + "="*50 + "\n")
    
    print("Change Analysis:")
    article_change = article_boost_modified - article_boost_current
    book_change = book_boost_modified - book_boost_current
    
    print(f"  article boost change: {article_change:+.6f}")
    print(f"  book boost change: {book_change:+.6f}")
    print(f"  total swing: {(book_change - article_change):.6f}")
    
    print(f"\nRank Position Details:")
    
    # Current ranks analysis
    current_unique = sorted(set(current_ranks.values()))
    article_rank_pos = current_unique.index(current_ranks['article'])
    book_rank_pos = current_unique.index(current_ranks['book'])
    
    print(f"Current:")
    print(f"  article rank {current_ranks['article']} -> position {article_rank_pos} of {len(current_unique)-1} -> boost = 1.0 - ({article_rank_pos}/{len(current_unique)-1}) = {article_boost_current:.6f}")
    print(f"  book rank {current_ranks['book']} -> position {book_rank_pos} of {len(current_unique)-1} -> boost = 1.0 - ({book_rank_pos}/{len(current_unique)-1}) = {book_boost_current:.6f}")
    
    # Modified ranks analysis  
    modified_unique = sorted(set(modified_ranks.values()))
    article_rank_pos_mod = modified_unique.index(modified_ranks['article'])
    book_rank_pos_mod = modified_unique.index(modified_ranks['book'])
    
    print(f"Modified:")
    print(f"  book rank {modified_ranks['book']} -> position {book_rank_pos_mod} of {len(modified_unique)-1} -> boost = 1.0 - ({book_rank_pos_mod}/{len(modified_unique)-1}) = {book_boost_modified:.6f}")
    print(f"  article rank {modified_ranks['article']} -> position {article_rank_pos_mod} of {len(modified_unique)-1} -> boost = 1.0 - ({article_rank_pos_mod}/{len(modified_unique)-1}) = {article_boost_modified:.6f}")

if __name__ == "__main__":
    analyze_doctype_boosts()
