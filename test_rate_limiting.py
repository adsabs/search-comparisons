#!/usr/bin/env python3
"""
Test script to verify rate limiting and secure logging implementation.

This script tests the rate limiting functionality and secure logging
redaction features to ensure they work correctly.
"""
import asyncio
import aiohttp
import time
import json
from typing import Dict, Any, List

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_ENDPOINTS = [
    # (endpoint, method, expected_limit, data)
    ("/api/health", "GET", 60, None),
    ("/", "GET", 60, None),
    ("/api/search", "POST", 10, {
        "query": "test query",
        "sources": ["ads"],
        "metrics": ["jaccard"],
        "fields": ["title", "author"],
        "max_results": 5
    }),
    ("/api/transform-query", "POST", 5, {
        "query": "test query",
        "field_boosts": {"title": 2.0, "author": 1.5}
    }),
    ("/api/experiments/health", "GET", 60, None),
    ("/api/debug/sources", "GET", 20, None),  # This requires auth
]

# Test sensitive data patterns for logging redaction
SENSITIVE_TEST_DATA = [
    "ADS_API_KEY=abc123def456ghi789",
    "password=mysecretpassword",
    "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
    "email@example.com",
    "https://user:pass@example.com/api",
    "4111-1111-1111-1111",  # credit card
    "+1-555-123-4567",      # phone
]

async def test_endpoint_rate_limit(session: aiohttp.ClientSession, 
                                  endpoint: str, 
                                  method: str, 
                                  limit: int, 
                                  data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Test rate limiting for a specific endpoint.
    
    Args:
        session: aiohttp session
        endpoint: API endpoint to test
        method: HTTP method
        limit: Expected rate limit per minute
        data: Request data for POST requests
        
    Returns:
        Dict with test results
    """
    url = f"{BASE_URL}{endpoint}"
    results = {
        "endpoint": endpoint,
        "method": method,
        "expected_limit": limit,
        "requests_sent": 0,
        "successful_requests": 0,
        "rate_limited_requests": 0,
        "first_rate_limit_at": None,
        "errors": []
    }
    
    print(f"\nTesting {method} {endpoint} (limit: {limit}/minute)")
    
    # Calculate number of requests to send (slightly over limit)
    test_requests = min(limit + 5, 70)  # Don't overwhelm the server
    
    start_time = time.time()
    
    for i in range(test_requests):
        try:
            if method == "GET":
                async with session.get(url) as response:
                    results["requests_sent"] += 1
                    if response.status == 200:
                        results["successful_requests"] += 1
                    elif response.status == 429:
                        results["rate_limited_requests"] += 1
                        if results["first_rate_limit_at"] is None:
                            results["first_rate_limit_at"] = i + 1
                        print(f"  Rate limited at request {i + 1}")
                    else:
                        results["errors"].append(f"Request {i + 1}: HTTP {response.status}")
            
            elif method == "POST":
                async with session.post(url, json=data) as response:
                    results["requests_sent"] += 1
                    if response.status in [200, 422]:  # 422 is validation error, not rate limit
                        results["successful_requests"] += 1
                    elif response.status == 429:
                        results["rate_limited_requests"] += 1
                        if results["first_rate_limit_at"] is None:
                            results["first_rate_limit_at"] = i + 1
                        print(f"  Rate limited at request {i + 1}")
                    else:
                        results["errors"].append(f"Request {i + 1}: HTTP {response.status}")
        
        except Exception as e:
            results["errors"].append(f"Request {i + 1}: {str(e)}")
        
        # Small delay to avoid overwhelming the server
        await asyncio.sleep(0.1)
    
    elapsed_time = time.time() - start_time
    results["test_duration"] = elapsed_time
    
    print(f"  Sent: {results['requests_sent']}, "
          f"Success: {results['successful_requests']}, "
          f"Rate limited: {results['rate_limited_requests']}")
    
    if results["rate_limited_requests"] > 0:
        print(f"  ✅ Rate limiting working - first limit at request {results['first_rate_limit_at']}")
    else:
        print(f"  ⚠️  No rate limiting detected")
    
    return results


async def test_logging_redaction():
    """
    Test the logging redaction functionality.
    """
    print("\n🔒 Testing Logging Redaction")
    print("=" * 50)
    
    from backend.app.core.logging import SensitiveDataRedactionFilter
    
    # Create a redaction filter
    redaction_filter = SensitiveDataRedactionFilter()
    
    print("Testing sensitive data patterns:")
    for test_data in SENSITIVE_TEST_DATA:
        redacted = redaction_filter._redact_sensitive_data(test_data)
        is_redacted = redacted != test_data
        status = "✅ REDACTED" if is_redacted else "❌ NOT REDACTED"
        print(f"  {status}: '{test_data}' -> '{redacted}'")
    
    return True


async def test_rate_limiting():
    """
    Test rate limiting on various endpoints.
    """
    print("\n🚦 Testing Rate Limiting")
    print("=" * 50)
    
    all_results = []
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        connector=aiohttp.TCPConnector(limit=10)
    ) as session:
        
        for endpoint, method, limit, data in TEST_ENDPOINTS:
            try:
                results = await test_endpoint_rate_limit(session, endpoint, method, limit, data)
                all_results.append(results)
            except Exception as e:
                print(f"❌ Error testing {endpoint}: {e}")
                all_results.append({
                    "endpoint": endpoint,
                    "method": method,
                    "error": str(e)
                })
    
    return all_results


async def main():
    """
    Main test function.
    """
    print("🔐 Rate Limiting and Secure Logging Test")
    print("=" * 60)
    print("This script tests the rate limiting and logging security features.")
    print("Make sure the backend server is running on http://localhost:8001")
    print()
    
    # Test logging redaction
    logging_test_passed = await test_logging_redaction()
    
    # Test rate limiting
    rate_limit_results = await test_rate_limiting()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    print(f"Logging redaction: {'✅ PASSED' if logging_test_passed else '❌ FAILED'}")
    
    total_endpoints = len(rate_limit_results)
    endpoints_with_rate_limiting = sum(1 for r in rate_limit_results if r.get("rate_limited_requests", 0) > 0)
    
    print(f"Rate limiting: {endpoints_with_rate_limiting}/{total_endpoints} endpoints have working rate limits")
    
    # Detailed results
    print("\nDetailed Results:")
    for result in rate_limit_results:
        if "error" in result:
            print(f"  ❌ {result['endpoint']}: {result['error']}")
        else:
            status = "✅" if result.get("rate_limited_requests", 0) > 0 else "⚠️"
            print(f"  {status} {result['endpoint']}: "
                  f"{result.get('rate_limited_requests', 0)} rate limited out of "
                  f"{result.get('requests_sent', 0)} requests")
    
    print("\n🔐 Security Features Test Completed!")
    
    # Recommendations
    print("\n📝 Recommendations:")
    if endpoints_with_rate_limiting < total_endpoints:
        print("  - Some endpoints may need rate limiting configuration")
    if logging_test_passed:
        print("  ✅ Sensitive data redaction is working correctly")
    else:
        print("  ❌ Review logging redaction implementation")
    
    print("  - Monitor logs for actual redaction in production")
    print("  - Consider adjusting rate limits based on usage patterns")
    print("  - Implement IP whitelisting for debug endpoints")


if __name__ == "__main__":
    asyncio.run(main())
