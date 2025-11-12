"""
Campaign Attribution Analysis Script
====================================
This script calculates cumulative opportunity values attributed to campaigns
by tracking the relationship: Campaigns → Leads → Opportunities

Usage:
    python campaign_attribution.py [--api-url URL] [--api-key KEY] [--output FILE]

Requirements:
    - salesforce_driver module
    - Access to Salesforce API
"""

import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient


class CampaignAttributionAnalyzer:
    """Analyzes campaign performance based on attributed opportunity values."""
    
    def __init__(self, api_url: str, api_key: str):
        """Initialize the analyzer with Salesforce credentials."""
        self.client = SalesforceClient(api_url=api_url, api_key=api_key)
        self.leads = []
        self.opportunities = []
        
    def fetch_data(self) -> None:
        """Fetch all necessary data from Salesforce."""
        print("Fetching leads from Salesforce...")
        self.leads = self.client.query(
            "SELECT Id, CampaignId, FirstName, LastName, Company FROM Lead"
        )
        
        print("Fetching opportunities from Salesforce...")
        self.opportunities = self.client.query(
            "SELECT Id, Name, Amount, LeadId FROM Opportunity"
        )
        
        print(f"Retrieved {len(self.leads)} leads and {len(self.opportunities)} opportunities")
    
    def build_lead_mappings(self) -> tuple:
        """Create mappings for lead-to-campaign and lead information."""
        lead_to_campaign = {}
        lead_info = {}
        
        for lead in self.leads:
            lead_id = lead['Id']
            campaign_id = lead.get('CampaignId')
            
            lead_to_campaign[lead_id] = campaign_id
            lead_info[lead_id] = {
                'name': f"{lead.get('FirstName', '')} {lead.get('LastName', '')}".strip(),
                'company': lead.get('Company', 'N/A')
            }
        
        return lead_to_campaign, lead_info
    
    def calculate_attribution(self, lead_to_campaign: Dict, lead_info: Dict) -> tuple:
        """Calculate opportunity values attributed to each campaign."""
        campaign_values = {}
        opportunity_details = {}
        
        for opp in self.opportunities:
            lead_id = opp.get('LeadId')
            amount = opp.get('Amount')
            
            # Skip opportunities without lead or amount
            if not lead_id or amount is None:
                continue
            
            campaign_id = lead_to_campaign.get(lead_id)
            
            # Only process if lead has a campaign association
            if campaign_id:
                amount_value = float(amount)
                
                if campaign_id not in campaign_values:
                    campaign_values[campaign_id] = 0
                    opportunity_details[campaign_id] = []
                
                campaign_values[campaign_id] += amount_value
                opportunity_details[campaign_id].append({
                    'opportunity_id': opp['Id'],
                    'opportunity_name': opp.get('Name'),
                    'amount': amount_value,
                    'lead_name': lead_info.get(lead_id, {}).get('name', 'Unknown'),
                    'lead_company': lead_info.get(lead_id, {}).get('company', 'N/A')
                })
        
        return campaign_values, opportunity_details
    
    def format_results(self, campaign_values: Dict, opportunity_details: Dict) -> Dict[str, Any]:
        """Format the analysis results into a structured output."""
        results = []
        
        for campaign_id, total_value in campaign_values.items():
            opps = opportunity_details.get(campaign_id, [])
            
            # Sort opportunities by amount descending
            opps.sort(key=lambda x: x['amount'], reverse=True)
            
            results.append({
                'campaign_id': campaign_id,
                'total_opportunity_value': total_value,
                'opportunity_count': len(opps),
                'average_opportunity_value': total_value / len(opps) if opps else 0,
                'opportunities': opps
            })
        
        # Sort campaigns by total value descending
        results.sort(key=lambda x: x['total_opportunity_value'], reverse=True)
        
        # Calculate summary statistics
        grand_total = sum(r['total_opportunity_value'] for r in results)
        total_opps = sum(r['opportunity_count'] for r in results)
        leads_with_campaigns = sum(1 for lead in self.leads if lead.get('CampaignId'))
        
        output = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_leads': len(self.leads),
                'total_opportunities': len(self.opportunities)
            },
            'summary': {
                'total_campaigns_with_opportunities': len(results),
                'total_leads_with_campaigns': leads_with_campaigns,
                'grand_total_opportunity_value': grand_total,
                'total_opportunities_attributed': total_opps,
                'average_value_per_campaign': grand_total / len(results) if results else 0,
                'average_value_per_opportunity': grand_total / total_opps if total_opps else 0
            },
            'campaigns': results
        }
        
        return output
    
    def analyze(self) -> Dict[str, Any]:
        """Run the complete attribution analysis."""
        self.fetch_data()
        lead_to_campaign, lead_info = self.build_lead_mappings()
        campaign_values, opportunity_details = self.calculate_attribution(
            lead_to_campaign, lead_info
        )
        return self.format_results(campaign_values, opportunity_details)
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print a human-readable summary of the results."""
        summary = results['summary']
        
        print("\n" + "="*80)
        print("CAMPAIGN ATTRIBUTION ANALYSIS SUMMARY")
        print("="*80)
        print(f"\nTotal Campaigns with Opportunities: {summary['total_campaigns_with_opportunities']}")
        print(f"Grand Total Opportunity Value: ${summary['grand_total_opportunity_value']:,.2f}")
        print(f"Total Opportunities Attributed: {summary['total_opportunities_attributed']}")
        print(f"Average Value per Campaign: ${summary['average_value_per_campaign']:,.2f}")
        print(f"Average Value per Opportunity: ${summary['average_value_per_opportunity']:,.2f}")
        
        print("\n" + "-"*80)
        print("TOP 10 CAMPAIGNS BY OPPORTUNITY VALUE")
        print("-"*80)
        
        for i, campaign in enumerate(results['campaigns'][:10], 1):
            print(f"\n{i}. {campaign['campaign_id']}")
            print(f"   Total Value: ${campaign['total_opportunity_value']:,.2f}")
            print(f"   Opportunities: {campaign['opportunity_count']}")
            print(f"   Avg per Opportunity: ${campaign['average_opportunity_value']:,.2f}")
            
            # Show top 3 opportunities
            top_opps = campaign['opportunities'][:3]
            if top_opps:
                print(f"   Top Opportunities:")
                for opp in top_opps:
                    print(f"     - {opp['opportunity_name']}: ${opp['amount']:,.2f}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Analyze campaign attribution based on opportunity values'
    )
    parser.add_argument(
        '--api-url',
        default='http://localhost:8000',
        help='Salesforce API URL (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--api-key',
        default='<api_key_here>',
        help='Salesforce API key'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file path (optional, prints to stdout if not specified)'
    )
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Only print summary, not full JSON output'
    )
    
    args = parser.parse_args()
    
    try:
        # Run analysis
        analyzer = CampaignAttributionAnalyzer(
            api_url=args.api_url,
            api_key=args.api_key
        )
        results = analyzer.analyze()
        
        # Print summary
        if args.summary_only or args.output:
            analyzer.print_summary(results)
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✓ Full results saved to: {args.output}")
        else:
            if not args.summary_only:
                print("\n" + "="*80)
                print("FULL JSON OUTPUT")
                print("="*80 + "\n")
                print(json.dumps(results, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())