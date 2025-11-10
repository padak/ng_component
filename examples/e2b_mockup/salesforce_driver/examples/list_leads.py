#!/usr/bin/env python3
"""
Simple example: List all leads

This script demonstrates the most basic Salesforce operation:
querying all Lead records and displaying them.

Usage:
    export SF_API_KEY="your-api-key"
    python list_leads.py
"""

import os
import sys

# Add parent directory to path to import salesforce_driver
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from salesforce_driver import SalesforceClient, SalesforceError


def main():
    """List all leads with basic information"""

    # Initialize client (uses SF_API_KEY from environment)
    try:
        client = SalesforceClient()
        print("Connected to Salesforce Mock API")
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        print("\nMake sure to set SF_API_KEY environment variable:")
        print("  export SF_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        # Query all leads with basic fields
        print("\nQuerying leads...")
        leads = client.query(
            "SELECT Id, Name, Email, Company, Status, CreatedDate FROM Lead"
        )

        # Display results
        print(f"\nFound {len(leads)} leads:")
        print("=" * 100)

        for i, lead in enumerate(leads, 1):
            print(f"\n{i}. {lead.get('Name', 'N/A')}")
            print(f"   ID:         {lead.get('Id', 'N/A')}")
            print(f"   Email:      {lead.get('Email', 'N/A')}")
            print(f"   Company:    {lead.get('Company', 'N/A')}")
            print(f"   Status:     {lead.get('Status', 'N/A')}")
            print(f"   Created:    {lead.get('CreatedDate', 'N/A')}")

        # Summary
        print("\n" + "=" * 100)
        print(f"Total leads: {len(leads)}")

        # Count leads with email
        leads_with_email = [l for l in leads if l.get('Email')]
        print(f"Leads with email: {len(leads_with_email)}")

        # Count by status
        statuses = {}
        for lead in leads:
            status = lead.get('Status', 'Unknown')
            statuses[status] = statuses.get(status, 0) + 1

        print(f"\nLeads by status:")
        for status, count in sorted(statuses.items()):
            print(f"  {status}: {count}")

    except SalesforceError as e:
        print(f"\nSalesforce error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == '__main__':
    main()
