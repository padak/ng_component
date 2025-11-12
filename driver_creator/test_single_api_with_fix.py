"""
Test agent-based driver generation with fix-retry loop.

This tests the NEW fix-retry implementation where Tester Agent
analyzes failures and Generator Agent regenerates fixed code.
"""

from dotenv import load_dotenv
load_dotenv()

from agent_tools import generate_driver_with_agents

print("="*80)
print("🧪 Testing Agent-Based Generation with Fix-Retry Loop")
print("="*80)
print("API: JSONPlaceholder")
print("Max Retries: 2 (initial + 1 fix iteration)")
print("="*80)

result = generate_driver_with_agents(
    api_name="JSONPlaceholder",
    api_url="https://jsonplaceholder.typicode.com",
    max_retries=2  # Allow 1 fix iteration
)

print("\n\n")
print("="*80)
print("📊 FINAL RESULT")
print("="*80)
print(f"Success: {result.get('success', False)}")
print(f"Driver: {result.get('driver_name', 'N/A')}")
print(f"Output: {result.get('output_path', 'N/A')}")
print(f"Files: {len(result.get('files_created', []))}")
print(f"Iterations: {result.get('iterations', 0)}")
print(f"Execution Time: {result.get('execution_time', 0):.1f}s")

if result.get('test_results'):
    tests = result['test_results']
    print(f"\nTest Results:")
    print(f"  Passed: {tests.get('tests_passed', 0)}")
    print(f"  Failed: {tests.get('tests_failed', 0)}")
    print(f"  Success: {tests.get('success', False)}")

if result.get('learning_result'):
    learning = result['learning_result']
    print(f"\nLearnings Saved: {learning.get('learnings_saved', 0)}")

print("="*80)

if result.get('success'):
    print("✅ SUCCESS! Driver generated and tests passed!")
else:
    print("⚠️  Driver generated but tests incomplete")
    if result.get('test_results'):
        errors = result['test_results'].get('errors', [])
        if errors:
            print(f"\nRemaining Errors:")
            for err in errors:
                print(f"  - {err.get('test', 'unknown')}: {err.get('error', 'unknown')}")

print("="*80)
