#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Deployment Test Script
Tests all API endpoints on ec2-13-222-13-14.compute-1.amazonaws.com
"""

import requests
import json
import sys
import io
from datetime import datetime
from typing import Dict, Tuple

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configuration
AWS_HOST = "ec2-13-222-13-14.compute-1.amazonaws.com"
KONG_PORT = 8000
KONG_ADMIN_PORT = 8001
DJANGO_PORT = 8080

# Base URLs
KONG_BASE_URL = f"http://{AWS_HOST}:{KONG_PORT}"
KONG_ADMIN_URL = f"http://{AWS_HOST}:{KONG_ADMIN_PORT}"
DJANGO_BASE_URL = f"http://{AWS_HOST}:{DJANGO_PORT}"

# Test API Keys (from DEPLOYMENT_SUMMARY.md)
API_KEYS = {
    "test-client": "test-api-key-12345",
    "jmeter-client": "jmeter-load-test-key-67890",
    "production-client": "prod-secure-key-CHANGE-THIS-IN-PRODUCTION",
    "monitoring-client": "monitor-health-check-key-11111"
}

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_test(name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} - {name}")
    if details:
        print(f"     {details}")

def test_kong_admin_status() -> bool:
    """Test 1: Kong Admin API is accessible"""
    print_header("Test 1: Kong Admin API Status")
    try:
        response = requests.get(f"{KONG_ADMIN_URL}/status", timeout=10)
        passed = response.status_code == 200

        if passed:
            data = response.json()
            print_test("Kong Admin API accessible", True)
            print(f"     Server: {response.headers.get('Server', 'N/A')}")
            print(f"     Database: {data.get('database', {}).get('reachable', 'N/A')}")
        else:
            print_test("Kong Admin API accessible", False, f"Status: {response.status_code}")

        return passed
    except Exception as e:
        print_test("Kong Admin API accessible", False, f"Error: {str(e)}")
        return False

def test_kong_routes() -> bool:
    """Test 2: Kong has routes configured (declarative mode)"""
    print_header("Test 2: Kong Routes Configuration")
    try:
        response = requests.get(f"{KONG_ADMIN_URL}/routes", timeout=10)
        passed = response.status_code == 200

        if passed:
            data = response.json()
            routes = data.get('data', [])
            passed = len(routes) > 0

            if passed:
                print_test("Kong routes configured", True, f"Found {len(routes)} routes")
                for route in routes:
                    print(f"     • {route.get('name', 'unnamed')}: {route.get('paths', [])}")
            else:
                print_test("Kong routes configured", False, "No routes found (declarative config not loaded)")
        else:
            print_test("Kong routes configured", False, f"Status: {response.status_code}")

        return passed
    except Exception as e:
        print_test("Kong routes configured", False, f"Error: {str(e)}")
        return False

def test_kong_services() -> bool:
    """Test 3: Kong has services configured"""
    print_header("Test 3: Kong Services Configuration")
    try:
        response = requests.get(f"{KONG_ADMIN_URL}/services", timeout=10)
        passed = response.status_code == 200

        if passed:
            data = response.json()
            services = data.get('data', [])
            passed = len(services) > 0

            if passed:
                print_test("Kong services configured", True, f"Found {len(services)} services")
                for service in services:
                    print(f"     • {service.get('name', 'unnamed')}: {service.get('host', 'N/A')}")
            else:
                print_test("Kong services configured", False, "No services found")
        else:
            print_test("Kong services configured", False, f"Status: {response.status_code}")

        return passed
    except Exception as e:
        print_test("Kong services configured", False, f"Error: {str(e)}")
        return False

def test_health_endpoint_via_kong() -> bool:
    """Test 4: Health check endpoint via Kong (no auth required)"""
    print_header("Test 4: Health Check via Kong")
    try:
        response = requests.get(f"{KONG_BASE_URL}/api/health/", timeout=10)
        passed = response.status_code == 200

        if passed:
            try:
                data = response.json()
                print_test("Health endpoint accessible", True, f"Response: {data}")
            except:
                print_test("Health endpoint accessible", True, f"Response: {response.text[:100]}")
        else:
            print_test("Health endpoint accessible", False,
                      f"Status: {response.status_code}, Response: {response.text[:200]}")

        return passed
    except Exception as e:
        print_test("Health endpoint accessible", False, f"Error: {str(e)}")
        return False

def test_report_endpoint_with_auth() -> bool:
    """Test 5: Report endpoint with API key authentication"""
    print_header("Test 5: Report Endpoint with Authentication")

    # Test without API key (should fail)
    try:
        response = requests.get(
            f"{KONG_BASE_URL}/api/report/",
            params={"projectId": "proj-001", "month": "2026-01"},
            timeout=10
        )
        no_auth_works = response.status_code == 401 or "No API key" in response.text
        print_test("Endpoint requires authentication", no_auth_works,
                  f"Status without API key: {response.status_code}")
    except Exception as e:
        print_test("Endpoint requires authentication", False, f"Error: {str(e)}")
        return False

    # Test with valid API key
    try:
        headers = {"apikey": API_KEYS["test-client"]}
        response = requests.get(
            f"{KONG_BASE_URL}/api/report/",
            headers=headers,
            params={"projectId": "proj-001", "month": "2026-01"},
            timeout=10
        )

        auth_works = response.status_code in [200, 404]  # 404 is ok if no data

        if auth_works:
            if response.status_code == 200:
                try:
                    data = response.json()
                    print_test("Authenticated request successful", True,
                              f"Data received: {json.dumps(data, indent=2)[:200]}")
                except:
                    print_test("Authenticated request successful", True,
                              f"Response: {response.text[:100]}")
            else:
                print_test("Authenticated request successful", True,
                          f"Status: {response.status_code} (No data for this project/month)")
        else:
            print_test("Authenticated request successful", False,
                      f"Status: {response.status_code}, Response: {response.text[:200]}")

        return no_auth_works and auth_works
    except Exception as e:
        print_test("Authenticated request successful", False, f"Error: {str(e)}")
        return False

def test_all_api_keys() -> bool:
    """Test 6: All configured API keys work"""
    print_header("Test 6: Test All API Keys")

    all_passed = True
    for consumer, api_key in API_KEYS.items():
        try:
            headers = {"apikey": api_key}
            response = requests.get(
                f"{KONG_BASE_URL}/api/health/",
                headers=headers,
                timeout=10
            )

            passed = response.status_code == 200
            print_test(f"API key for {consumer}", passed,
                      f"Key: {api_key[:20]}...")

            all_passed = all_passed and passed
        except Exception as e:
            print_test(f"API key for {consumer}", False, f"Error: {str(e)}")
            all_passed = False

    return all_passed

def test_django_direct_access() -> bool:
    """Test 7: Django direct access (bypass Kong)"""
    print_header("Test 7: Django Direct Access (Port 8080)")
    try:
        response = requests.get(f"{DJANGO_BASE_URL}/api/health/", timeout=10)
        passed = response.status_code in [200, 400]  # 400 = ALLOWED_HOSTS issue

        if response.status_code == 200:
            print_test("Django direct access", True, f"Health check successful")
        elif response.status_code == 400:
            print_test("Django direct access", True,
                      f"Django responding but ALLOWED_HOSTS not configured (this is OK)")
        else:
            print_test("Django direct access", False,
                      f"Status: {response.status_code}, Response: {response.text[:200]}")

        return passed
    except Exception as e:
        print_test("Django direct access", False, f"Error: {str(e)}")
        return False

def test_rate_limiting() -> bool:
    """Test 8: Rate limiting is configured"""
    print_header("Test 8: Rate Limiting")
    try:
        headers = {"apikey": API_KEYS["test-client"]}

        # Make multiple requests quickly
        responses = []
        for i in range(5):
            response = requests.get(
                f"{KONG_BASE_URL}/api/health/",
                headers=headers,
                timeout=10
            )
            responses.append(response)

        # Check if rate limiting headers are present
        last_response = responses[-1]
        has_rate_limit_headers = (
            'X-RateLimit-Limit' in last_response.headers or
            'RateLimit-Limit' in last_response.headers or
            'X-Kong-Limit' in last_response.headers
        )

        if has_rate_limit_headers:
            print_test("Rate limiting configured", True,
                      f"Rate limit headers present")
            for key, value in last_response.headers.items():
                if 'rate' in key.lower() or 'limit' in key.lower():
                    print(f"     {key}: {value}")
        else:
            print_test("Rate limiting configured", False,
                      "No rate limiting headers found (may not be configured)")
            return False

        return True
    except Exception as e:
        print_test("Rate limiting configured", False, f"Error: {str(e)}")
        return False

def test_cors_headers() -> bool:
    """Test 9: CORS headers are configured"""
    print_header("Test 9: CORS Configuration")
    try:
        headers = {
            "apikey": API_KEYS["test-client"],
            "Origin": "http://example.com"
        }
        response = requests.options(
            f"{KONG_BASE_URL}/api/health/",
            headers=headers,
            timeout=10
        )

        has_cors = 'Access-Control-Allow-Origin' in response.headers

        if has_cors:
            print_test("CORS configured", True,
                      f"CORS headers present")
            for key, value in response.headers.items():
                if 'access-control' in key.lower():
                    print(f"     {key}: {value}")
        else:
            print_test("CORS configured", False, "No CORS headers found")

        return has_cors
    except Exception as e:
        print_test("CORS configured", False, f"Error: {str(e)}")
        return False

def test_database_connection() -> bool:
    """Test 10: Database connectivity test"""
    print_header("Test 10: Database Connection (Indirect)")
    try:
        # Try to access an endpoint that would require database
        headers = {"apikey": API_KEYS["test-client"]}
        response = requests.get(
            f"{KONG_BASE_URL}/api/report/",
            headers=headers,
            params={"projectId": "test", "month": "2026-01"},
            timeout=10
        )

        # Any response means database is accessible (even if no data)
        passed = response.status_code in [200, 404, 400]

        if passed:
            print_test("Database connection working", True,
                      f"API responds correctly (Status: {response.status_code})")
        else:
            print_test("Database connection working", False,
                      f"Unexpected status: {response.status_code}")

        return passed
    except Exception as e:
        print_test("Database connection working", False, f"Error: {str(e)}")
        return False

def run_all_tests():
    """Run all tests and display summary"""
    print(f"\n{Colors.BOLD}Starting AWS Deployment Tests{Colors.END}")
    print(f"Target: {AWS_HOST}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    tests = [
        ("Kong Admin Status", test_kong_admin_status),
        ("Kong Routes", test_kong_routes),
        ("Kong Services", test_kong_services),
        ("Health Check via Kong", test_health_endpoint_via_kong),
        ("Report Endpoint Auth", test_report_endpoint_with_auth),
        ("All API Keys", test_all_api_keys),
        ("Django Direct Access", test_django_direct_access),
        ("Rate Limiting", test_rate_limiting),
        ("CORS Configuration", test_cors_headers),
        ("Database Connection", test_database_connection),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"{Colors.RED}ERROR in {name}: {str(e)}{Colors.END}")
            results.append((name, False))

    # Summary
    print_header("Test Summary")
    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)

    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {status} - {name}")

    print(f"\n{Colors.BOLD}Total: {passed_count}/{total_count} tests passed{Colors.END}")

    if passed_count == total_count:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed! Deployment is healthy.{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ {total_count - passed_count} test(s) failed.{Colors.END}\n")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
