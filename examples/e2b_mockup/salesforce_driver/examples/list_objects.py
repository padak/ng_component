#!/usr/bin/env python3
"""
Example: List all available Salesforce objects

This script demonstrates how to discover what Salesforce objects are available
in your instance. This is the first step when exploring a new Salesforce
environment or validating that expected objects exist.

Usage:
    export SF_API_KEY="your-api-key"
    export SF_API_URL="http://localhost:8000"  # optional
    python list_objects.py

What you'll learn:
- How to initialize the Salesforce client
- How to list all available objects
- How to handle connection and authentication errors
"""

import os
import sys

# Add parent directory to path to import salesforce_driver
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from salesforce_driver import SalesforceClient, ConnectionError, AuthError


def main():
    """Discover and list all available Salesforce objects"""

    print("Salesforce Object Discovery")
    print("=" * 80)

    # Initialize client
    # The client will read SF_API_KEY and SF_API_URL from environment variables
    try:
        client = SalesforceClient()
        print(f"Connected to Salesforce API at: {client.api_url}")
    except AuthError as e:
        print(f"\nAuthentication Error: {e}")
        print("\nTo fix this:")
        print("  1. Set your API key: export SF_API_KEY='your-api-key'")
        print("  2. Verify the key is correct")
        sys.exit(1)
    except Exception as e:
        print(f"\nFailed to initialize client: {e}")
        sys.exit(1)

    # Discover available objects
    try:
        print("\nDiscovering available Salesforce objects...")
        objects = client.list_objects()

        # Display results
        print(f"\nFound {len(objects)} Salesforce objects:")
        print("-" * 80)

        for i, obj in enumerate(objects, 1):
            print(f"  {i}. {obj}")

        print("-" * 80)

        # Provide helpful next steps
        print("\nNext steps:")
        print("  - To see fields for an object, run: python discover_lead_fields.py")
        print("  - To query data, run: python query_recent_leads.py")
        print("\nExample field discovery:")
        if objects:
            example_obj = objects[0]
            print(f"  fields = client.get_fields('{example_obj}')")
            print(f"  print(fields)")

    except ConnectionError as e:
        print(f"\nConnection Error: {e}")
        print("\nTo fix this:")
        print("  1. Start the mock API server")
        print("  2. Verify SF_API_URL is correct (default: http://localhost:8000)")
        print("  3. Check network connectivity")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == '__main__':
    main()
