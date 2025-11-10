"""
Example Usage of Agent Executor

This script demonstrates how to use the AgentExecutor to execute
Salesforce operations in an E2B sandbox.

Run this after:
1. Setting up .env file with E2B_API_KEY
2. Starting the mock API: python mock_api/main.py
3. Running tests: python test_executor.py

Usage:
    python example_usage.py
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the executor
from agent_executor import AgentExecutor


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(result: dict):
    """Pretty print execution result."""
    if result['success']:
        print(f"\n✓ SUCCESS: {result['description']}")

        # Show data summary
        if result['data']:
            data = result['data']

            # Count of records
            if 'count' in data:
                print(f"  Records: {data['count']}")

            # Status breakdown if available
            if 'status_breakdown' in data:
                print(f"\n  Status Breakdown:")
                for status, count in data['status_breakdown'].items():
                    print(f"    - {status}: {count}")

            # Show sample leads
            if 'leads' in data and data['leads']:
                print(f"\n  Sample Leads:")
                for i, lead in enumerate(data['leads'][:3], 1):
                    name = lead.get('Name', 'N/A')
                    company = lead.get('Company', 'N/A')
                    email = lead.get('Email', 'N/A')
                    status = lead.get('Status', 'N/A')
                    print(f"    {i}. {name}")
                    print(f"       Company: {company}")
                    print(f"       Email: {email}")
                    print(f"       Status: {status}")

                if len(data['leads']) > 3:
                    print(f"    ... and {len(data['leads']) - 3} more")

            # Show campaign info if available
            if 'campaign' in data:
                campaign = data['campaign']
                print(f"\n  Campaign Info:")
                print(f"    Name: {campaign.get('Name', 'N/A')}")
                print(f"    Status: {campaign.get('Status', 'N/A')}")
                print(f"    Members: {data.get('member_count', 0)}")
                print(f"    Leads: {data.get('lead_count', 0)}")

        # Show partial output
        if result['output']:
            print(f"\n  Output Preview:")
            lines = result['output'].split('\n')
            for line in lines[:5]:
                print(f"    {line}")
            if len(lines) > 5:
                print(f"    ... ({len(lines) - 5} more lines)")

    else:
        print(f"\n✗ FAILED: {result['description']}")
        print(f"  Error: {result['error']}")


def example_1_basic_usage():
    """Example 1: Basic usage - get all leads."""
    print_section("Example 1: Basic Usage - Get All Leads")

    try:
        # Create executor
        print("Creating executor...")
        executor = AgentExecutor()
        print(f"✓ Executor ready (Sandbox: {executor.sandbox.id})")

        # Execute a simple request
        print("\nExecuting request: 'Get all leads'")
        result = executor.execute("Get all leads")

        # Print results
        print_result(result)

        # Clean up
        print("\nClosing executor...")
        executor.close()
        print("✓ Done")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


def example_2_recent_leads():
    """Example 2: Get recent leads with date filtering."""
    print_section("Example 2: Get Recent Leads (Last 30 Days)")

    try:
        with AgentExecutor() as executor:
            print(f"Executor ready (Sandbox: {executor.sandbox.id})")

            # Get leads from last 30 days
            print("\nExecuting request: 'Get all leads from last 30 days'")
            result = executor.execute("Get all leads from last 30 days")
            print_result(result)

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


def example_3_filtered_leads():
    """Example 3: Get leads filtered by status."""
    print_section("Example 3: Get Leads by Status")

    try:
        with AgentExecutor() as executor:
            print(f"Executor ready (Sandbox: {executor.sandbox.id})")

            # Test different status filters
            statuses = ['New', 'Qualified', 'Working']

            for status in statuses:
                print(f"\n--- Getting leads with status: {status} ---")
                result = executor.execute(f"Get leads with status {status}")

                if result['success'] and result['data']:
                    count = result['data'].get('count', 0)
                    print(f"✓ Found {count} {status} leads")
                else:
                    print(f"✗ Failed to get {status} leads")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


def example_4_campaign_leads():
    """Example 4: Get campaign with associated leads."""
    print_section("Example 4: Get Campaign with Leads")

    try:
        with AgentExecutor() as executor:
            print(f"Executor ready (Sandbox: {executor.sandbox.id})")

            # Get campaign with leads
            print("\nExecuting request: 'Get leads for Summer Campaign'")
            result = executor.execute("Get leads for Summer Campaign")
            print_result(result)

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


def example_5_multiple_requests():
    """Example 5: Execute multiple requests with same executor."""
    print_section("Example 5: Multiple Requests (Reusing Sandbox)")

    try:
        executor = AgentExecutor()
        print(f"Executor ready (Sandbox: {executor.sandbox.id})")

        # List of requests to execute
        requests = [
            "Get all leads from last 30 days",
            "Get leads with status New",
            "Get leads for Summer Campaign",
        ]

        print(f"\nExecuting {len(requests)} requests using same sandbox...")

        for i, request in enumerate(requests, 1):
            print(f"\n--- Request {i}/{len(requests)}: {request} ---")

            result = executor.execute(request)

            if result['success']:
                count = result['data'].get('count', 0) if result['data'] else 0
                print(f"✓ Success: {count} records")
            else:
                print(f"✗ Failed: {result['error']}")

        # Clean up
        print("\nClosing executor...")
        executor.close()
        print("✓ Done - sandbox reused for all requests")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


def example_6_discovery():
    """Example 6: Run discovery to see available objects and schemas."""
    print_section("Example 6: Discovery - Available Objects and Schemas")

    try:
        with AgentExecutor() as executor:
            print(f"Executor ready (Sandbox: {executor.sandbox.id})")

            # Run discovery
            print("\nRunning discovery...")
            discovery = executor.run_discovery()

            # Show available objects
            print(f"\n✓ Found {len(discovery['objects'])} objects:")
            for i, obj in enumerate(discovery['objects'], 1):
                print(f"  {i}. {obj}")

            # Show schemas
            print(f"\nObject Schemas:")
            for obj_name, schema in discovery['schemas'].items():
                fields = schema.get('fields', [])
                print(f"\n  {obj_name} ({len(fields)} fields):")

                # Show first 5 fields
                for field in fields[:5]:
                    name = field.get('name', 'unknown')
                    field_type = field.get('type', 'unknown')
                    label = field.get('label', name)
                    print(f"    - {name} ({field_type}): {label}")

                if len(fields) > 5:
                    print(f"    ... and {len(fields) - 5} more fields")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


def example_7_custom_script():
    """Example 7: Execute custom script directly."""
    print_section("Example 7: Execute Custom Script")

    try:
        with AgentExecutor() as executor:
            print(f"Executor ready (Sandbox: {executor.sandbox.id})")

            # Create a custom script
            from script_templates import ScriptTemplates

            print("\nGenerating custom script...")
            script = ScriptTemplates.custom_query(
                api_url=executor.sandbox_sf_api_url,
                api_key=executor.sf_api_key,
                soql_query="SELECT Id, Name, Email, Status FROM Lead WHERE Email != null LIMIT 5"
            )

            print("Executing custom script...")
            result = executor.execute_script(
                script,
                description="Get first 5 leads with email addresses"
            )

            print_result({
                'success': result['success'],
                'description': "Custom SOQL Query",
                'output': result['output'],
                'error': result['error'],
                'data': result['data']
            })

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


def example_8_error_handling():
    """Example 8: Error handling examples."""
    print_section("Example 8: Error Handling")

    try:
        with AgentExecutor() as executor:
            print(f"Executor ready (Sandbox: {executor.sandbox.id})")

            # Try a query that might fail
            print("\n1. Testing with invalid object name...")
            from script_templates import ScriptTemplates

            script = ScriptTemplates.custom_query(
                api_url=executor.sandbox_sf_api_url,
                api_key=executor.sf_api_key,
                soql_query="SELECT Id FROM NonExistentObject"
            )

            result = executor.execute_script(script, "Query invalid object")

            if result['success']:
                print("  ✓ Query succeeded (unexpected)")
            else:
                print(f"  ✓ Query failed as expected: {result['error'][:100]}...")

            # Try with valid query
            print("\n2. Testing with valid query...")
            script = ScriptTemplates.get_all_leads(
                api_url=executor.sandbox_sf_api_url,
                api_key=executor.sf_api_key,
                limit=5
            )

            result = executor.execute_script(script, "Get 5 leads")

            if result['success']:
                count = result['data'].get('count', 0) if result['data'] else 0
                print(f"  ✓ Query succeeded: {count} records")
            else:
                print(f"  ✗ Query failed: {result['error']}")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("  AGENT EXECUTOR - EXAMPLE USAGE")
    print("=" * 80)

    # Check prerequisites
    if not os.getenv('E2B_API_KEY'):
        print("\n✗ ERROR: E2B_API_KEY not set in environment")
        print("  Please set it in .env file")
        return 1

    print("\nThis will demonstrate various ways to use the AgentExecutor.")
    print("Each example creates a sandbox, executes operations, and cleans up.")
    print("\nPress Ctrl+C at any time to stop.")

    # List of examples
    examples = [
        ("Basic Usage", example_1_basic_usage),
        ("Recent Leads", example_2_recent_leads),
        ("Filtered Leads", example_3_filtered_leads),
        ("Campaign Leads", example_4_campaign_leads),
        ("Multiple Requests", example_5_multiple_requests),
        ("Discovery", example_6_discovery),
        ("Custom Script", example_7_custom_script),
        ("Error Handling", example_8_error_handling),
    ]

    try:
        # Run each example
        for i, (name, func) in enumerate(examples, 1):
            print(f"\n\n{'#' * 80}")
            print(f"  Running Example {i}/{len(examples)}: {name}")
            print(f"{'#' * 80}")

            try:
                func()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"\n✗ Example {name} failed: {str(e)}")
                import traceback
                traceback.print_exc()

            # Pause between examples
            if i < len(examples):
                print("\n" + "-" * 80)
                input("Press Enter to continue to next example...")

        # Summary
        print("\n\n" + "=" * 80)
        print("  ALL EXAMPLES COMPLETED")
        print("=" * 80)
        print("\n✓ Successfully demonstrated all AgentExecutor capabilities")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Examples interrupted by user")
        return 1


if __name__ == '__main__':
    sys.exit(main())
