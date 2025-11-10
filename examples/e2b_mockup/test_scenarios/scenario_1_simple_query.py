#!/usr/bin/env python3
"""
Scenario 1: Simple Lead Query
Tests agent's ability to execute a basic time-based query.

User Prompt: "Get all leads from the last 30 days"

Expected Behavior:
- Parse the user intent to query leads
- Generate SOQL with proper date filtering
- Execute query against Salesforce API
- Return results with proper date comparison

Success Criteria:
- Query uses date comparison (CreatedDate >= LAST_N_DAYS:30)
- Returns only leads from the last 30 days
- Results include core fields (Id, Name, Email, Company, CreatedDate)
- No errors during execution
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from salesforce_driver.client import SalesforceClient
from salesforce_driver.exceptions import SalesforceError


class Scenario1SimpleQuery:
    """Test scenario for simple date-based lead query"""

    def __init__(self):
        self.name = "Scenario 1: Simple Lead Query"
        self.description = "Test basic time-based query: 'Get all leads from the last 30 days'"
        self.user_prompt = "Get all leads from the last 30 days"
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

            # Calculate date threshold (30 days ago)
            date_threshold = datetime.now() - timedelta(days=30)
            date_str = date_threshold.strftime('%Y-%m-%d')

            # Build SOQL query
            # Note: In real Salesforce, we'd use LAST_N_DAYS:30
            # For testing with static data, we'll use explicit date comparison
            print("Step 2: Generate SOQL Query")
            soql = f"""
                SELECT Id, Name, Email, Company, Status, Source, CreatedDate
                FROM Lead
                WHERE CreatedDate >= {date_str}
                ORDER BY CreatedDate DESC
            """
            print(f"  Generated SOQL:\n{soql}\n")

            # Execute query
            print("Step 3: Execute Query")
            query_start = datetime.now()
            self.results = client.query(soql)
            query_time = (datetime.now() - query_start).total_seconds()
            print(f"  ✓ Query executed in {query_time:.3f}s\n")

            # Validate results
            print("Step 4: Validate Results")
            self._validate_results(date_threshold)

            # Calculate metrics
            self.metrics = {
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'query_time': query_time,
                'records_returned': len(self.results),
                'date_threshold': date_str,
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

    def _validate_results(self, date_threshold: datetime):
        """Validate query results against success criteria"""

        # Check if results exist
        if self.results is None:
            self.errors.append("No results returned from query")
            return

        if not isinstance(self.results, list):
            self.errors.append(f"Results should be a list, got {type(self.results)}")
            return

        print(f"  Records returned: {len(self.results)}")

        # If no results, that's okay - might just not have recent leads in test data
        if len(self.results) == 0:
            self.warnings.append("No leads found in the last 30 days (this may be expected with test data)")
            print("  ⚠ WARNING: No leads found in date range\n")
            return

        # Validate fields in results
        required_fields = ['Id', 'Name', 'Email', 'Company', 'CreatedDate']
        sample_record = self.results[0]

        missing_fields = [f for f in required_fields if f not in sample_record]
        if missing_fields:
            self.errors.append(f"Missing required fields in results: {missing_fields}")
            print(f"  ✗ Missing fields: {missing_fields}")
        else:
            print(f"  ✓ All required fields present")

        # Validate date filtering (check first few records)
        date_errors = 0
        for i, record in enumerate(self.results[:5]):  # Check first 5
            if 'CreatedDate' in record and record['CreatedDate']:
                try:
                    # Parse the date (handle various formats)
                    created_date_str = record['CreatedDate']
                    if 'T' in created_date_str:
                        created_date = datetime.fromisoformat(created_date_str.replace('Z', '+00:00'))
                    else:
                        created_date = datetime.strptime(created_date_str, '%Y-%m-%d')

                    # Remove timezone for comparison if present
                    if created_date.tzinfo:
                        created_date = created_date.replace(tzinfo=None)

                    if created_date < date_threshold:
                        date_errors += 1
                except Exception as e:
                    self.warnings.append(f"Could not parse date for record {i}: {str(e)}")

        if date_errors > 0:
            self.errors.append(f"{date_errors} records have dates outside the 30-day window")
            print(f"  ✗ Date filtering error: {date_errors} records outside range")
        else:
            print(f"  ✓ Date filtering working correctly")

        print(f"  ✓ Validation complete\n")

    def _print_results(self):
        """Print formatted results"""
        print(f"{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

        if self.results and len(self.results) > 0:
            print(f"Sample Records (showing first 3 of {len(self.results)}):\n")
            for i, record in enumerate(self.results[:3]):
                print(f"  Record {i+1}:")
                print(f"    Id:          {record.get('Id', 'N/A')}")
                print(f"    Name:        {record.get('Name', 'N/A')}")
                print(f"    Email:       {record.get('Email', 'N/A')}")
                print(f"    Company:     {record.get('Company', 'N/A')}")
                print(f"    Status:      {record.get('Status', 'N/A')}")
                print(f"    Source:      {record.get('Source', 'N/A')}")
                print(f"    CreatedDate: {record.get('CreatedDate', 'N/A')}")
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
    scenario = Scenario1SimpleQuery()
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
