#!/usr/bin/env python3
"""
Test the Self-Healing Agent System with Open-Meteo API.

This test will:
1. Call generate_driver_supervised() with Open-Meteo API
2. Monitor for diagnostic agent launches
3. Verify supervisor metadata in results
4. Check logs for self-healing behavior
"""

import sys
from pathlib import Path
from agent_tools import generate_driver_supervised

def test_self_healing_system():
    """Test complete self-healing system with Open-Meteo API."""

    print("=" * 80)
    print("Testing Self-Healing Agent System")
    print("=" * 80)
    print()
    print("API: Open-Meteo Weather API")
    print("URL: https://api.open-meteo.com/v1")
    print()
    print("Expected behavior:")
    print("- Supervisor orchestrates generation")
    print("- Diagnostic agent launches on failures")
    print("- Automatic retry with fixes applied")
    print("- Enhanced metadata in results")
    print()
    print("=" * 80)
    print()

    try:
        # Call supervised generation
        result = generate_driver_supervised(
            api_name="OpenMeteo",
            api_url="https://api.open-meteo.com/v1",
            output_dir=None,  # Use default
            max_supervisor_attempts=3,
            max_retries=3  # Fix-retry iterations per attempt
        )

        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()

        # Check success
        if result.get('success'):
            print("✅ Driver generation SUCCEEDED")
        else:
            print("❌ Driver generation FAILED")
            print(f"   Error: {result.get('error', 'Unknown')}")

        print()

        # Check supervisor metadata
        print("📊 Supervisor Metadata:")
        print(f"   - Supervisor attempts: {result.get('supervisor_attempts', 'N/A')}")
        print(f"   - Diagnostics run: {result.get('diagnostics_run', 0)}")
        print(f"   - Fixes applied: {len(result.get('fixes_applied', []))}")

        if result.get('fixes_applied'):
            print()
            print("🔧 Fixes Applied:")
            for i, fix in enumerate(result['fixes_applied'], 1):
                print(f"   {i}. Attempt {fix['attempt']}: {fix['strategy']}")
                print(f"      → {fix['description']}")

        print()

        # Check file generation
        if result.get('files_created'):
            print(f"📁 Files Created: {len(result['files_created'])}")
            for file_path in result['files_created']:
                print(f"   - {file_path}")

        print()

        # Check output path
        if result.get('output_path'):
            print(f"📂 Output Directory: {result['output_path']}")

        print()
        print("=" * 80)
        print()

        # Check for self-healing indicators
        self_healed = (
            result.get('diagnostics_run', 0) > 0 and
            result.get('success') == True
        )

        if self_healed:
            print("🎉 SELF-HEALING VERIFIED!")
            print("   System recovered from failure automatically")
        elif result.get('success') and result.get('supervisor_attempts', 1) == 1:
            print("✅ SUCCESS ON FIRST TRY")
            print("   No self-healing needed")
        else:
            print("⚠️  Generation failed even with self-healing")

        print()

        return result

    except Exception as e:
        print()
        print("=" * 80)
        print("💥 EXCEPTION")
        print("=" * 80)
        print()
        print(f"Error: {type(e).__name__}: {e}")
        print()
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = test_self_healing_system()

    # Exit code
    if result and result.get('success'):
        sys.exit(0)
    else:
        sys.exit(1)
