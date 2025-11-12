"""
Test agent-based driver generation.

This script tests the new generate_driver_with_agents function
with a simple public API.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file

from agent_tools import generate_driver_with_agents

def test_jsonplaceholder_driver():
    """Test driver generation for JSONPlaceholder API"""
    print("🧪 Testing Agent-Based Driver Generation")
    print("=" * 80)
    print("API: JSONPlaceholder (simple REST API)")
    print("=" * 80)

    result = generate_driver_with_agents(
        api_name="JSONPlaceholder",
        api_url="https://jsonplaceholder.typicode.com",
        max_retries=2
    )

    print("\n\n📊 FINAL RESULT:")
    print("=" * 80)
    print(f"Success: {result.get('success', False)}")

    if 'driver_name' in result:
        print(f"Driver Name: {result['driver_name']}")
        print(f"Output Path: {result['output_path']}")
        print(f"Files Created: {len(result.get('files_created', []))}")
        for file in result.get('files_created', []):
            print(f"  - {file}")
        print(f"Iterations: {result.get('iterations', 0)}")

    if 'error' in result:
        print(f"Error: {result['error']}")
        print(f"Message: {result['message']}")

    print(f"Execution Time: {result.get('execution_time', 0):.1f}s")

    if result['test_results']:
        tests = result['test_results']
        print(f"\nTest Results:")
        print(f"  - Passed: {tests.get('tests_passed', 0)}")
        print(f"  - Failed: {tests.get('tests_failed', 0)}")

    if result.get('learning_result'):
        learning = result['learning_result']
        print(f"\nLearnings Saved: {learning.get('learnings_saved', 0)}")

    print("=" * 80)

    return result['success']


if __name__ == "__main__":
    success = test_jsonplaceholder_driver()
    exit(0 if success else 1)
