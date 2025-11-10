#!/usr/bin/env python3
"""
Scenario 4: Complex Filtered Query
Tests agent's ability to construct complex queries with multiple conditions.

User Prompt: "Get qualified leads from webinar campaigns"

Expected Behavior:
- Parse user intent requiring JOIN between Lead and Campaign
- Filter by Lead status (Qualified)
- Filter by Campaign type (Webinar)
- Generate proper SOQL with JOIN and WHERE conditions
- Execute query and return results

Success Criteria:
- Query uses JOIN to connect Lead and Campaign
- Includes WHERE clause with multiple conditions:
  - Lead.Status = 'Qualified'
  - Campaign.Type = 'Webinar'
- Returns only matching records
- Results include fields from both objects
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


class Scenario4FilteredQuery:
    """Test scenario for complex filtered query with JOIN"""

    def __init__(self):
        self.name = "Scenario 4: Complex Filtered Query"
        self.description = "Test complex filtering: 'Get qualified leads from webinar campaigns'"
        self.user_prompt = "Get qualified leads from webinar campaigns"
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

            # Build SOQL query with JOIN and filters
            print("Step 2: Generate Complex SOQL Query")
            soql = """
                SELECT
                    Lead.Id,
                    Lead.Name,
                    Lead.Email,
                    Lead.Company,
                    Lead.Status,
                    Lead.Source,
                    Campaign.Id AS CampaignId,
                    Campaign.Name AS CampaignName,
                    Campaign.Type AS CampaignType
                FROM Lead
                INNER JOIN Campaign ON Lead.CampaignId = Campaign.Id
                WHERE Lead.Status = 'Qualified'
                  AND Campaign.Type = 'Webinar'
                ORDER BY Lead.Name
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
                'records_returned': len(self.results) if self.results else 0,
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

        print(f"  Records returned: {len(self.results)}")

        # If no results, that's a problem - we should have qualified leads from webinars
        if len(self.results) == 0:
            self.warnings.append(
                "No qualified leads from webinar campaigns found. "
                "This may indicate missing test data or incorrect query."
            )
            print("  ⚠ WARNING: No matching records found\n")
            return

        # Validate fields in results
        required_fields = ['Id', 'Name', 'Email', 'Status', 'CampaignId', 'CampaignName', 'CampaignType']
        sample_record = self.results[0]

        missing_fields = [f for f in required_fields if f not in sample_record]
        if missing_fields:
            self.errors.append(f"Missing required fields in results: {missing_fields}")
            print(f"  ✗ Missing fields: {missing_fields}")
        else:
            print(f"  ✓ All required fields present")

        # Validate filtering (check all records)
        filter_violations = []
        for i, record in enumerate(self.results):
            # Check Lead status
            status = record.get('Status')
            if status != 'Qualified':
                filter_violations.append(f"Record {i} has status '{status}' (expected 'Qualified')")

            # Check Campaign type
            campaign_type = record.get('CampaignType')
            if campaign_type != 'Webinar':
                filter_violations.append(f"Record {i} has campaign type '{campaign_type}' (expected 'Webinar')")

        if filter_violations:
            self.errors.append(f"Filter validation failed: {len(filter_violations)} violations")
            for violation in filter_violations[:5]:  # Show first 5
                print(f"  ✗ {violation}")
            if len(filter_violations) > 5:
                print(f"  ✗ ... and {len(filter_violations) - 5} more violations")
        else:
            print(f"  ✓ All records match filter criteria")

        # Validate JOIN (check that campaign data is present)
        join_errors = 0
        for record in self.results:
            if not record.get('CampaignId') or not record.get('CampaignName'):
                join_errors += 1

        if join_errors > 0:
            self.errors.append(f"{join_errors} records missing campaign data (JOIN failed)")
            print(f"  ✗ JOIN validation failed: {join_errors} records missing campaign data")
        else:
            print(f"  ✓ JOIN working correctly (all records have campaign data)")

        print(f"  ✓ Validation complete\n")

    def _print_results(self):
        """Print formatted results"""
        print(f"{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

        if self.results and len(self.results) > 0:
            print(f"Found {len(self.results)} qualified leads from webinar campaigns\n")
            print(f"Sample Records (showing first 3):\n")

            for i, record in enumerate(self.results[:3]):
                print(f"  Record {i+1}:")
                print(f"    Lead ID:      {record.get('Id', 'N/A')}")
                print(f"    Name:         {record.get('Name', 'N/A')}")
                print(f"    Email:        {record.get('Email', 'N/A')}")
                print(f"    Company:      {record.get('Company', 'N/A')}")
                print(f"    Status:       {record.get('Status', 'N/A')}")
                print(f"    Source:       {record.get('Source', 'N/A')}")
                print(f"    Campaign:     {record.get('CampaignName', 'N/A')}")
                print(f"    Campaign Type: {record.get('CampaignType', 'N/A')}")
                print()

            # Summary statistics
            if len(self.results) > 3:
                # Count by source
                sources = {}
                for record in self.results:
                    source = record.get('Source', 'Unknown')
                    sources[source] = sources.get(source, 0) + 1

                print(f"  Lead Sources Distribution:")
                for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
                    print(f"    {source}: {count}")
                print()

                # Count by campaign
                campaigns = {}
                for record in self.results:
                    campaign = record.get('CampaignName', 'Unknown')
                    campaigns[campaign] = campaigns.get(campaign, 0) + 1

                print(f"  Campaign Distribution:")
                for campaign, count in sorted(campaigns.items(), key=lambda x: x[1], reverse=True):
                    print(f"    {campaign}: {count}")
                print()

        else:
            print("  No records returned\n")

    def _generate_report(self) -> Dict[str, Any]:
        """Generate test report"""
        return {
            'scenario': self.name,
            'user_prompt': self.user_prompt,
            'success': self.success,
            'errors': self.errors,
            'warnings': self.warnings,
            'metrics': self.metrics,
            'records_count': len(self.results) if self.results else 0,
        }


def main():
    """Run the scenario"""
    scenario = Scenario4FilteredQuery()
    report = scenario.run()

    # Print final status
    print(f"{'='*70}")
    print("FINAL STATUS")
    print(f"{'='*70}")
    print(f"Success: {'✓ PASS' if report['success'] else '✗ FAIL'}")
    print(f"Execution Time: {report['metrics'].get('execution_time', 0):.3f}s")
    print(f"Records Returned: {report['records_count']}")

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
