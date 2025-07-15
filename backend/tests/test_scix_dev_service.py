"""
Tests for the SciX Development service module.

This module tests the functionality of the SciX Development service for
retrieving search results from the development API endpoint.
"""
import os
from unittest.mock import patch, AsyncMock
import pytest
from typing import List

from app.services.scix_dev_service import (
    get_scix_dev_results,
    get_scix_dev_paper_details
)
from app.api.models import SearchResult


class TestSciXDevService:
    """Test cases for SciX Development service."""

    @pytest.mark.asyncio
    async def test_get_scix_dev_results_no_endpoint(self, caplog):
        """Test that service returns empty results when endpoint is not configured."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove SCIX_DEV_ENDPOINT if it exists
            if 'SCIX_DEV_ENDPOINT' in os.environ:
                del os.environ['SCIX_DEV_ENDPOINT']
            
            results = await get_scix_dev_results("test query", num_results=10)
            
            assert results == []
            assert "SCIX_DEV_ENDPOINT environment variable not set" in caplog.text

    @pytest.mark.asyncio
    async def test_get_scix_dev_results_with_endpoint(self, caplog):
        """Test that service logs appropriately when endpoint is configured."""
        with patch.dict(os.environ, {'SCIX_DEV_ENDPOINT': 'http://dev.example.com/api'}):
            results = await get_scix_dev_results("test query", num_results=10)
            
            assert results == []
            assert "SciX Development API not yet implemented" in caplog.text

    @pytest.mark.asyncio
    async def test_get_scix_dev_results_parameters(self, caplog):
        """Test that service properly handles different parameter combinations."""
        with patch.dict(os.environ, {'SCIX_DEV_ENDPOINT': 'http://dev.example.com/api'}):
            # Test with different parameters
            results = await get_scix_dev_results(
                "quantum mechanics",
                fields=["title", "abstract", "author"],
                num_results=20
            )
            
            assert results == []
            assert "Query: 'quantum mechanics'" in caplog.text
            assert "num_results: 20" in caplog.text

    @pytest.mark.asyncio
    async def test_get_scix_dev_paper_details_no_endpoint(self, caplog):
        """Test paper details function when endpoint is not configured."""
        with patch.dict(os.environ, {}, clear=True):
            if 'SCIX_DEV_ENDPOINT' in os.environ:
                del os.environ['SCIX_DEV_ENDPOINT']
            
            result = await get_scix_dev_paper_details("10.1234/test.doi")
            
            assert result == {}
            assert "SCIX_DEV_ENDPOINT environment variable not set" in caplog.text

    @pytest.mark.asyncio
    async def test_get_scix_dev_paper_details_with_endpoint(self, caplog):
        """Test paper details function when endpoint is configured."""
        with patch.dict(os.environ, {'SCIX_DEV_ENDPOINT': 'http://dev.example.com/api'}):
            result = await get_scix_dev_paper_details("10.1234/test.doi")
            
            assert result == {}
            assert "Getting paper details for DOI: 10.1234/test.doi" in caplog.text
            assert "SciX Development paper details API not yet implemented" in caplog.text

    @pytest.mark.asyncio
    async def test_service_integration_with_search_service(self):
        """Test that the service integrates properly with the search service."""
        # This test ensures the service can be imported and called as expected
        # by the search service's query_source function
        
        with patch.dict(os.environ, {'SCIX_DEV_ENDPOINT': 'http://dev.example.com/api'}):
            # Test that the function signature matches what's expected
            results = await get_scix_dev_results("test", ["title"], 10)
            assert isinstance(results, list)
            assert all(isinstance(r, SearchResult) for r in results)

    # Future test for when actual API is implemented
    @pytest.mark.asyncio
    @pytest.mark.skip("Will be enabled when actual API is implemented")
    async def test_get_scix_dev_results_with_actual_api(self):
        """Test with actual API implementation (placeholder for future)."""
        # This test will be updated once the actual SciX Development API is ready
        # It should test:
        # - Actual HTTP requests to the development endpoint
        # - Proper parsing of real API responses
        # - Error handling for API failures
        # - Result formatting to SearchResult objects
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip("Will be enabled when actual API is implemented")
    async def test_get_scix_dev_paper_details_with_actual_api(self):
        """Test paper details with actual API implementation (placeholder for future)."""
        # This test will be updated once the actual SciX Development API is ready
        # It should test:
        # - Actual HTTP requests for paper details
        # - DOI validation and formatting
        # - Error handling for invalid DOIs
        # - Response parsing and formatting
        pass


class TestSciXDevServiceInSearchService:
    """Test SciX Development service integration with the main search service."""

    @pytest.mark.asyncio
    async def test_scix_dev_in_service_config(self):
        """Test that SciX Development is properly configured in SERVICE_CONFIG."""
        from app.services.search_service import SERVICE_CONFIG
        
        assert "sciXDev" in SERVICE_CONFIG
        assert SERVICE_CONFIG["sciXDev"]["enabled"] is True
        assert SERVICE_CONFIG["sciXDev"]["priority"] == 5
        assert SERVICE_CONFIG["sciXDev"]["timeout"] == 15
        assert SERVICE_CONFIG["sciXDev"]["min_results"] == 0

    @pytest.mark.asyncio
    async def test_scix_dev_in_search_results(self):
        """Test that SciX Development results are handled in search service."""
        from app.services.search_service import get_results_with_fallback
        
        with patch.dict(os.environ, {'SCIX_DEV_ENDPOINT': 'http://dev.example.com/api'}):
            results = await get_results_with_fallback(
                query="test",
                sources=["sciXDev"],
                fields=["title", "abstract"],
                max_results=10
            )
            
            assert "sciXDev" in results
            assert isinstance(results["sciXDev"], list)

    @pytest.mark.asyncio
    async def test_scix_dev_with_other_sources(self):
        """Test SciX Development alongside other sources."""
        from app.services.search_service import get_results_with_fallback
        
        with patch.dict(os.environ, {'SCIX_DEV_ENDPOINT': 'http://dev.example.com/api'}):
            # Mock other services to avoid actual API calls
            with patch('app.services.ads_service.get_ads_results', return_value=[]):
                results = await get_results_with_fallback(
                    query="test",
                    sources=["ads", "sciXDev"],
                    fields=["title", "abstract"],
                    max_results=10
                )
                
                assert "ads" in results
                assert "sciXDev" in results
                assert isinstance(results["ads"], list)
                assert isinstance(results["sciXDev"], list)


# Test fixtures for future API implementation
@pytest.fixture
def mock_scix_dev_api_response():
    """Mock response for SciX Development API (for future use)."""
    return {
        "results": [
            {
                "title": "Test Paper from SciX Dev",
                "abstract": "Test abstract from development API",
                "authors": ["Test Author"],
                "year": 2024,
                "doi": "10.1234/test.dev.doi",
                "citation_count": 5,
                "bibcode": "2024TestDevPaper"
            }
        ],
        "total": 1
    }


@pytest.fixture
def mock_scix_dev_paper_details_response():
    """Mock paper details response for SciX Development API (for future use)."""
    return {
        "doi": "10.1234/test.dev.doi",
        "title": "Test Paper Details from SciX Dev",
        "abstract": "Detailed abstract from development API",
        "authors": ["Test Author", "Another Author"],
        "year": 2024,
        "journal": "Test Development Journal",
        "citation_count": 10,
        "references": ["ref1", "ref2"],
        "bibcode": "2024TestDevPaper"
    }
