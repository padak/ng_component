#!/usr/bin/env python3
"""
Test Edit-based fix-retry loop with Open-Meteo driver.
"""

import sys
from agent_tools import generate_driver_with_agents

def main():
    print("=" * 80)
    print("Testing Edit-based Fix-Retry Loop")
    print("=" * 80)
    print()

    print("Generating Open-Meteo driver...")
    print("This should:")
    print("1. Generate driver with list_objects() bug")
    print("2. Detect error in tests")
    print("3. Use Edit tool to fix the bug")
    print("4. Retry tests and pass")
    print()

    result = generate_driver_with_agents(
        api_name="Open-Meteo",
        api_url="https://api.open-meteo.com/v1",
        max_retries=3  # Allow 3 retry attempts
    )

    print()
    print("=" * 80)
    print("RESULT:")
    print("=" * 80)
    print(f"Success: {result['success']}")
    print(f"Driver path: {result['output_path']}")
    print(f"Files created: {len(result['files_created'])}")
    print(f"Test results: {result.get('test_results', {})}")
    print()

    if result['success']:
        print("✅ Driver generation PASSED - fix-retry loop worked!")
        return 0
    else:
        print("❌ Driver generation FAILED - fix-retry loop needs debugging")
        return 1

if __name__ == "__main__":
    sys.exit(main())
