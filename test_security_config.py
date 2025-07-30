#!/usr/bin/env python3
"""
Security configuration test script.

Tests the security configurations for debug endpoints, CORS, and TrustedHost settings.
"""
import asyncio
import aiohttp
import os
import sys
from typing import Dict, Any


async def test_debug_endpoints_disabled() -> Dict[str, Any]:
    """Test that debug endpoints are properly secured when disabled."""
    results = {}
    base_url = "http://localhost:8001"
    
    debug_endpoints = [
        "/api/debug/env",
        "/api/debug/sources", 
        "/api/debug/ping/ads",
        "/api/debug/search/ads?query=test&limit=1",
        "/api/debug/request-headers"
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in debug_endpoints:
            try:
                async with session.get(f"{base_url}{endpoint}") as response:
                    status = response.status
                    text = await response.text()
                    
                    if status == 403:
                        results[endpoint] = "✅ SECURED (403 Forbidden)"
                    elif status == 401:
                        results[endpoint] = "✅ SECURED (401 Unauthorized)" 
                    else:
                        results[endpoint] = f"❌ EXPOSED (Status: {status})"
                        
            except Exception as e:
                results[endpoint] = f"❌ ERROR: {str(e)}"
    
    return results


async def test_cors_configuration() -> Dict[str, Any]:
    """Test CORS configuration with various origins."""
    results = {}
    base_url = "http://localhost:8001"
    
    test_origins = [
        "http://localhost:3001",  # Should be allowed
        "https://search.sjarmak.ai",  # Should be allowed
        "http://malicious-site.com",  # Should be blocked
        "https://evil.com",  # Should be blocked
    ]
    
    async with aiohttp.ClientSession() as session:
        for origin in test_origins:
            try:
                headers = {
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET"
                }
                
                async with session.options(f"{base_url}/api/health", headers=headers) as response:
                    cors_origin = response.headers.get("Access-Control-Allow-Origin")
                    
                    if origin in ["http://localhost:3001", "https://search.sjarmak.ai"]:
                        if cors_origin == origin:
                            results[origin] = "✅ ALLOWED (as expected)"
                        else:
                            results[origin] = "❌ BLOCKED (should be allowed)"
                    else:
                        if cors_origin == origin:
                            results[origin] = "❌ ALLOWED (should be blocked)"
                        else:
                            results[origin] = "✅ BLOCKED (as expected)"
                            
            except Exception as e:
                results[origin] = f"❌ ERROR: {str(e)}"
    
    return results


async def test_security_headers() -> Dict[str, Any]:
    """Test that security headers are properly set."""
    results = {}
    base_url = "http://localhost:8001"
    
    expected_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options", 
        "X-XSS-Protection",
        "Referrer-Policy",
        "Content-Security-Policy"
    ]
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/api/health") as response:
                for header in expected_headers:
                    if header in response.headers:
                        results[header] = f"✅ PRESENT: {response.headers[header]}"
                    else:
                        results[header] = "❌ MISSING"
                        
        except Exception as e:
            results["error"] = f"❌ ERROR: {str(e)}"
    
    return results


async def test_trusted_host() -> Dict[str, Any]:
    """Test TrustedHost middleware configuration."""
    results = {}
    base_url = "http://localhost:8001"
    
    # Test with invalid Host header
    async with aiohttp.ClientSession() as session:
        try:
            headers = {"Host": "malicious-host.com"}
            async with session.get(f"{base_url}/api/health", headers=headers) as response:
                if response.status == 400:
                    results["invalid_host"] = "✅ BLOCKED (400 Bad Request)"
                else:
                    results["invalid_host"] = f"❌ ALLOWED (Status: {response.status})"
                    
        except Exception as e:
            results["invalid_host"] = f"❌ ERROR: {str(e)}"
    
    return results


async def main():
    """Run all security tests."""
    print("🔒 Security Configuration Test")
    print("=" * 50)
    
    print("\n📍 Testing Debug Endpoints Security...")
    debug_results = await test_debug_endpoints_disabled()
    for endpoint, result in debug_results.items():
        print(f"  {endpoint}: {result}")
    
    print("\n📍 Testing CORS Configuration...")
    cors_results = await test_cors_configuration()
    for origin, result in cors_results.items():
        print(f"  {origin}: {result}")
    
    print("\n📍 Testing Security Headers...")
    headers_results = await test_security_headers()
    for header, result in headers_results.items():
        print(f"  {header}: {result}")
    
    print("\n📍 Testing TrustedHost Protection...")
    trusted_host_results = await test_trusted_host()
    for test, result in trusted_host_results.items():
        print(f"  {test}: {result}")
    
    # Summary
    all_tests = [debug_results, cors_results, headers_results, trusted_host_results]
    total_tests = sum(len(test_dict) for test_dict in all_tests)
    passed_tests = sum(
        1 for test_dict in all_tests 
        for result in test_dict.values() 
        if result.startswith("✅")
    )
    
    print(f"\n📊 Summary: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All security tests passed!")
        return 0
    else:
        print("⚠️  Some security tests failed. Please review the configuration.")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Security Configuration Test Script")
        print("\nUsage: python test_security_config.py")
        print("\nThis script tests:")
        print("- Debug endpoints are properly secured")
        print("- CORS configuration blocks malicious origins")
        print("- Security headers are present")
        print("- TrustedHost middleware blocks invalid hosts")
        print("\nMake sure the backend server is running on localhost:8001")
        sys.exit(0)
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        sys.exit(1)
