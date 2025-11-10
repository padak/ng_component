#!/usr/bin/env python3
"""
Scenario 3: Field Discovery
Tests agent's ability to discover field schema for a Salesforce object.

User Prompt: "What fields does the Lead object have?"

Expected Behavior:
- Call get_fields('Lead') API method
- Parse and display field schema
- Show field types and metadata

Success Criteria:
- Successfully retrieves field schema
- Returns complete field definitions
- Shows field names, types, and important attributes
- Displays results in a readable format
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


class Scenario3FieldDiscovery:
    """Test scenario for field schema discovery"""

    def __init__(self):
        self.name = "Scenario 3: Field Discovery"
        self.description = "Test field discovery: 'What fields does the Lead object have?'"
        self.user_prompt = "What fields does the Lead object have?"
        self.target_object = "Lead"
        self.success = False
        self.errors = []
        self.warnings = []
        self.metrics = {}
        self.schema = None

    def run(self) -> Dict[str, Any]:
        """Execute the test scenario"""
        print(f"\n{'='*70}")
        print(f"{self.name}")
        print(f"{'='*70}")
        print(f"Description: {self.description}")
        print(f"User Prompt: \"{self.user_prompt}\"")
        print(f"Target Object: {self.target_object}")
        print(f"{'='*70}\n")

        start_time = datetime.now()

        try:
            # Initialize client
            print("Step 1: Initialize Salesforce Client")
            client = SalesforceClient()
            print("  ✓ Client initialized\n")

            # Call get_fields API
            print(f"Step 2: Call get_fields('{self.target_object}') API")
            api_start = datetime.now()
            self.schema = client.get_fields(self.target_object)
            api_time = (datetime.now() - api_start).total_seconds()
            print(f"  ✓ API call completed in {api_time:.3f}s\n")

            # Validate results
            print("Step 3: Validate Results")
            self._validate_results()

            # Display schema
            print("Step 4: Display Field Schema")
            self._display_schema()

            # Calculate metrics
            field_count = len(self.schema.get('fields', [])) if self.schema else 0
            self.metrics = {
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'api_time': api_time,
                'fields_count': field_count,
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
        if self.schema is None:
            self.errors.append("No schema returned from API")
            print("  ✗ No schema returned\n")
            return

        # Check result type
        if not isinstance(self.schema, dict):
            self.errors.append(f"Schema should be a dict, got {type(self.schema)}")
            print(f"  ✗ Invalid result type: {type(self.schema)}\n")
            return

        # Check for fields key
        if 'fields' not in self.schema:
            self.errors.append("Schema missing 'fields' key")
            print("  ✗ Schema missing 'fields' key\n")
            return

        fields = self.schema['fields']
        print(f"  Fields returned: {len(fields)}")

        # Check for expected fields
        expected_fields = ['Id', 'Name', 'Email', 'Company', 'Status', 'Source', 'CreatedDate']
        field_names = [f['name'] for f in fields]

        missing_fields = [f for f in expected_fields if f not in field_names]
        if missing_fields:
            self.errors.append(f"Missing expected fields: {missing_fields}")
            print(f"  ✗ Missing fields: {missing_fields}")
        else:
            print(f"  ✓ All expected fields present")

        # Validate field structure
        if fields:
            sample_field = fields[0]
            required_keys = ['name', 'type']
            missing_keys = [k for k in required_keys if k not in sample_field]
            if missing_keys:
                self.errors.append(f"Field definition missing keys: {missing_keys}")
                print(f"  ✗ Field structure incomplete: missing {missing_keys}")
            else:
                print(f"  ✓ Field structure valid")

        # Check field count
        if len(fields) < 7:
            self.warnings.append(f"Expected at least 7 fields, got {len(fields)}")
            print(f"  ⚠ WARNING: Expected at least 7 fields\n")
        else:
            print(f"  ✓ Field count correct ({len(fields)} >= 7)\n")

    def _display_schema(self):
        """Display schema in a readable format"""
        if not self.schema or 'fields' not in self.schema:
            print("  No schema to display\n")
            return

        fields = self.schema['fields']
        print(f"  {self.target_object} Field Schema ({len(fields)} fields):\n")

        # Group fields by type for better readability
        field_types = {}
        for field in fields:
            field_type = field.get('type', 'unknown')
            if field_type not in field_types:
                field_types[field_type] = []
            field_types[field_type].append(field)

        # Display fields grouped by type
        for field_type, type_fields in sorted(field_types.items()):
            print(f"    {field_type.upper()} Fields ({len(type_fields)}):")
            for field in type_fields:
                nullable = "nullable" if field.get('nullable', True) else "required"
                label = field.get('label', field['name'])
                print(f"      - {field['name']:<20} ({label}, {nullable})")
            print()

    def _print_results(self):
        """Print formatted results"""
        print(f"{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

        if self.schema and 'fields' in self.schema:
            fields = self.schema['fields']
            print(f"Schema Summary:")
            print(f"  Object: {self.schema.get('name', self.target_object)}")
            print(f"  Total Fields: {len(fields)}")

            # Count by type
            type_counts = {}
            for field in fields:
                field_type = field.get('type', 'unknown')
                type_counts[field_type] = type_counts.get(field_type, 0) + 1

            print(f"  Field Types:")
            for field_type, count in sorted(type_counts.items()):
                print(f"    {field_type}: {count}")

            # Sample fields
            print(f"\n  Sample Fields (first 5):")
            for field in fields[:5]:
                print(f"    {field['name']}: {field['type']}")
        else:
            print("  No schema available")

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
            'schema': self.schema,
        }


def main():
    """Run the scenario"""
    scenario = Scenario3FieldDiscovery()
    report = scenario.run()

    # Print final status
    print(f"{'='*70}")
    print("FINAL STATUS")
    print(f"{'='*70}")
    print(f"Success: {'✓ PASS' if report['success'] else '✗ FAIL'}")
    print(f"Execution Time: {report['metrics'].get('execution_time', 0):.3f}s")
    print(f"Fields Discovered: {report['metrics'].get('fields_count', 0)}")

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
