#!/bin/bash
"""
Simple security test script using curl.
Tests the security configurations for debug endpoints and headers.
"""

echo "🔒 Security Configuration Test"
echo "=" $(printf "%0.s=" {1..50})
echo

BASE_URL="http://localhost:8001"

echo "📍 Testing Debug Endpoints Security..."

# Test debug endpoints - should be blocked
debug_endpoints=(
    "/api/debug/env"
    "/api/debug/sources" 
    "/api/debug/ping/ads"
    "/api/debug/search/ads?query=test&limit=1"
    "/api/debug/request-headers"
)

for endpoint in "${debug_endpoints[@]}"; do
    echo -n "  $endpoint: "
    status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")
    if [[ "$status" == "403" ]] || [[ "$status" == "401" ]]; then
        echo "✅ SECURED ($status)"
    else
        echo "❌ EXPOSED ($status)"
    fi
done

echo
echo "📍 Testing Security Headers..."

# Test security headers
headers_response=$(curl -s -I "$BASE_URL/api/health")

check_header() {
    local header_name="$1"
    if echo "$headers_response" | grep -qi "$header_name:"; then
        echo "✅ PRESENT: $header_name"
    else
        echo "❌ MISSING: $header_name"
    fi
}

echo -n "  X-Content-Type-Options: "; check_header "X-Content-Type-Options"
echo -n "  X-Frame-Options: "; check_header "X-Frame-Options"
echo -n "  X-XSS-Protection: "; check_header "X-XSS-Protection"
echo -n "  Referrer-Policy: "; check_header "Referrer-Policy"
echo -n "  Content-Security-Policy: "; check_header "Content-Security-Policy"

echo
echo "📍 Testing CORS Configuration..."

# Test CORS with malicious origin
echo -n "  Malicious origin block: "
cors_response=$(curl -s -H "Origin: http://malicious-site.com" -H "Access-Control-Request-Method: GET" -X OPTIONS "$BASE_URL/api/health")
if echo "$cors_response" | grep -q "Access-Control-Allow-Origin: http://malicious-site.com"; then
    echo "❌ ALLOWED (should be blocked)"
else
    echo "✅ BLOCKED (as expected)"
fi

# Test CORS with legitimate origin
echo -n "  Legitimate origin allow: "
cors_response=$(curl -s -H "Origin: http://localhost:3001" -H "Access-Control-Request-Method: GET" -X OPTIONS "$BASE_URL/api/health")
if echo "$cors_response" | grep -q "Access-Control-Allow-Origin: http://localhost:3001"; then
    echo "✅ ALLOWED (as expected)"
else
    echo "❌ BLOCKED (should be allowed)"
fi

echo
echo "📍 Testing TrustedHost Protection..."

# Test with invalid Host header
echo -n "  Invalid host block: "
status=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: malicious-host.com" "$BASE_URL/api/health")
if [[ "$status" == "400" ]]; then
    echo "✅ BLOCKED ($status)"
else
    echo "❌ ALLOWED ($status)"
fi

echo
echo "📊 Security test completed!"
echo "Review the results above to ensure all security measures are working properly."
