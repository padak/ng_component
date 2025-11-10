#!/usr/bin/env python3
"""
Example: Discover Lead object schema

This script demonstrates how to retrieve and inspect the field schema for the
Lead object. Understanding the schema is crucial before writing queries, as it
shows you what fields are available, their data types, and whether they're
required or optional.

Usage:
    export SF_API_KEY="your-api-key"
    export SF_API_URL="http://localhost:8000"  # optional
    python discover_lead_fields.py

What you'll learn:
- How to retrieve object schema/metadata
- How to inspect field definitions (name, type, nullable, etc.)
- How to use schema information to build queries
- Best practices for field discovery
"""

import os
import sys

# Add parent directory to path to import salesforce_driver
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from salesforce_driver import (
    SalesforceClient,
    ConnectionError,
    AuthError,
    ObjectNotFoundError
)


def main():
    """Discover and display the Lead object schema"""

    print("Lead Object Schema Discovery")
    print("=" * 80)

    # Initialize client
    try:
        client = SalesforceClient()
        print(f"Connected to Salesforce API at: {client.api_url}")
    except AuthError as e:
        print(f"\nAuthentication Error: {e}")
        print("\nSet SF_API_KEY environment variable and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFailed to initialize client: {e}")
        sys.exit(1)

    try:
        # Step 1: Verify Lead object exists
        print("\nStep 1: Verifying Lead object exists...")
        objects = client.list_objects()

        if 'Lead' not in objects:
            print(f"\nError: Lead object not found!")
            print(f"Available objects: {', '.join(objects)}")
            sys.exit(1)

        print("  ✓ Lead object found")

        # Step 2: Get Lead schema
        print("\nStep 2: Retrieving Lead schema...")
        schema = client.get_fields('Lead')

        # The response contains metadata about the object
        print(f"  Object Name: {schema.get('name', 'Lead')}")
        print(f"  Label: {schema.get('label', 'Lead')}")

        fields = schema.get('fields', [])
        print(f"  Total Fields: {len(fields)}")

        # Step 3: Display field details
        print("\nStep 3: Field Definitions")
        print("-" * 80)
        print(f"{'Field Name':<30} {'Type':<15} {'Nullable':<10} {'Label':<30}")
        print("-" * 80)

        for field in fields:
            field_name = field.get('name', 'Unknown')
            field_type = field.get('type', 'unknown')
            nullable = "Yes" if field.get('nullable', True) else "No"
            label = field.get('label', field_name)

            # Truncate long labels for display
            if len(label) > 28:
                label = label[:25] + "..."

            print(f"{field_name:<30} {field_type:<15} {nullable:<10} {label:<30}")

        print("-" * 80)

        # Step 4: Field type summary
        print("\nStep 4: Field Type Summary")
        print("-" * 80)

        type_counts = {}
        for field in fields:
            field_type = field.get('type', 'unknown')
            type_counts[field_type] = type_counts.get(field_type, 0) + 1

        for field_type in sorted(type_counts.keys()):
            count = type_counts[field_type]
            print(f"  {field_type:<20} {count:>3} field(s)")

        # Step 5: Required vs Optional fields
        print("\nStep 5: Field Requirements")
        print("-" * 80)

        required_fields = [f['name'] for f in fields if not f.get('nullable', True)]
        optional_fields = [f['name'] for f in fields if f.get('nullable', True)]

        print(f"Required fields ({len(required_fields)}):")
        if required_fields:
            for field_name in required_fields:
                print(f"  - {field_name}")
        else:
            print("  (none)")

        print(f"\nOptional fields ({len(optional_fields)}):")
        # Show first 10 optional fields
        for field_name in optional_fields[:10]:
            print(f"  - {field_name}")
        if len(optional_fields) > 10:
            print(f"  ... and {len(optional_fields) - 10} more")

        # Step 6: Example query construction
        print("\nStep 6: Building a Query from Schema")
        print("-" * 80)

        # Select common fields that exist
        desired_fields = ['Id', 'Name', 'Email', 'Company', 'Status', 'CreatedDate']
        available_fields = [f['name'] for f in fields]
        query_fields = [f for f in desired_fields if f in available_fields]

        if query_fields:
            example_query = f"SELECT {', '.join(query_fields)} FROM Lead LIMIT 10"
            print("Based on discovered fields, here's an example query:\n")
            print(f"  {example_query}\n")
            print("You can execute this query with:")
            print(f"  leads = client.query(\"{example_query}\")")
        else:
            print("No common fields found. Use field discovery to build queries.")

        # Step 7: Show relationship fields
        print("\nStep 7: Relationship Fields")
        print("-" * 80)

        # Look for fields that might be relationships (typically end with Id or __c)
        potential_relationships = [
            f['name'] for f in fields
            if f['name'].endswith('Id') and f['name'] != 'Id'
        ]

        if potential_relationships:
            print("Potential relationship fields (can be used for joins):")
            for field_name in potential_relationships:
                print(f"  - {field_name}")
            print("\nTo query relationships, use dot notation:")
            print("  SELECT Lead.Name, Campaign.Name FROM Lead WHERE Campaign.Id != null")
        else:
            print("No obvious relationship fields found.")

        print("\n" + "=" * 80)
        print("Schema discovery complete!")
        print("\nNext steps:")
        print("  - Run query_recent_leads.py to see data in action")
        print("  - Experiment with different fields in your queries")
        print("  - Try joining related objects using relationship fields")

    except ConnectionError as e:
        print(f"\nConnection Error: {e}")
        print("\nMake sure the mock API server is running.")
        sys.exit(1)
    except ObjectNotFoundError as e:
        print(f"\nObject Not Found: {e}")
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
