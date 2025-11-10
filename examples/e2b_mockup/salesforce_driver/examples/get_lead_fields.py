#!/usr/bin/env python3
"""
Discovery example: Get Lead object structure

This script demonstrates how to discover the schema of a Salesforce object
before querying it. This is essential for understanding what fields are
available and their data types.

Usage:
    export SF_API_KEY="your-api-key"
    python get_lead_fields.py
"""

import os
import sys

# Add parent directory to path to import salesforce_driver
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from salesforce_driver import SalesforceClient, SalesforceError


def main():
    """Discover and display Lead object schema"""

    # Initialize client
    try:
        client = SalesforceClient()
        print("Connected to Salesforce Mock API")
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        print("\nMake sure to set SF_API_KEY environment variable:")
        print("  export SF_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        # First, list all available objects
        print("\nStep 1: Discovering available objects...")
        objects = client.list_objects()
        print(f"Available Salesforce objects: {', '.join(objects)}")

        # Check if Lead exists
        if 'Lead' not in objects:
            print("\nWarning: 'Lead' object not found!")
            print("This example requires the Lead object to be available.")
            sys.exit(1)

        # Get Lead object schema
        print("\nStep 2: Retrieving Lead object schema...")
        fields = client.get_fields('Lead')

        # Display field information
        print(f"\nLead Object Fields ({len(fields)} total):")
        print("=" * 100)

        # Sort fields by name for easier reading
        for field_name in sorted(fields.keys()):
            field_def = fields[field_name]

            field_type = field_def.get('type', 'unknown')
            nullable = field_def.get('nullable', True)
            label = field_def.get('label', field_name)

            nullable_str = "nullable" if nullable else "required"

            print(f"\n{field_name}")
            print(f"  Label:      {label}")
            print(f"  Type:       {field_type}")
            print(f"  Nullable:   {nullable_str}")

            # Show additional metadata if available
            if 'length' in field_def:
                print(f"  Max Length: {field_def['length']}")
            if 'defaultValue' in field_def:
                print(f"  Default:    {field_def['defaultValue']}")
            if 'description' in field_def:
                print(f"  Description: {field_def['description']}")

        # Summary
        print("\n" + "=" * 100)
        print("\nField Type Summary:")

        # Count fields by type
        type_counts = {}
        for field_def in fields.values():
            field_type = field_def.get('type', 'unknown')
            type_counts[field_type] = type_counts.get(field_type, 0) + 1

        for field_type in sorted(type_counts.keys()):
            count = type_counts[field_type]
            print(f"  {field_type}: {count}")

        # Show required vs optional
        required_fields = [
            name for name, def_ in fields.items()
            if not def_.get('nullable', True)
        ]
        optional_fields = [
            name for name, def_ in fields.items()
            if def_.get('nullable', True)
        ]

        print(f"\nRequired fields ({len(required_fields)}): {', '.join(required_fields) if required_fields else 'None'}")
        print(f"Optional fields ({len(optional_fields)}): {', '.join(sorted(optional_fields)[:10])}{'...' if len(optional_fields) > 10 else ''}")

        # Example query construction
        print("\n" + "=" * 100)
        print("\nExample: Building a query from discovered fields")

        # Select a few common fields for the example
        common_fields = ['Id', 'Name', 'Email', 'Company', 'Status']
        available_common = [f for f in common_fields if f in fields]

        if available_common:
            example_query = f"SELECT {', '.join(available_common)} FROM Lead LIMIT 10"
            print(f"\nSample query:")
            print(f"  {example_query}")

            print(f"\nYou can execute this query using:")
            print(f"  leads = client.query(\"{example_query}\")")

    except SalesforceError as e:
        print(f"\nSalesforce error: {e}")
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
