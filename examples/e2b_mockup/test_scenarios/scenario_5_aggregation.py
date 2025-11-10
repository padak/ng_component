#!/usr/bin/env python3
"""
Scenario 5: Aggregation Query
Tests agent's ability to construct analytics queries with aggregation.

User Prompt: "Which campaign has the most leads?"

Expected Behavior:
- Parse user intent requiring aggregation
- Generate SOQL with GROUP BY and COUNT
- Add ORDER BY to find the top result
- Execute query and return results

Success Criteria:
- Query uses COUNT() to aggregate leads
- Includes GROUP BY Campaign
- Uses ORDER BY to rank campaigns
- Returns campaign name with lead count
- Correctly identifies the top campaign
- No errors during execution
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from salesforce_driver.client import SalesforceClient
from salesforce_driver.exceptions import SalesforceError


class Scenario5Aggregation:
    """Test scenario for aggregation and analytics queries"""

    def __init__(self):
        self.name = "Scenario 5: Aggregation Query"
        self.description = "Test analytics query: 'Which campaign has the most leads?'"
        self.user_prompt = "Which campaign has the most leads?"
        self.success = False
        self.errors = []
        self.warnings = []
        self.metrics = {}
        self.results = None

    def run(self) -> Dict[str, Any]:
        """Execute the test scenario"""
        print(f"\n{'='*70}")
        print(f"{self.name}")
        print(f"{'='*70}")
        print(f"Description: {self.description}")
        print(f"User Prompt: \"{self.user_prompt}\"")
        print(f"{'='*70}\n")

        start_time = datetime.now()

        try:
            # Initialize client
            print("Step 1: Initialize Salesforce Client")
            client = SalesforceClient()
            print("  ✓ Client initialized\n")

            # Build SOQL query with aggregation
            print("Step 2: Generate Aggregation SOQL Query")
            soql = """
                SELECT
                    Campaign.Id AS CampaignId,
                    Campaign.Name AS CampaignName,
                    Campaign.Type AS CampaignType,
                    Campaign.Status AS CampaignStatus,
                    COUNT(Lead.Id) AS LeadCount
                FROM Lead
                INNER JOIN Campaign ON Lead.CampaignId = Campaign.Id
                GROUP BY Campaign.Id, Campaign.Name, Campaign.Type, Campaign.Status
                ORDER BY LeadCount DESC
                LIMIT 10
            """
            print("  Generated SOQL:")
            print("  " + "\n  ".join(soql.strip().split('\n')))
            print()

            # Execute query
            print("Step 3: Execute Query")
            query_start = datetime.now()
            self.results = client.query(soql)
            query_time = (datetime.now() - query_start).total_seconds()
            print(f"  ✓ Query executed in {query_time:.3f}s\n")

            # Validate results
            print("Step 4: Validate Results")
            self._validate_results()

            # Calculate metrics
            self.metrics = {
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'query_time': query_time,
                'campaigns_returned': len(self.results) if self.results else 0,
                'top_campaign': self.results[0].get('CampaignName') if self.results else None,
                'top_lead_count': self.results[0].get('LeadCount') if self.results else 0,
            }

            # Mark as successful if no errors
            if not self.errors:
                self.success = True

        except SalesforceError as e:
            self.errors.append(f"Salesforce API error: {str(e)}")
            print(f"  ✗ ERROR: {str(e)}\n")
        except Exception as e:
            self.errors.append(f"Unexpected error: {str(e)}")
            print(f"  ✗ UNEXPECTED ERROR: {str(e)}\n")

        # Print results
        self._print_results()

        return self._generate_report()

    def _validate_results(self):
        """Validate query results against success criteria"""

        # Check if results exist
        if self.results is None:
            self.errors.append("No results returned from query")
            print("  ✗ No results returned\n")
            return

        if not isinstance(self.results, list):
            self.errors.append(f"Results should be a list, got {type(self.results)}")
            print(f"  ✗ Invalid result type: {type(self.results)}\n")
            return

        print(f"  Campaigns returned: {len(self.results)}")

        # If no results, that's a problem
        if len(self.results) == 0:
            self.errors.append(
                "No campaigns found with leads. "
                "This indicates missing test data or incorrect query."
            )
            print("  ✗ ERROR: No campaigns found\n")
            return

        # Validate fields in results
        required_fields = ['CampaignId', 'CampaignName', 'LeadCount']
        sample_record = self.results[0]

        missing_fields = [f for f in required_fields if f not in sample_record]
        if missing_fields:
            self.errors.append(f"Missing required fields in results: {missing_fields}")
            print(f"  ✗ Missing fields: {missing_fields}")
        else:
            print(f"  ✓ All required fields present")

        # Validate aggregation (LeadCount should be numeric)
        lead_count_errors = 0
        for i, record in enumerate(self.results):
            lead_count = record.get('LeadCount')
            if not isinstance(lead_count, (int, float)):
                lead_count_errors += 1

        if lead_count_errors > 0:
            self.errors.append(f"{lead_count_errors} records have invalid LeadCount values")
            print(f"  ✗ LeadCount validation failed: {lead_count_errors} invalid values")
        else:
            print(f"  ✓ LeadCount values are valid")

        # Validate ordering (should be descending by LeadCount)
        ordering_errors = False
        for i in range(len(self.results) - 1):
            current_count = self.results[i].get('LeadCount', 0)
            next_count = self.results[i + 1].get('LeadCount', 0)
            if current_count < next_count:
                ordering_errors = True
                break

        if ordering_errors:
            self.errors.append("Results are not properly ordered by LeadCount DESC")
            print(f"  ✗ Ordering validation failed")
        else:
            print(f"  ✓ Results properly ordered by LeadCount DESC")

        # Validate that top campaign has the most leads
        if len(self.results) > 0:
            top_campaign = self.results[0]
            top_lead_count = top_campaign.get('LeadCount', 0)
            print(f"  ✓ Top campaign: {top_campaign.get('CampaignName')} with {top_lead_count} leads")

        print(f"  ✓ Validation complete\n")

    def _print_results(self):
        """Print formatted results"""
        print(f"{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

        if self.results and len(self.results) > 0:
            # Answer the user's question
            top_campaign = self.results[0]
            print(f"ANSWER: The campaign with the most leads is:")
            print(f"  Campaign: {top_campaign.get('CampaignName', 'N/A')}")
            print(f"  Type:     {top_campaign.get('CampaignType', 'N/A')}")
            print(f"  Status:   {top_campaign.get('CampaignStatus', 'N/A')}")
            print(f"  Leads:    {top_campaign.get('LeadCount', 0)}")
            print()

            # Show top 5 campaigns
            if len(self.results) > 1:
                print(f"Top {min(5, len(self.results))} Campaigns by Lead Count:\n")
                for i, record in enumerate(self.results[:5], 1):
                    print(f"  {i}. {record.get('CampaignName', 'N/A')}")
                    print(f"     Type:   {record.get('CampaignType', 'N/A')}")
                    print(f"     Status: {record.get('CampaignStatus', 'N/A')}")
                    print(f"     Leads:  {record.get('LeadCount', 0)}")
                    print()

            # Summary statistics
            total_leads = sum(r.get('LeadCount', 0) for r in self.results)
            avg_leads = total_leads / len(self.results) if self.results else 0

            print(f"Summary Statistics:")
            print(f"  Total Campaigns: {len(self.results)}")
            print(f"  Total Leads:     {total_leads}")
            print(f"  Average Leads:   {avg_leads:.1f} per campaign")
            print(f"  Highest:         {self.results[0].get('LeadCount', 0)} leads")
            print(f"  Lowest:          {self.results[-1].get('LeadCount', 0)} leads")

            # Distribution by type
            print(f"\n  Campaign Type Distribution:")
            type_stats = {}
            for record in self.results:
                campaign_type = record.get('CampaignType', 'Unknown')
                if campaign_type not in type_stats:
                    type_stats[campaign_type] = {'campaigns': 0, 'leads': 0}
                type_stats[campaign_type]['campaigns'] += 1
                type_stats[campaign_type]['leads'] += record.get('LeadCount', 0)

            for campaign_type, stats in sorted(type_stats.items()):
                print(f"    {campaign_type}: {stats['campaigns']} campaigns, {stats['leads']} leads")

            print()

        else:
            print("  No campaigns found\n")

    def _generate_report(self) -> Dict[str, Any]:
        """Generate test report"""
        return {
            'scenario': self.name,
            'user_prompt': self.user_prompt,
            'success': self.success,
            'errors': self.errors,
            'warnings': self.warnings,
            'metrics': self.metrics,
            'results': self.results,
        }


def main():
    """Run the scenario"""
    scenario = Scenario5Aggregation()
    report = scenario.run()

    # Print final status
    print(f"{'='*70}")
    print("FINAL STATUS")
    print(f"{'='*70}")
    print(f"Success: {'✓ PASS' if report['success'] else '✗ FAIL'}")
    print(f"Execution Time: {report['metrics'].get('execution_time', 0):.3f}s")
    print(f"Campaigns Analyzed: {report['metrics'].get('campaigns_returned', 0)}")
    if report['metrics'].get('top_campaign'):
        print(f"Top Campaign: {report['metrics']['top_campaign']} ({report['metrics']['top_lead_count']} leads)")

    if report['errors']:
        print(f"\nErrors ({len(report['errors'])}):")
        for error in report['errors']:
            print(f"  - {error}")

    if report['warnings']:
        print(f"\nWarnings ({len(report['warnings'])}):")
        for warning in report['warnings']:
            print(f"  - {warning}")

    print(f"{'='*70}\n")

    # Exit with appropriate code
    sys.exit(0 if report['success'] else 1)


if __name__ == "__main__":
    main()
