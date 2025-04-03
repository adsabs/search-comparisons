"""
Tests for retrieving title metadata from Quepid judgments.

This module contains tests specifically focused on retrieving title
metadata from Quepid judgments for case 8835.
"""
import json
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import pytest
from unittest.mock import MagicMock, patch

from app.services.quepid_service import (
    QuepidJudgment,
    QuepidCase,
    load_case_with_judgments,
    get_case_judgments,
    get_judgment_titles_from_case,
    get_flat_judgment_titles_from_case
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def mock_judgment_with_title() -> QuepidJudgment:
    """
    Create a mock Quepid judgment with title metadata for testing.
    
    Returns:
        QuepidJudgment: A mock judgment object with title metadata
    """
    return QuepidJudgment(
        query_text="example query",
        doc_id="10.1234/document123",
        rating=3,
        metadata={"title": "Example Document Title"}
    )


@pytest.fixture
def mock_judgments_response() -> Dict[str, Any]:
    """
    Create a mock response from the Quepid API for judgments.
    
    Returns:
        Dict[str, Any]: Mock API response for judgments
    """
    return {
        "ratings": [
            {
                "query_text": "example query",
                "doc_id": "10.1234/document123",
                "rating": 3,
                "title": "Example Document Title",
                "other_field": "other value"
            },
            {
                "query_text": "example query",
                "doc_id": "10.5678/document456",
                "rating": 2,
                "title": "Another Document Title",
                "publication_date": "2021"
            }
        ]
    }


@patch('app.services.quepid_service.safe_api_request')
@pytest.mark.asyncio
async def test_judgment_metadata_includes_title(
    mock_safe_request: MagicMock, 
    mock_judgments_response: Dict[str, Any]
) -> None:
    """
    Test that judgment metadata includes title information.
    
    Args:
        mock_safe_request: Mocked API request function
        mock_judgments_response: Mock judgment response data
    """
    # Configure the mock to return the judgment response
    mock_safe_request.return_value = mock_judgments_response
    
    # Mock the QUEPID_API_KEY to avoid the environment check failing
    with patch('app.services.quepid_service.QUEPID_API_KEY', 'mock_api_key'):
        # Call the function to get judgments
        result = await get_case_judgments(case_id=8835)
        
        # Verify the result contains the expected data
        assert "ratings" in result
        assert len(result["ratings"]) == 2
        
        # Check that titles are present in the raw response
        for rating in result["ratings"]:
            assert "title" in rating
        
        # Check the first judgment's title
        assert result["ratings"][0]["title"] == "Example Document Title"


@patch('app.services.quepid_service.get_case_judgments')
@patch('app.services.quepid_service.safe_api_request')
@pytest.mark.asyncio
async def test_load_case_preserves_title_in_metadata(
    mock_safe_request: MagicMock,
    mock_get_judgments: MagicMock,
    mock_judgments_response: Dict[str, Any]
) -> None:
    """
    Test that load_case_with_judgments preserves title in judgment metadata.
    
    Args:
        mock_safe_request: Mocked API request function
        mock_get_judgments: Mocked get_case_judgments function
        mock_judgments_response: Mock judgment response data
    """
    # Configure mocks
    mock_safe_request.return_value = {
        "name": "Test Case 8835",
        "id": 8835
    }
    mock_get_judgments.return_value = mock_judgments_response
    
    # Call the function to load case with judgments
    case = await load_case_with_judgments(case_id=8835)
    
    # Verify the case is loaded correctly
    assert case is not None
    assert case.case_id == 8835
    assert case.name == "Test Case 8835"
    
    # Verify queries are extracted
    assert "example query" in case.queries
    
    # Verify judgments are created with metadata
    judgments = case.judgments["example query"]
    assert len(judgments) == 2
    
    # Check that titles are preserved in metadata
    assert "title" in judgments[0].metadata
    assert judgments[0].metadata["title"] == "Example Document Title"
    
    # Check the second judgment
    assert "title" in judgments[1].metadata
    assert judgments[1].metadata["title"] == "Another Document Title"


@pytest.mark.asyncio
async def test_real_case_8835_has_titles() -> None:
    """
    Integration test to check if real case 8835 contains title metadata.
    
    This test uses a mock to simulate the real case 8835.
    """
    # Create a mock case response
    case_data = {
        "name": "Test Case 8835",
        "id": 8835
    }
    
    # Create a mock judgment response with titles
    judgments_data = {
        "ratings": [
            {
                "query_text": "space weather",
                "doc_id": "10.1029/2018SW002067",
                "rating": 3,
                "title": "Space Weather: The Effects on Operations and Mitigation Strategies—Past, Present, and Future"
            },
            {
                "query_text": "space weather",
                "doc_id": "10.1029/2019SW002278",
                "rating": 2,
                "title": "Space Weather: What Is It, How Will It Affect Us, and How Do We Prepare?"
            },
            {
                "query_text": "solar storms",
                "doc_id": "10.1063/PT.3.2908",
                "rating": 3,
                "title": "Space Weather: Challenges and opportunities"
            }
        ]
    }
    
    # Mock the API requests
    with patch('app.services.quepid_service.safe_api_request') as mock_request, \
         patch('app.services.quepid_service.get_case_judgments') as mock_get_judgments:
        
        # Configure mocks
        mock_request.return_value = case_data
        mock_get_judgments.return_value = judgments_data
        
        # Load the case with mocked data
        case = await load_case_with_judgments(case_id=8835)
        
        # Verify we could load the case
        assert case is not None, "Failed to load case 8835"
        assert case.case_id == 8835
        
        # Check that we have queries and judgments
        assert len(case.queries) > 0, "Case has no queries"
        
        # Examine each query and its judgments for title metadata
        title_counts = 0
        total_judgments = 0
        
        print("\nTitle metadata in case 8835:")
        for query in case.queries:
            judgments = case.judgments.get(query, [])
            total_judgments += len(judgments)
            
            for judgment in judgments:
                if "title" in judgment.metadata:
                    title_counts += 1
                    # Print the first few titles for manual verification
                    if title_counts <= 5:
                        print(f"Query: {query}, Doc ID: {judgment.doc_id}, Title: {judgment.metadata['title']}")
        
        # Report how many judgments have title metadata
        print(f"\nFound {title_counts} judgments with titles out of {total_judgments} total judgments")
        
        # For this test to pass, we expect at least some judgments to have titles
        assert title_counts > 0, "No judgments have title metadata"


def test_extract_title_from_judgment(mock_judgment_with_title: QuepidJudgment) -> None:
    """
    Test extracting title from a judgment object.
    
    Args:
        mock_judgment_with_title: A mock judgment with title metadata
    """
    # Verify we can access the title from the metadata
    assert "title" in mock_judgment_with_title.metadata
    title = mock_judgment_with_title.metadata.get("title")
    assert title == "Example Document Title"


def test_get_judgment_titles_from_case(mock_judgment_with_title: QuepidJudgment) -> None:
    """
    Test extracting titles from all judgments in a case.
    
    Args:
        mock_judgment_with_title: A mock judgment with title metadata
    """
    # Create a test case with judgments
    case = QuepidCase(
        case_id=999,
        name="Test Case",
        queries=["example query", "another query"],
        judgments={
            "example query": [
                mock_judgment_with_title,
                QuepidJudgment(
                    query_text="example query",
                    doc_id="10.5678/another",
                    rating=2,
                    metadata={"title": "Another Title"}
                )
            ],
            "another query": [
                QuepidJudgment(
                    query_text="another query",
                    doc_id="10.9876/document",
                    rating=1,
                    metadata={"title": "Third Document"}
                )
            ]
        }
    )
    
    # Test the utility function for hierarchical title extraction
    titles_by_query = get_judgment_titles_from_case(case)
    
    # Verify we extracted the expected titles
    assert len(titles_by_query) == 2
    assert "example query" in titles_by_query
    assert "another query" in titles_by_query
    
    assert len(titles_by_query["example query"]) == 2
    assert titles_by_query["example query"]["10.1234/document123"] == "Example Document Title"
    assert titles_by_query["example query"]["10.5678/another"] == "Another Title"
    
    assert len(titles_by_query["another query"]) == 1
    assert titles_by_query["another query"]["10.9876/document"] == "Third Document"
    
    # Test the utility function for flat title extraction
    flat_titles = get_flat_judgment_titles_from_case(case)
    
    # Verify we extracted the expected titles
    assert len(flat_titles) == 3
    assert flat_titles["10.1234/document123"] == "Example Document Title"
    assert flat_titles["10.5678/another"] == "Another Title"
    assert flat_titles["10.9876/document"] == "Third Document"


@pytest.mark.asyncio
async def test_real_case_8835_title_extraction() -> None:
    """
    Integration test to extract titles from real case 8835.
    
    This test uses a mock to simulate the real case 8835.
    """
    # Create a mock case response
    case_data = {
        "name": "Test Case 8835",
        "id": 8835
    }
    
    # Create a mock judgment response with titles
    judgments_data = {
        "ratings": [
            {
                "query_text": "space weather",
                "doc_id": "10.1029/2018SW002067",
                "rating": 3,
                "title": "Space Weather: The Effects on Operations and Mitigation Strategies—Past, Present, and Future"
            },
            {
                "query_text": "space weather",
                "doc_id": "10.1029/2019SW002278",
                "rating": 2,
                "title": "Space Weather: What Is It, How Will It Affect Us, and How Do We Prepare?"
            },
            {
                "query_text": "solar storms",
                "doc_id": "10.1063/PT.3.2908",
                "rating": 3,
                "title": "Space Weather: Challenges and opportunities"
            }
        ]
    }
    
    # Mock the API requests
    with patch('app.services.quepid_service.safe_api_request') as mock_request, \
         patch('app.services.quepid_service.get_case_judgments') as mock_get_judgments:
        
        # Configure mocks
        mock_request.return_value = case_data
        mock_get_judgments.return_value = judgments_data
        
        # Load the case with mocked data
        case = await load_case_with_judgments(case_id=8835)
        
        # Verify we could load the case
        assert case is not None, "Failed to load case 8835"
        
        # Extract titles using the utility functions
        titles_by_query = get_judgment_titles_from_case(case)
        flat_titles = get_flat_judgment_titles_from_case(case)
        
        # Print some titles for verification
        print("\nHierarchical titles from case 8835:")
        for query, doc_titles in titles_by_query.items():
            print(f"Query: {query}, Number of documents with titles: {len(doc_titles)}")
            # Print a few examples
            count = 0
            for doc_id, title in doc_titles.items():
                if count < 2:  # Only print 2 examples per query
                    print(f"  Doc ID: {doc_id}, Title: {title}")
                    count += 1
        
        print(f"\nTotal number of documents with titles: {len(flat_titles)}")
        
        # For this test to pass, we expect at least some titles to be extracted
        assert len(flat_titles) > 0, "No titles found in case 8835"
        
        # Verify specific titles are extracted correctly
        assert "10.1029/2018SW002067" in flat_titles
        assert flat_titles["10.1029/2018SW002067"] == "Space Weather: The Effects on Operations and Mitigation Strategies—Past, Present, and Future" 