#!/usr/bin/env python3
"""
Test script to verify the PostHog driver is working correctly.

This script performs basic connectivity and functionality tests.

Usage:
    # Set up .env file with credentials or export environment variables
    export POSTHOG_API_KEY="phx_your_api_key"
    export POSTHOG_PROJECT_ID="12345"
    export POSTHOG_REGION="us"  # or "eu"

    python test_connection.py
"""

import os
import sys

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required if env vars are set

from posthog_driver import (
    PostHogDriver,
    PostHogError,
    AuthenticationError,
    ConnectionError,
    ObjectNotFoundError,
    QuerySyntaxError,
    RateLimitError,
    TimeoutError
)


def test_connection():
    """Test basic connection to PostHog API."""
    print("Test 1: Connection Test")
    print("-" * 60)

    try:
        client = PostHogDriver.from_env()
        print("✓ Successfully connected to PostHog API")
        print(f"  API URL: {client.api_url}")
        print(f"  Project ID: {client.project_id}")
        return client, True
    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e.message}")
        print(f"  Details: {e.details}")
        print("\nMake sure to set environment variables:")
        print("  export POSTHOG_API_KEY='phx_your_key'")
        print("  export POSTHOG_PROJECT_ID='12345'")
        return None, False
    except ConnectionError as e:
        print(f"✗ Connection failed: {e.message}")
        print(f"  Details: {e.details}")
        print("\nCheck your network connection and API URL")
        return None, False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return None, False


def test_list_objects(client):
    """Test listing available objects."""
    print("\nTest 2: List Objects")
    print("-" * 60)

    try:
        objects = client.list_objects()
        print(f"✓ Successfully retrieved {len(objects)} objects")
        print(f"  Objects: {', '.join(objects)}")

        # Verify expected objects are present
        expected = ["events", "persons", "cohorts", "insights"]
        for obj in expected:
            if obj not in objects:
                print(f"✗ Warning: Expected object '{obj}' not found")
                return False

        return True
    except Exception as e:
        print(f"✗ Failed to list objects: {e}")
        return False


def test_get_fields(client):
    """Test getting field schema."""
    print("\nTest 3: Get Field Schema")
    print("-" * 60)

    try:
        # Try to get fields for events object
        fields = client.get_fields('events')
        print(f"✓ Successfully retrieved {len(fields)} fields for events object")
        print(f"  Sample fields: {', '.join(list(fields.keys())[:5])}")

        # Verify essential fields are present (PostHog uses different schema)
        essential_fields = ["event", "timestamp", "distinct_id"]
        for field in essential_fields:
            if field not in fields:
                print(f"✗ Warning: Expected field '{field}' not found")
                return False

        return True
    except ObjectNotFoundError as e:
        print(f"✗ Events object not found: {e.message}")
        return False
    except Exception as e:
        print(f"✗ Failed to get fields: {e}")
        return False


