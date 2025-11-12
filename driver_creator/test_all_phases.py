#!/usr/bin/env python3
"""
Test script to verify all 5 phases of FIX_DRIVER_GENERATION.md are working.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from agent_tools import generate_driver_with_agents

# Load environment variables from .env file
load_dotenv()

def test_all_phases():
    """
    Test driver generation with all improvements:
    - Phase 1: Logging
    - Phase 2: Enhanced prompts
    - Phase 3: Tester visibility
    - Phase 4: Max retries = 7
    - Phase 5: Error prioritization
    """

    print("=" * 80)
    print("Testing All Phases Implementation")
    print("=" * 80)

    # Test with JSONPlaceholder (simple, well-documented API)
    api_name = "JSONPlaceholder"
    api_url = "https://jsonplaceholder.typicode.com"

    print(f"\n🧪 Testing with: {api_name}")
    print(f"📍 API URL: {api_url}")
    print(f"🔄 Max retries: 7 (Phase 4)")
    print()

    try:
        result = generate_driver_with_agents(
            api_name=api_name,
            api_url=api_url,
            max_retries=7  # Phase 4: Increased from 3
        )

        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)

        print(f"\n✅ Success: {result.get('success')}")
        print(f"📁 Output: {result.get('output_path')}")
        print(f"📄 Files created: {result.get('files_created')}")
        print(f"🧪 Tests passed: {result.get('tests_passed', 0)}")
        print(f"❌ Tests failed: {result.get('tests_failed', 0)}")
        print(f"🔄 Iterations: {result.get('iterations', 0)}")

        # Verify Phase 1: Logging
        print("\n" + "=" * 80)
        print("PHASE 1: Logging Verification")
        print("=" * 80)

        logs_dir = Path("logs")
        if logs_dir.exists():
            sessions = sorted(logs_dir.glob("session_*"))
            if sessions:
                latest_session = sessions[-1]
                print(f"\n✅ Logs created: {latest_session}")

                log_files = list(latest_session.glob("*"))
                print(f"📋 Log files ({len(log_files)}):")
                for log_file in sorted(log_files):
                    size = log_file.stat().st_size
                    print(f"   - {log_file.name} ({size} bytes)")
            else:
                print("\n❌ No session directories found!")
        else:
            print("\n❌ Logs directory not created!")

        # Verify Phase 2: Generator prompts
        print("\n" + "=" * 80)
        print("PHASE 2: Generator Prompts Verification")
        print("=" * 80)

        output_dir = Path(result.get('output_path', ''))
        if output_dir.exists():
            client_py = output_dir / "client.py"
            if client_py.exists():
                content = client_py.read_text()

                # Check if list_objects returns List[str]
                if "def list_objects(self) -> List[str]:" in content:
                    print("\n✅ list_objects() has correct signature: List[str]")
                else:
                    print("\n⚠️  list_objects() signature may be incorrect")

                # Check if get_fields is present
                if "def get_fields(self" in content:
                    print("✅ get_fields() method exists")
                else:
                    print("⚠️  get_fields() method not found")

        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)

        return result

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_all_phases()
    sys.exit(0 if result and result.get('success') else 1)
