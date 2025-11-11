#!/usr/bin/env python3
"""
Get All Leads from Salesforce

This script retrieves all leads from the Salesforce API and displays them
with key information (Id, FirstName, LastName, Email, Company, Status, CreatedDate).

Usage:
    export SF_API_KEY="your-api-key"
    python get_all_leads.py
"""

import sys
import os
import json

# Add parent directory to path to import salesforce_driver
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from salesforce_driver import SalesforceClient, SalesforceError


def main():
    """Retrieve and display all leads"""

    # Initialize client
    try:
        client = SalesforceClient()
        print("✓ Connected to Salesforce API\n")
    except Exception as e:
        print(f"✗ Failed to initialize client: {e}")
        print("\nMake sure to set SF_API_KEY environment variable:")
        print("  export SF_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        # Query all leads
        print("📋 Querying all leads...")
        leads = client.query(
            "SELECT Id, FirstName, LastName, Email, Company, Status, CreatedDate FROM Lead"
        )

        # Display summary
        print(f"\n✓ Found {len(leads)} leads\n")
        print("=" * 120)

        # Display each lead
        for i, lead in enumerate(leads, 1):
            first_name = lead.get('FirstName', '')
            last_name = lead.get('LastName', '')
            name = f"{first_name} {last_name}".strip() or 'N/A'
            email = lead.get('Email', 'N/A')
            company = lead.get('Company', 'N/A')
            status = lead.get('Status', 'N/A')
            created = lead.get('CreatedDate', 'N/A')
            lead_id = lead.get('Id', 'N/A')

            print(f"\n{i}. {name}")
            print(f"   ID:          {lead_id}")
            print(f"   Email:       {email}")
            print(f"   Company:     {company}")
            print(f"   Status:      {status}")
            print(f"   Created:     {created}")

        # Print summary statistics
        print("\n" + "=" * 120)
        print(f"\n📊 Summary Statistics:")
        print(f"   Total leads: {len(leads)}")

        # Count leads with email
        leads_with_email = [l for l in leads if l.get('Email') and l.get('Email').strip()]
        print(f"   Leads with email: {len(leads_with_email)}")

        # Count by status
        statuses = {}
        for lead in leads:
            status = lead.get('Status', 'Unknown')
            statuses[status] = statuses.get(status, 0) + 1

        print(f"\n   Leads by Status:")
        for status, count in sorted(statuses.items()):
            print(f"      • {status}: {count}")

        # Count by company
        companies = {}
        for lead in leads:
            company = lead.get('Company', 'Unknown')
            companies[company] = companies.get(company, 0) + 1

        print(f"\n   Top Companies:")
        for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"      • {company}: {count}")

        # Output as JSON for structured processing
        print("\n" + "=" * 120)
        print("\n📄 Full JSON Output:\n")
        print(json.dumps(leads, indent=2))

        return 0

    except SalesforceError as e:
        print(f"\n✗ Salesforce error: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        client.close()


if __name__ == '__main__':
    sys.exit(main())
