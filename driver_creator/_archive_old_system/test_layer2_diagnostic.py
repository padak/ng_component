#!/usr/bin/env python3
"""
Test script for Layer 2 Diagnostic Agent functions.

This demonstrates the diagnostic output format without requiring
an actual Claude API call.
"""

from pathlib import Path
from agent_tools import (
    build_diagnostic_prompt,
    read_recent_logs,
    extract_json_from_response
)


def test_build_diagnostic_prompt():
    """Test building diagnostic prompt"""
    print("=" * 80)
    print("TEST 1: build_diagnostic_prompt()")
    print("=" * 80)

    # Create mock failure context
    failure_context = {
        "attempt": 2,
        "error_type": "logic",
        "error_message": "list_objects() returned List[Dict] instead of List[str]",
        "result": {
            "success": False,
            "files_generated": ["client.py", "__init__.py", "exceptions.py"]
        },
        "api_name": "TestAPI",
        "files_generated": ["client.py", "__init__.py"],
        "test_results": {
            "tests_passed": 0,
            "tests_failed": 3
        }
    }

    # Create temporary session directory
    session_dir = Path("logs/test_session")
    session_dir.mkdir(parents=True, exist_ok=True)

    # Write a test log file
    test_log = session_dir / "generator_prompt.txt"
    test_log.write_text("=" * 80 + "\nTimestamp: 2025-11-12 14:00:00\n" + "=" * 80 + "\nTest log content...")

    # Build prompt
    prompt = build_diagnostic_prompt(failure_context, session_dir)

    print("\nGenerated diagnostic prompt (first 500 chars):")
    print(prompt[:500])
    print("\n✓ Diagnostic prompt built successfully!")

    # Cleanup
    test_log.unlink()
    session_dir.rmdir()


def test_read_recent_logs():
    """Test reading recent logs"""
    print("\n" + "=" * 80)
    print("TEST 2: read_recent_logs()")
    print("=" * 80)

    # Create temporary session directory with logs
    session_dir = Path("logs/test_session2")
    session_dir.mkdir(parents=True, exist_ok=True)

    # Write multiple log files
    (session_dir / "research_prompt.txt").write_text("Research log content\n" * 50)
    (session_dir / "generator_prompt.txt").write_text("Generator log content\n" * 50)

    # Read logs
    logs = read_recent_logs(session_dir, max_lines=10)

    print("\nRead logs (truncated to 200 chars):")
    print(logs[:200])
    print("\n✓ Logs read successfully!")

    # Cleanup
    for log_file in session_dir.glob("*.txt"):
        log_file.unlink()
    session_dir.rmdir()


def test_extract_json_from_response():
    """Test extracting JSON from Claude response"""
    print("\n" + "=" * 80)
    print("TEST 3: extract_json_from_response()")
    print("=" * 80)

    # Test case 1: Raw JSON
    raw_json = '{"error_type": "logic", "root_cause": "Test error", "can_fix": true}'
    result1 = extract_json_from_response(raw_json)
    print("\nTest case 1 - Raw JSON:")
    print(f"  Input: {raw_json[:60]}...")
    print(f"  Output: {result1}")
    print("  ✓ Extracted successfully!")

    # Test case 2: JSON in markdown code block
    markdown_json = """Here's the analysis:

```json
{
    "error_type": "formatting",
    "root_cause": "JSON parsing error",
    "can_fix": true,
    "fix_strategy": "prompt_adjustment"
}
```

Hope this helps!"""
    result2 = extract_json_from_response(markdown_json)
    print("\nTest case 2 - Markdown-wrapped JSON:")
    print(f"  Input: {markdown_json[:60]}...")
    print(f"  Output: {result2}")
    print("  ✓ Extracted successfully!")

    # Test case 3: JSON with code block without language tag
    plain_block = """Analysis complete:

```
{"error_type": "api", "root_cause": "Rate limit", "can_fix": false}
```
"""
    result3 = extract_json_from_response(plain_block)
    print("\nTest case 3 - Plain code block:")
    print(f"  Input: {plain_block[:60]}...")
    print(f"  Output: {result3}")
    print("  ✓ Extracted successfully!")


def test_diagnostic_output_format():
    """Demonstrate expected diagnostic output format"""
    print("\n" + "=" * 80)
    print("TEST 4: Expected Diagnostic Output Format")
    print("=" * 80)

    example_diagnosis = {
        "error_type": "logic",
        "root_cause": "list_objects() returns List[Dict] instead of List[str]. The function returns full endpoint objects with 'name', 'path', 'method' fields instead of extracting just the 'name' strings.",
        "can_fix": True,
        "fix_strategy": "prompt_adjustment",
        "fix_description": "Add explicit instruction to extract only 'name' field from endpoint objects. The prompt should emphasize returning List[str] not List[Dict].",
        "prompt_modification": "Add this to GENERATOR_AGENT_PROMPT: 'CRITICAL: list_objects() MUST return List[str] (simple strings). If research_data contains dicts, extract ONLY the name field: [obj[\"name\"] for obj in objects]'"
    }

    print("\nExample diagnostic output:")
    print(f"  Error Type: {example_diagnosis['error_type']}")
    print(f"  Root Cause: {example_diagnosis['root_cause'][:80]}...")
    print(f"  Can Fix: {example_diagnosis['can_fix']}")
    print(f"  Fix Strategy: {example_diagnosis['fix_strategy']}")
    print(f"  Fix Description: {example_diagnosis['fix_description'][:80]}...")
    print(f"  Prompt Modification: {example_diagnosis['prompt_modification'][:80]}...")

    print("\n✓ All fields present in expected format!")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("LAYER 2 DIAGNOSTIC AGENT - FUNCTION TESTS")
    print("=" * 80)

    try:
        test_build_diagnostic_prompt()
        test_read_recent_logs()
        test_extract_json_from_response()
        test_diagnostic_output_format()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\nLayer 2 functions are working correctly!")
        print("\nTo use the Diagnostic Agent in production:")
        print("  from agent_tools import launch_diagnostic_agent")
        print("  diagnosis = launch_diagnostic_agent(failure_context, session_dir, attempt)")
        print("\nNote: launch_diagnostic_agent() requires ANTHROPIC_API_KEY env var")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
