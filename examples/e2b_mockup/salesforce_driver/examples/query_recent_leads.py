#!/usr/bin/env python3
"""
Filtering example: Query leads from the last 30 days

This script demonstrates how to filter Salesforce records by date
using WHERE clauses in SOQL queries.

Usage:
    export SF_API_KEY="your-api-key"
    python query_recent_leads.py
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to import salesforce_driver
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from salesforce_driver import SalesforceClient, SalesforceError


def main():
    """Query leads created in the last 30 days"""

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
        # Calculate date 30 days ago
        thirty_days_ago = datetime.now() - timedelta(days=30)
        date_filter = thirty_days_ago.strftime('%Y-%m-%d')

        print(f"\nQuerying leads created after {date_filter}...")

        # Query leads from last 30 days
        query = f"""
            SELECT Id, Name, Email, Company, Status, CreatedDate
            FROM Lead
            WHERE CreatedDate > {date_filter}
            ORDER BY CreatedDate DESC
        """

        leads = client.query(query)

        # Display results
        print(f"\nFound {len(leads)} leads created in the last 30 days:")
        print("=" * 100)

        if not leads:
            print("\nNo recent leads found.")
            print("\nTrying to query all leads to see available data...")

            # Fallback: get all leads to show what's available
            all_leads = client.query("SELECT Id, Name, CreatedDate FROM Lead LIMIT 5")

            if all_leads:
                print(f"\nFound {len(all_leads)} total leads (showing sample):")
                for lead in all_leads:
                    created = lead.get('CreatedDate', 'N/A')
                    print(f"  {lead.get('Name', 'N/A')} - Created: {created}")
            else:
                print("No leads found in the system.")

        else:
            # Group leads by week
            weeks = {}

            for lead in leads:
                # Parse created date
                created_str = lead.get('CreatedDate', '')
                if created_str:
                    try:
                        # Handle different date formats
                        if 'T' in created_str:
                            created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                        else:
                            created_date = datetime.strptime(created_str, '%Y-%m-%d')

                        # Calculate week
                        week_start = created_date - timedelta(days=created_date.weekday())
                        week_key = week_start.strftime('%Y-%m-%d')

                        if week_key not in weeks:
                            weeks[week_key] = []
                        weeks[week_key].append(lead)
                    except (ValueError, AttributeError):
                        # If date parsing fails, add to "Unknown" week
                        if 'Unknown' not in weeks:
                            weeks['Unknown'] = []
                        weeks['Unknown'].append(lead)

            # Display leads grouped by week
            for week in sorted(weeks.keys(), reverse=True):
                week_leads = weeks[week]
                print(f"\nWeek of {week} ({len(week_leads)} leads):")
                print("-" * 100)

                for lead in week_leads:
                    name = lead.get('Name', 'N/A')
                    email = lead.get('Email', 'N/A')
                    company = lead.get('Company', 'N/A')
                    status = lead.get('Status', 'N/A')
                    created = lead.get('CreatedDate', 'N/A')

                    print(f"  {name:30} | {email:30} | {company:20} | {status:10}")
                    print(f"    Created: {created}")

            # Summary statistics
            print("\n" + "=" * 100)
            print("\nSummary:")
            print(f"  Total recent leads: {len(leads)}")

            # Average leads per week
            if weeks:
                avg_per_week = len(leads) / len(weeks)
                print(f"  Average per week: {avg_per_week:.1f}")

            # Count by status
            statuses = {}
            for lead in leads:
                status = lead.get('Status', 'Unknown')
                statuses[status] = statuses.get(status, 0) + 1

            print(f"\n  Leads by status:")
            for status in sorted(statuses.keys()):
                count = statuses[status]
                percentage = (count / len(leads)) * 100
                print(f"    {status}: {count} ({percentage:.1f}%)")

            # Find leads without email
            no_email = [l for l in leads if not l.get('Email')]
            if no_email:
                print(f"\n  Warning: {len(no_email)} leads missing email addresses")

        # Additional queries: Compare with older leads
        print("\n" + "=" * 100)
        print("\nComparison with all-time data:")

        total_leads = client.query("SELECT Id FROM Lead")
        print(f"  Total leads in system: {len(total_leads)}")

        if total_leads:
            recent_percentage = (len(leads) / len(total_leads)) * 100
            print(f"  Recent leads (last 30 days): {len(leads)} ({recent_percentage:.1f}% of total)")

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
