#!/usr/bin/env python3
"""
Scenario 2: Object Discovery
Tests agent's ability to discover available Salesforce objects.

User Prompt: "What objects are available in Salesforce?"

Expected Behavior:
- Call list_objects() API method
- Parse and display available objects
- Show object metadata if available

Success Criteria:
- Successfully retrieves object list
- Returns all 4 test objects (Lead, Campaign, Account, Opportunity)
- Displays objects in a readable format
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


class Scenario2ObjectDiscovery:
    """Test scenario for object discovery workflow"""

    def __init__(self):
        self.name = "Scenario 2: Object Discovery"
        self.description = "Test object discovery: 'What objects are available in Salesforce?'"
        self.user_prompt = "What objects are available in Salesforce?"
        self.success = False
        self.errors = []
        self.warnings = []
        self.metrics = {}
        self.objects = None

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

            # Call list_objects API
            print("Step 2: Call list_objects() API")
            api_start = datetime.now()
            self.objects = client.list_objects()
            api_time = (datetime.now() - api_start).total_seconds()
            print(f"  ✓ API call completed in {api_time:.3f}s\n")

            # Validate results
            print("Step 3: Validate Results")
            self._validate_results()

            # Display objects
            print("Step 4: Display Available Objects")
            self._display_objects()

            # Calculate metrics
            self.metrics = {
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'api_time': api_time,
                'objects_count': len(self.objects) if self.objects else 0,
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
        """Validate API response against success criteria"""

        # Check if results exist
        if self.objects is None:
            self.errors.append("No objects returned from API")
            print("  ✗ No objects returned\n")
            return

        # Check result type
        if not isinstance(self.objects, list):
            self.errors.append(f"Objects should be a list, got {type(self.objects)}")
            print(f"  ✗ Invalid result type: {type(self.objects)}\n")
            return

        print(f"  Objects returned: {len(self.objects)}")

        # Check for expected objects (our test data has these 4 objects)
        expected_objects = ['Lead', 'Campaign', 'Account', 'Opportunity']

        missing_objects = [obj for obj in expected_objects if obj not in self.objects]
        if missing_objects:
            self.errors.append(f"Missing expected objects: {missing_objects}")
            print(f"  ✗ Missing objects: {missing_objects}")
        else:
            print(f"  ✓ All expected objects present")

        # Check object count
        if len(self.objects) < 4:
            self.warnings.append(f"Expected at least 4 objects, got {len(self.objects)}")
            print(f"  ⚠ WARNING: Expected at least 4 objects\n")
        else:
            print(f"  ✓ Object count correct ({len(self.objects)} >= 4)\n")

    def _display_objects(self):
        """Display objects in a readable format"""
        if not self.objects:
            print("  No objects to display\n")
            return

        print(f"  Available Salesforce Objects ({len(self.objects)}):\n")
        for i, obj in enumerate(sorted(self.objects), 1):
            print(f"    {i}. {obj}")
        print()

    def _print_results(self):
        """Print formatted results"""
        print(f"{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

        if self.objects:
            print(f"Discovery Summary:")
            print(f"  Total Objects: {len(self.objects)}")
            print(f"  Object List: {', '.join(sorted(self.objects))}")
        else:
            print("  No objects discovered")

        print()

    def _generate_report(self) -> Dict[str, Any]:
        """Generate test report"""
        return {
            'scenario': self.name,
            'user_prompt': self.user_prompt,
            'success': self.success,
            'errors': self.errors,
            'warnings': self.warnings,
            'metrics': self.metrics,
            'objects': self.objects if self.objects else [],
        }


def main():
    """Run the scenario"""
    scenario = Scenario2ObjectDiscovery()
    report = scenario.run()

    # Print final status
    print(f"{'='*70}")
    print("FINAL STATUS")
    print(f"{'='*70}")
    print(f"Success: {'✓ PASS' if report['success'] else '✗ FAIL'}")
    print(f"Execution Time: {report['metrics'].get('execution_time', 0):.3f}s")
    print(f"Objects Discovered: {len(report['objects'])}")

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