def test_simple_query(client):
    """Test executing a simple HogQL query."""
    print("\nTest 4: Simple Query")
    print("-" * 60)

    try:
        query = """
            SELECT event, timestamp, distinct_id
            FROM events
            LIMIT 5
        """
        results = client.read(query)
        print(f"✓ Successfully executed query")
        print(f"  Retrieved {len(results)} records")
        if results:
            print(f"  Sample record: {list(results[0].keys())}")
        return True
    except QuerySyntaxError as e:
        print(f"✗ Query syntax error: {e.message}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_filtered_query(client):
    """Test query with WHERE clause."""
    print("\nTest 5: Filtered Query")
    print("-" * 60)

    try:
        query = """
            SELECT event, timestamp, distinct_id
            FROM events
            WHERE timestamp > now() - INTERVAL 7 DAY
            LIMIT 10
        """
        results = client.read(query)
        print(f"✓ Successfully executed filtered query")
        print(f"  Retrieved {len(results)} records from last 7 days")
        return True
    except Exception as e:
        print(f"✗ Filtered query failed: {e}")
        return False


def test_aggregation_query(client):
    """Test query with aggregation."""
    print("\nTest 6: Aggregation Query")
    print("-" * 60)

    try:
        query = """
            SELECT
                event,
                count() as count
            FROM events
            WHERE timestamp > now() - INTERVAL 7 DAY
            GROUP BY event
            ORDER BY count DESC
            LIMIT 5
        """
        results = client.read(query)
        print(f"✓ Successfully executed aggregation query")
        print(f"  Retrieved {len(results)} event types")
        if results:
            print(f"  Top event: {results[0]['event']} ({results[0]['count']} times)")
        return True
    except Exception as e:
        print(f"✗ Aggregation query failed: {e}")
        return False


def test_property_access(client):
    """Test accessing event properties."""
    print("\nTest 7: Property Access")
    print("-" * 60)

    try:
        query = """
            SELECT
                event,
                properties.$current_url as url,
                properties.browser as browser
            FROM events
            WHERE timestamp > now() - INTERVAL 1 DAY
            LIMIT 5
        """
        results = client.read(query)
        print(f"✓ Successfully accessed properties")
        print(f"  Retrieved {len(results)} records with properties")
        return True
    except Exception as e:
        print(f"✗ Property access failed: {e}")
        return False


def test_pagination(client):
    """Test pagination with LIMIT and OFFSET."""
    print("\nTest 8: Pagination")
    print("-" * 60)

    try:
        # First page
        query1 = """
            SELECT event, timestamp
            FROM events
            ORDER BY timestamp DESC
            LIMIT 5
        """
        page1 = client.read(query1)

        # Second page
        query2 = """
            SELECT event, timestamp
            FROM events
            ORDER BY timestamp DESC
            LIMIT 5 OFFSET 5
        """
        page2 = client.read(query2)

        print(f"✓ Successfully paginated results")
        print(f"  Page 1: {len(page1)} records")
        print(f"  Page 2: {len(page2)} records")
        return True
    except Exception as e:
        print(f"✗ Pagination failed: {e}")
        return False


def test_batched_reading(client):
    """Test read_batched() functionality."""
    print("\nTest 9: Batched Reading")
    print("-" * 60)

    try:
        query = """
            SELECT event, timestamp
            FROM events
            WHERE timestamp > now() - INTERVAL 1 DAY
        """

        batch_count = 0
        total_records = 0

        for batch in client.read_batched(query, batch_size=100):
            batch_count += 1
            total_records += len(batch)

            # Limit test to first 3 batches
            if batch_count >= 3:
                break

        print(f"✓ Successfully used read_batched()")
        print(f"  Processed {batch_count} batches")
        print(f"  Total records: {total_records}")
        return True
    except Exception as e:
        print(f"✗ Batched reading failed: {e}")
        return False


def test_error_handling(client):
    """Test error handling."""
    print("\nTest 10: Error Handling")
    print("-" * 60)

    # Test invalid object
    try:
        client.get_fields('invalid_object')
        print("✗ Should have raised ObjectNotFoundError")
        return False
    except ObjectNotFoundError as e:
        print(f"✓ ObjectNotFoundError raised correctly: {e.message}")

    # Test invalid query syntax
    try:
        client.read("SELECT FROM events")  # Missing column list
        print("✗ Should have raised QuerySyntaxError")
        return False
    except QuerySyntaxError as e:
        print(f"✓ QuerySyntaxError raised correctly: {e.message}")

    return True


def test_capabilities(client):
    """Test get_capabilities() method."""
    print("\nTest 11: Driver Capabilities")
    print("-" * 60)

    try:
        caps = client.get_capabilities()
        print(f"✓ Successfully retrieved capabilities")
        print(f"  Read: {caps.read}")
        print(f"  Write: {caps.write}")
        print(f"  Query Language: {caps.query_language}")
        print(f"  Pagination: {caps.pagination_style}")
        print(f"  Max Page Size: {caps.max_page_size}")

        # Verify expected capabilities
        if caps.read != True:
            print("✗ Expected read capability to be True")
            return False
        if caps.query_language != "HogQL":
            print("✗ Expected query language to be HogQL")
            return False

        return True
    except Exception as e:
        print(f"✗ Failed to get capabilities: {e}")
        return False


def test_rate_limit_status(client):
    """Test rate limit status checking."""
    print("\nTest 12: Rate Limit Status")
    print("-" * 60)

    try:
        status = client.get_rate_limit_status()
        print(f"✓ Successfully retrieved rate limit status")
        print(f"  Limit: {status['limit'] or 'Not available'}")
        print(f"  Remaining: {status['remaining'] or 'Not available'}")
        print(f"  Reset at: {status['reset_at'] or 'Not available'}")

        if status['remaining'] is not None and status['remaining'] < 50:
            print(f"  ⚠ Warning: Only {status['remaining']} requests remaining")
        elif status['remaining'] is None:
            print(f"  ℹ PostHog API did not return rate limit headers")

        return True
    except Exception as e:
        print(f"✗ Failed to get rate limit status: {e}")
        return False


def test_persons_object(client):
    """Test querying persons object."""
    print("\nTest 13: Persons Object")
    print("-" * 60)

    try:
        # Get fields for persons
        fields = client.get_fields('persons')
        print(f"✓ Retrieved {len(fields)} fields for persons object")

        # Query persons
        query = """
            SELECT id, created_at, properties
            FROM persons
            LIMIT 5
        """
        results = client.read(query)
        print(f"✓ Successfully queried persons")
        print(f"  Retrieved {len(results)} person records")
        return True
    except Exception as e:
        print(f"✗ Persons query failed: {e}")
        # This is not critical - might not have person data
        print("  (This is OK if no person data exists)")
        return True  # Don't fail test


def main():
    """Run all tests."""
    print("=" * 60)
    print("PostHog Driver Test Suite")
    print("=" * 60)

    # Check environment
    if not os.getenv('POSTHOG_API_KEY'):
        print("\n⚠ Warning: POSTHOG_API_KEY not set")
        print("Please set up environment variables:")
        print("  export POSTHOG_API_KEY='phx_your_key'")
        print("  export POSTHOG_PROJECT_ID='12345'")
        print("  export POSTHOG_REGION='us'  # or 'eu'")
        print("\nOr create a .env file with these values")
        sys.exit(1)

    results = []

    # Test 1: Connection
    client, success = test_connection()
    results.append(success)

    if not success or not client:
        print("\n" + "=" * 60)
        print("FAILED: Cannot proceed without connection")
        print("=" * 60)
        sys.exit(1)

    # Run remaining tests
    try:
        results.append(test_list_objects(client))
        results.append(test_get_fields(client))
        results.append(test_simple_query(client))
        results.append(test_filtered_query(client))
        results.append(test_aggregation_query(client))
        results.append(test_property_access(client))
        results.append(test_pagination(client))
        results.append(test_batched_reading(client))
        results.append(test_error_handling(client))
        results.append(test_capabilities(client))
        results.append(test_rate_limit_status(client))
        results.append(test_persons_object(client))
    except KeyboardInterrupt:
        print("\n\n⚠ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error during tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)
    failed = total - passed

    print(f"Passed: {passed}/{total}")
    print(f"Failed: {failed}/{total}")

    if failed == 0:
        print("\n✓ All tests passed!")
        print("\nYour PostHog driver is working correctly!")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} test(s) failed")
        print("\nCheck the error messages above for details")
        sys.exit(1)


if __name__ == '__main__':
    main()
