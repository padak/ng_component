#!/usr/bin/env python3
"""
Test script to verify the Salesforce driver is working correctly.

This script performs basic connectivity and functionality tests.

Usage:
    export SF_API_KEY="your-api-key"
    python test_connection.py
"""

import os
import sys
from salesforce_driver import (
    SalesforceClient,
    ConnectionError,
    AuthError,
    ObjectNotFoundError,
    QueryError
)


def test_connection():
    """Test basic connection to the API"""
    print("Test 1: Connection Test")
    print("-" * 60)

    try:
        client = SalesforceClient()
        print("✓ Successfully connected to Salesforce API")
        print(f"  API URL: {client.api_url}")
        return client, True
    except AuthError as e:
        print(f"✗ Authentication failed: {e}")
        print("\nMake sure to set SF_API_KEY environment variable:")
        print("  export SF_API_KEY='your-api-key'")
        return None, False
    except ConnectionError as e:
        print(f"✗ Connection failed: {e}")
        print("\nMake sure the mock API server is running:")
        print("  python mock_api.py")
        return None, False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return None, False


def test_list_objects(client):
    """Test listing available objects"""
    print("\nTest 2: List Objects")
    print("-" * 60)

    try:
        objects = client.list_objects()
        print(f"✓ Successfully retrieved {len(objects)} objects")
        print(f"  Objects: {', '.join(objects)}")
        return True
    except Exception as e:
        print(f"✗ Failed to list objects: {e}")
        return False


def test_get_fields(client):
    """Test getting field schema"""
    print("\nTest 3: Get Field Schema")
    print("-" * 60)

    try:
        # Try to get fields for Lead object
        fields = client.get_fields('Lead')
        print(f"✓ Successfully retrieved {len(fields)} fields for Lead object")
        print(f"  Sample fields: {', '.join(list(fields.keys())[:5])}")
        return True
    except ObjectNotFoundError as e:
        print(f"✗ Lead object not found: {e}")
        return False
    except Exception as e:
        print(f"✗ Failed to get fields: {e}")
        return False


def test_simple_query(client):
    """Test executing a simple SOQL query"""
    print("\nTest 4: Simple Query")
    print("-" * 60)

    try:
        leads = client.query("SELECT Id, Name FROM Lead LIMIT 5")
        print(f"✓ Successfully executed query")
        print(f"  Retrieved {len(leads)} records")
        if leads:
            print(f"  Sample record: {leads[0]}")
        return True
    except QueryError as e:
        print(f"✗ Query failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_filtered_query(client):
    """Test query with WHERE clause"""
    print("\nTest 5: Filtered Query")
    print("-" * 60)

    try:
        leads = client.query("""
            SELECT Id, Name, Email
            FROM Lead
            WHERE Email != null
            LIMIT 5
        """)
        print(f"✓ Successfully executed filtered query")
        print(f"  Retrieved {len(leads)} records with email")
        return True
    except Exception as e:
        print(f"✗ Filtered query failed: {e}")
        return False


def test_relationship_query(client):
    """Test query with relationships"""
    print("\nTest 6: Relationship Query")
    print("-" * 60)

    try:
        leads = client.query("""
            SELECT Id, Name, Campaign.Name AS CampaignName
            FROM Lead
            WHERE Campaign.Id != null
            LIMIT 5
        """)
        print(f"✓ Successfully executed relationship query")
        print(f"  Retrieved {len(leads)} leads with campaigns")
        return True
    except Exception as e:
        print(f"✗ Relationship query failed: {e}")
        return False


def test_error_handling(client):
    """Test error handling"""
    print("\nTest 7: Error Handling")
    print("-" * 60)

    # Test invalid object
    try:
        client.get_fields('InvalidObject')
        print("✗ Should have raised ObjectNotFoundError")
        return False
    except ObjectNotFoundError:
        print("✓ ObjectNotFoundError raised correctly")

    # Test invalid query
    try:
        client.query("INVALID QUERY")
        print("✗ Should have raised QueryError")
        return False
    except QueryError:
        print("✓ QueryError raised correctly")

    return True


def test_context_manager(client):
    """Test context manager functionality"""
    print("\nTest 8: Context Manager")
    print("-" * 60)

    try:
        with SalesforceClient() as temp_client:
            objects = temp_client.list_objects()
        print("✓ Context manager works correctly")
        return True
    except Exception as e:
        print(f"✗ Context manager failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Salesforce Driver Test Suite")
    print("=" * 60)

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
        results.append(test_relationship_query(client))
        results.append(test_error_handling(client))
        results.append(test_context_manager(client))
    finally:
        client.close()

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
        sys.exit(0)
    else:
        print(f"\n✗ {failed} test(s) failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
