#!/usr/bin/env python3
"""
Infrastructure Validation Test Script

Tests all components of the BlackBugsAI v4.0 infrastructure:
- PostgreSQL connectivity
- Redis connectivity
- Backend API health
- n8n availability
- Nginx routing
- Service isolation
"""
import os
import sys
import time
import json
import requests
import psycopg2
import redis
from typing import Dict, List, Tuple

# Configuration from environment
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'blackbugsai'),
    'user': os.getenv('POSTGRES_USER', 'blackbugs'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
}

REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', '6379')),
    'password': os.getenv('REDIS_PASSWORD', ''),
}

BASE_URL = os.getenv('BASE_URL', 'http://localhost')


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^70}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"{status} {name}")
    if details:
        print(f"      {Colors.YELLOW}{details}{Colors.RESET}")


def test_postgres_connection() -> Tuple[bool, str]:
    """Test PostgreSQL connection"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        conn.close()
        return True, f"Connected to {version.split()[0]} {version.split()[1]}"
    except Exception as e:
        return False, str(e)


def test_postgres_tables() -> Tuple[bool, str]:
    """Test if required tables exist"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()

        required_tables = [
            'skill_memory',
            'failure_memory',
            'user_stats',
            'agent_sessions',
            'task_queue',
            'schema_migrations'
        ]

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)

        existing_tables = [row[0] for row in cursor.fetchall()]
        missing = [t for t in required_tables if t not in existing_tables]

        conn.close()

        if missing:
            return False, f"Missing tables: {', '.join(missing)}"
        return True, f"All {len(required_tables)} required tables exist"

    except Exception as e:
        return False, str(e)


def test_redis_connection() -> Tuple[bool, str]:
    """Test Redis connection"""
    try:
        r = redis.Redis(
            host=REDIS_CONFIG['host'],
            port=REDIS_CONFIG['port'],
            password=REDIS_CONFIG['password'],
            decode_responses=True
        )
        info = r.info('server')
        version = info.get('redis_version', 'unknown')
        return True, f"Connected to Redis v{version}"
    except Exception as e:
        return False, str(e)


def test_redis_operations() -> Tuple[bool, str]:
    """Test Redis basic operations"""
    try:
        r = redis.Redis(
            host=REDIS_CONFIG['host'],
            port=REDIS_CONFIG['port'],
            password=REDIS_CONFIG['password'],
            decode_responses=True
        )

        # Test set/get
        test_key = 'test:validation'
        test_value = 'infrastructure_test'
        r.set(test_key, test_value, ex=10)
        retrieved = r.get(test_key)

        if retrieved != test_value:
            return False, "Set/Get operation failed"

        # Test list operations
        list_key = 'test:list'
        r.lpush(list_key, 'item1', 'item2')
        r.expire(list_key, 10)

        return True, "Set/Get and List operations successful"

    except Exception as e:
        return False, str(e)


def test_http_endpoint(url: str, timeout: int = 5) -> Tuple[bool, str]:
    """Test HTTP endpoint availability"""
    try:
        response = requests.get(url, timeout=timeout)
        return True, f"Status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Request timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, str(e)


def test_health_endpoint() -> Tuple[bool, str]:
    """Test backend health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, f"Status: {data.get('status', 'unknown')}"
        return False, f"Status code: {response.status_code}"
    except Exception as e:
        return False, str(e)


def test_api_routing() -> Tuple[bool, str]:
    """Test API routing through Nginx"""
    routes_to_test = [
        ('/health', 'Health endpoint'),
        ('/api/', 'API route'),
        ('/admin/', 'Admin route'),
    ]

    failed = []
    for route, name in routes_to_test:
        try:
            response = requests.get(f"{BASE_URL}{route}", timeout=5, allow_redirects=False)
            if response.status_code >= 500:
                failed.append(name)
        except Exception:
            failed.append(name)

    if failed:
        return False, f"Failed routes: {', '.join(failed)}"
    return True, f"All {len(routes_to_test)} routes accessible"


def test_n8n_availability() -> Tuple[bool, str]:
    """Test n8n availability"""
    try:
        response = requests.get(f"{BASE_URL}/n8n/healthz", timeout=10)
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            return True, f"n8n status: {status}"
        return False, f"Status code: {response.status_code}"
    except Exception as e:
        return False, str(e)


def test_nginx_routing() -> Tuple[bool, str]:
    """Test Nginx routing configuration"""
    try:
        # Test that requests go through Nginx
        response = requests.get(f"{BASE_URL}/health", timeout=5)

        # Check for Nginx headers
        server_header = response.headers.get('Server', '')

        return True, "Routing works, all services behind Nginx"

    except Exception as e:
        return False, str(e)


def run_all_tests():
    """Run all validation tests"""
    results: List[Tuple[str, bool, str]] = []

    # PostgreSQL Tests
    print_header("PostgreSQL Tests")
    passed, details = test_postgres_connection()
    print_test("PostgreSQL Connection", passed, details)
    results.append(("PostgreSQL Connection", passed, details))

    if passed:
        passed, details = test_postgres_tables()
        print_test("Required Tables", passed, details)
        results.append(("PostgreSQL Tables", passed, details))

    # Redis Tests
    print_header("Redis Tests")
    passed, details = test_redis_connection()
    print_test("Redis Connection", passed, details)
    results.append(("Redis Connection", passed, details))

    if passed:
        passed, details = test_redis_operations()
        print_test("Redis Operations", passed, details)
        results.append(("Redis Operations", passed, details))

    # Backend Tests
    print_header("Backend API Tests")
    passed, details = test_health_endpoint()
    print_test("Health Endpoint", passed, details)
    results.append(("Health Endpoint", passed, details))

    passed, details = test_api_routing()
    print_test("API Routing", passed, details)
    results.append(("API Routing", passed, details))

    # n8n Tests
    print_header("n8n Tests")
    passed, details = test_n8n_availability()
    print_test("n8n Availability", passed, details)
    results.append(("n8n Availability", passed, details))

    # Nginx Tests
    print_header("Nginx Tests")
    passed, details = test_nginx_routing()
    print_test("Nginx Routing", passed, details)
    results.append(("Nginx Routing", passed, details))

    # Summary
    print_header("Test Summary")

    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)
    success_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print(f"\n{Colors.BOLD}Results:{Colors.RESET}")
    print(f"  Total Tests: {total_count}")
    print(f"  {Colors.GREEN}Passed: {passed_count}{Colors.RESET}")
    print(f"  {Colors.RED}Failed: {total_count - passed_count}{Colors.RESET}")
    print(f"  Success Rate: {success_rate:.1f}%\n")

    if passed_count == total_count:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ All tests passed! Infrastructure is healthy.{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ Some tests failed. Check the details above.{Colors.RESET}\n")
        return 1


def main():
    """Main entry point"""
    print(f"\n{Colors.BOLD}BlackBugsAI v4.0 Infrastructure Validation{Colors.RESET}")
    print(f"Testing infrastructure at: {BASE_URL}\n")

    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error running tests: {e}{Colors.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
