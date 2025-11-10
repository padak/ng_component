#!/usr/bin/env python3
"""
Relationship example: Get leads with campaign information

This script demonstrates how to join related objects in Salesforce
using relationship queries (similar to SQL JOINs).

Usage:
    export SF_API_KEY="your-api-key"
    python join_lead_campaign.py
"""

import os
import sys

# Add parent directory to path to import salesforce_driver
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from salesforce_driver import SalesforceClient, SalesforceError


def main():
    """Query leads with their associated campaign information"""

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
        # First, let's understand the data model
        print("\nStep 1: Discovering available objects...")
        objects = client.list_objects()
        print(f"Available objects: {', '.join(objects)}")

        # Verify we have both Lead and Campaign
        has_lead = 'Lead' in objects
        has_campaign = 'Campaign' in objects

        if not has_lead or not has_campaign:
            print(f"\nWarning: Required objects not found!")
            print(f"  Lead object: {'Available' if has_lead else 'Missing'}")
            print(f"  Campaign object: {'Available' if has_campaign else 'Missing'}")
            sys.exit(1)

        # Query leads WITH campaign information
        print("\nStep 2: Querying leads with campaign relationships...")

        query = """
            SELECT
                Lead.Id,
                Lead.Name,
                Lead.Email,
                Lead.Company,
                Lead.Status,
                Lead.CreatedDate,
                Campaign.Id AS CampaignId,
                Campaign.Name AS CampaignName,
                Campaign.Status AS CampaignStatus,
                Campaign.Type AS CampaignType
            FROM Lead
            WHERE Campaign.Id != null
            ORDER BY Campaign.Name, Lead.Name
        """

        leads_with_campaigns = client.query(query)

        # Display results
        print(f"\nFound {len(leads_with_campaigns)} leads associated with campaigns:")
        print("=" * 120)

        if not leads_with_campaigns:
            print("\nNo leads with campaign associations found.")
            print("\nTrying alternative approach: query all leads to see campaign data...")

            # Fallback: get all leads to see what's available
            all_leads = client.query(
                "SELECT Id, Name, Email, Campaign.Name AS CampaignName FROM Lead LIMIT 10"
            )

            if all_leads:
                print(f"\nAll leads (sample of {len(all_leads)}):")
                for lead in all_leads:
                    campaign = lead.get('CampaignName', 'No campaign')
                    print(f"  {lead.get('Name', 'N/A'):30} - Campaign: {campaign}")
            else:
                print("No leads found in the system.")

        else:
            # Group leads by campaign
            campaigns = {}

            for lead in leads_with_campaigns:
                campaign_name = lead.get('CampaignName', 'Unknown Campaign')

                if campaign_name not in campaigns:
                    campaigns[campaign_name] = {
                        'campaign_id': lead.get('CampaignId'),
                        'campaign_status': lead.get('CampaignStatus'),
                        'campaign_type': lead.get('CampaignType'),
                        'leads': []
                    }

                campaigns[campaign_name]['leads'].append(lead)

            # Display leads grouped by campaign
            for campaign_name in sorted(campaigns.keys()):
                campaign_info = campaigns[campaign_name]
                leads = campaign_info['leads']

                print(f"\nCampaign: {campaign_name}")
                print(f"  ID:     {campaign_info['campaign_id']}")
                print(f"  Status: {campaign_info['campaign_status']}")
                print(f"  Type:   {campaign_info['campaign_type']}")
                print(f"  Leads:  {len(leads)}")
                print("-" * 120)

                for lead in leads:
                    name = lead.get('Name', 'N/A')
                    email = lead.get('Email', 'N/A')
                    company = lead.get('Company', 'N/A')
                    status = lead.get('Status', 'N/A')

                    print(f"    {name:30} | {email:30} | {company:20} | {status}")

            # Campaign summary
            print("\n" + "=" * 120)
            print("\nCampaign Summary:")
            print(f"  Total campaigns with leads: {len(campaigns)}")
            print(f"  Total leads in campaigns: {len(leads_with_campaigns)}")

            # Calculate average leads per campaign
            avg_leads = len(leads_with_campaigns) / len(campaigns)
            print(f"  Average leads per campaign: {avg_leads:.1f}")

            # Find most and least active campaigns
            campaign_sizes = [(name, len(info['leads'])) for name, info in campaigns.items()]
            campaign_sizes.sort(key=lambda x: x[1], reverse=True)

            print(f"\n  Most active campaign:")
            print(f"    {campaign_sizes[0][0]}: {campaign_sizes[0][1]} leads")

            if len(campaign_sizes) > 1:
                print(f"\n  Least active campaign:")
                print(f"    {campaign_sizes[-1][0]}: {campaign_sizes[-1][1]} leads")

            # Lead status breakdown within campaigns
            print(f"\n  Lead status distribution across campaigns:")
            all_statuses = {}
            for lead in leads_with_campaigns:
                status = lead.get('Status', 'Unknown')
                all_statuses[status] = all_statuses.get(status, 0) + 1

            for status in sorted(all_statuses.keys()):
                count = all_statuses[status]
                percentage = (count / len(leads_with_campaigns)) * 100
                print(f"    {status}: {count} ({percentage:.1f}%)")

        # Additional analysis: Leads WITHOUT campaigns
        print("\n" + "=" * 120)
        print("\nAdditional Analysis: Leads without campaigns")

        leads_without_campaigns = client.query(
            "SELECT Id, Name, Email, Status FROM Lead WHERE Campaign.Id = null"
        )

        print(f"  Leads without campaigns: {len(leads_without_campaigns)}")

        if leads_without_campaigns and len(leads_without_campaigns) <= 10:
            print(f"\n  Leads needing campaign assignment:")
            for lead in leads_without_campaigns:
                print(f"    {lead.get('Name', 'N/A'):30} | {lead.get('Email', 'N/A'):30} | {lead.get('Status', 'N/A')}")

        # Get campaign statistics
        print("\n" + "=" * 120)
        print("\nCampaign Statistics:")

        all_campaigns = client.query("SELECT Id, Name, Status, Type FROM Campaign")
        print(f"  Total campaigns in system: {len(all_campaigns)}")

        if all_campaigns:
            # Count campaigns by status
            campaign_statuses = {}
            for campaign in all_campaigns:
                status = campaign.get('Status', 'Unknown')
                campaign_statuses[status] = campaign_statuses.get(status, 0) + 1

            print(f"\n  Campaigns by status:")
            for status in sorted(campaign_statuses.keys()):
                count = campaign_statuses[status]
                print(f"    {status}: {count}")

            # Count campaigns by type
            campaign_types = {}
            for campaign in all_campaigns:
                camp_type = campaign.get('Type', 'Unknown')
                campaign_types[camp_type] = campaign_types.get(camp_type, 0) + 1

            print(f"\n  Campaigns by type:")
            for camp_type in sorted(campaign_types.keys()):
                count = campaign_types[camp_type]
                print(f"    {camp_type}: {count}")

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
