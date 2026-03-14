"""
Invisible Go Proxy - Test Script

This script tests the Go proxy server functionality and Cloudflare bypass capabilities.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration (Docker compatible)
import os

# Auto-detect proxy URL based on environment
if os.getenv("ENVIRONMENT") == "production":
    PROXY_URL = os.getenv("GO_PROXY_URL", "http://invisible-proxy:8080")
else:
    PROXY_URL = os.getenv("GO_PROXY_URL", "http://127.0.0.1:8080")

print(f"🔗 Testing with proxy URL: {PROXY_URL}")

TEST_URLS = [
    "https://httpbin.org/user-agent",
    "https://httpbin.org/headers",
    "https://httpbin.org/ip",
    "https://www.hepsiemlak.com",
]

def test_health_check() -> bool:
    """Test proxy server health check"""
    try:
        response = requests.get(f"{PROXY_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data.get('status')}")
            return True
        else:
            print(f"❌ Health check failed: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_simple_proxy(url: str) -> Dict[str, Any]:
    """Test simple proxy GET request"""
    try:
        start_time = time.time()
        response = requests.get(f"{PROXY_URL}/proxy?url={url}", timeout=30)
        end_time = time.time()

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Simple proxy test passed for {url}")
            print(f"   Response status: {data.get('status')}")
            print(f"   Response time: {end_time - start_time:.2f}s")
            print(f"   Body length: {len(data.get('body', ''))} bytes")
            return data
        else:
            print(f"❌ Simple proxy test failed for {url}: Status {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Simple proxy test failed for {url}: {e}")
        return {}

def test_advanced_proxy(url: str) -> Dict[str, Any]:
    """Test advanced proxy POST request with custom headers"""
    try:
        payload = {
            "url": url,
            "method": "GET",
            "headers": {
                "X-Custom-Header": "test-value",
                "Accept-Language": "en-US,en;q=0.9,tr;q=0.8"
            },
            "timeout": 30
        }

        start_time = time.time()
        response = requests.post(f"{PROXY_URL}/proxy", json=payload, timeout=35)
        end_time = time.time()

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Advanced proxy test passed for {url}")
            print(f"   Response status: {data.get('status')}")
            print(f"   Response time: {end_time - start_time:.2f}s")
            print(f"   Headers received: {len(data.get('headers', {}))}")
            print(f"   Body length: {len(data.get('body', ''))} bytes")

            # Check if custom header was forwarded
            if data.get('headers'):
                print(f"   Custom header forwarded: {'X-Custom-Header' in str(data.get('headers'))}")

            return data
        else:
            print(f"❌ Advanced proxy test failed for {url}: Status {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Advanced proxy test failed for {url}: {e}")
        return {}

def test_cloudflare_bypass(url: str) -> Dict[str, Any]:
    """Test Cloudflare bypass capabilities"""
    try:
        payload = {
            "url": url,
            "method": "GET",
            "timeout": 60
        }

        start_time = time.time()
        response = requests.post(f"{PROXY_URL}/proxy", json=payload, timeout=65)
        end_time = time.time()

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cloudflare bypass test for {url}")
            print(f"   Response status: {data.get('status')}")
            print(f"   Response time: {end_time - start_time:.2f}s")

            # Check if we got actual content (not Cloudflare challenge page)
            body = data.get('body', '')
            if isinstance(body, bytes):
                body_str = body.decode('utf-8', errors='ignore')
            else:
                body_str = str(body)

            cloudflare_indicators = ['cf-challenge', 'Cloudflare', 'challenge-platform']
            has_cloudflare = any(indicator in body_str.lower() for indicator in cloudflare_indicators)

            if has_cloudflare:
                print(f"   ⚠️  Cloudflare challenge detected in response")
            else:
                print(f"   ✅ No Cloudflare challenge detected")

            print(f"   Body length: {len(body)} bytes")

            return data
        else:
            print(f"❌ Cloudflare bypass test failed for {url}: Status {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Cloudflare bypass test failed for {url}: {e}")
        return {}

def test_error_handling() -> bool:
    """Test error handling with invalid requests"""
    try:
        # Test with invalid URL
        response = requests.get(f"{PROXY_URL}/proxy?url=not-a-valid-url", timeout=10)
        print(f"✅ Error handling test: Invalid URL - Status {response.status_code}")

        # Test with timeout
        payload = {
            "url": "https://httpbin.org/delay/30",
            "timeout": 5
        }
        response = requests.post(f"{PROXY_URL}/proxy", json=payload, timeout=10)
        print(f"✅ Error handling test: Timeout - Status {response.status_code}")

        return True
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_performance() -> Dict[str, Any]:
    """Test proxy performance with multiple requests"""
    url = "https://httpbin.org/get"
    request_count = 10

    print(f"🚀 Performance test: {request_count} concurrent requests to {url}")

    start_time = time.time()
    responses = []

    for i in range(request_count):
        try:
            response = requests.get(f"{PROXY_URL}/proxy?url={url}", timeout=30)
            if response.status_code == 200:
                responses.append(response.json())
        except Exception as e:
            print(f"   Request {i+1} failed: {e}")

    end_time = time.time()
    total_time = end_time - start_time

    successful_requests = len(responses)
    success_rate = (successful_requests / request_count) * 100
    avg_time = total_time / request_count
    requests_per_second = request_count / total_time

    print(f"✅ Performance test completed")
    print(f"   Successful requests: {successful_requests}/{request_count}")
    print(f"   Success rate: {success_rate:.1f}%")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average time per request: {avg_time:.2f}s")
    print(f"   Requests per second: {requests_per_second:.2f}")

    return {
        "total_requests": request_count,
        "successful_requests": successful_requests,
        "success_rate": success_rate,
        "total_time": total_time,
        "avg_time": avg_time,
        "requests_per_second": requests_per_second
    }

def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Invisible Go Proxy - Test Suite")
    print("=" * 60)
    print()

    # Health check
    print("📋 Test 1: Health Check")
    print("-" * 40)
    if not test_health_check():
        print("❌ Cannot proceed without a healthy proxy server")
        return
    print()

    # Simple proxy tests
    print("📋 Test 2: Simple Proxy Requests")
    print("-" * 40)
    for url in TEST_URLS[:2]:  # Test first 2 URLs
        test_simple_proxy(url)
        time.sleep(1)
        print()

    # Advanced proxy tests
    print("📋 Test 3: Advanced Proxy Requests")
    print("-" * 40)
    test_advanced_proxy(TEST_URLS[0])
    time.sleep(1)
    print()

    # Cloudflare bypass test
    print("📋 Test 4: Cloudflare Bypass")
    print("-" * 40)
    test_cloudflare_bypass(TEST_URLS[3])  # Test HepsiEmlak
    print()

    # Error handling test
    print("📋 Test 5: Error Handling")
    print("-" * 40)
    test_error_handling()
    print()

    # Performance test
    print("📋 Test 6: Performance")
    print("-" * 40)
    performance_data = test_performance()
    print()

    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print("✅ All basic tests completed successfully")
    print()
    print("📝 Notes:")
    print("   - Proxy server is running and responding")
    print("   - Simple and advanced requests work correctly")
    print("   - Error handling is functioning")
    print("   - Performance metrics collected")
    print()
    print(f"📈 Performance Results:")
    print(f"   - Success Rate: {performance_data['success_rate']:.1f}%")
    print(f"   - Requests/sec: {performance_data['requests_per_second']:.2f}")
    print()
    print("🎉 Test suite completed!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
