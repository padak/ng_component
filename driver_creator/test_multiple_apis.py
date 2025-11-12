"""
Test agent-based driver generation with multiple APIs.

This script tests the new generate_driver_with_agents function
with 3 different public REST APIs to verify universal functionality.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()  # Load .env file

from agent_tools import generate_driver_with_agents
import json
from datetime import datetime

# Test APIs - all public, no auth required
TEST_APIS = [
    {
        "name": "JSONPlaceholder",
        "url": "https://jsonplaceholder.typicode.com",
        "description": "Simple fake REST API for testing",
        "expected_objects": ["posts", "comments", "albums", "photos", "todos", "users"]
    },
    {
        "name": "CoinGecko",
        "url": "https://api.coingecko.com/api/v3",
        "description": "Cryptocurrency prices and market data",
        "expected_objects": ["coins", "simple", "exchanges"]
    },
    {
        "name": "RestCountries",
        "url": "https://restcountries.com/v3.1",
        "description": "Country data (population, languages, etc)",
        "expected_objects": ["all", "name", "alpha", "currency", "region"]
    }
]


def test_single_api(api_config: dict, max_retries: int = 1) -> dict:
    """
    Test driver generation for a single API.

    Args:
        api_config: API configuration dict
        max_retries: Max test-fix iterations

    Returns:
        Result dict with success, files_created, test_results, etc.
    """
    print(f"\n{'='*80}")
    print(f"🚀 Testing {api_config['name']}")
    print(f"   URL: {api_config['url']}")
    print(f"   Description: {api_config['description']}")
    print('='*80)

    result = generate_driver_with_agents(
        api_name=api_config['name'],
        api_url=api_config['url'],
        max_retries=max_retries
    )

    # Add test metadata
    result['test_metadata'] = {
        'api_name': api_config['name'],
        'api_url': api_config['url'],
        'expected_objects': api_config.get('expected_objects', []),
        'timestamp': datetime.now().isoformat()
    }

    return result


def print_summary(results: list):
    """Print summary of all test results"""
    print("\n\n")
    print("="*80)
    print("📊 TEST SUMMARY")
    print("="*80)

    total = len(results)
    successful = sum(1 for r in results if r.get('success', False))
    failed = total - successful

    print(f"\nTotal APIs Tested: {total}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {successful/total*100:.1f}%")

    print("\n" + "-"*80)
    print("Individual Results:")
    print("-"*80)

    for i, result in enumerate(results, 1):
        metadata = result.get('test_metadata', {})
        api_name = metadata.get('api_name', f'API {i}')
        success = result.get('success', False)

        status_icon = "✅" if success else "❌"
        print(f"\n{status_icon} {i}. {api_name}")
        print(f"   URL: {metadata.get('api_url', 'N/A')}")

        if success:
            files = result.get('files_created', [])
            print(f"   Files Generated: {len(files)}")

            if result.get('test_results'):
                tests = result['test_results']
                print(f"   Tests: {tests.get('tests_passed', 0)} passed, {tests.get('tests_failed', 0)} failed")

            print(f"   Execution Time: {result.get('execution_time', 0):.1f}s")
            print(f"   Output: {result.get('output_path', 'N/A')}")
        else:
            print(f"   Error: {result.get('error', 'Unknown')}")
            print(f"   Message: {result.get('message', 'N/A')}")

    print("\n" + "="*80)

    # Save results to JSON
    results_file = Path("test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Full results saved to: {results_file}")
    print("="*80)


def main():
    """Main test function"""
    print("🧪 MULTI-API DRIVER GENERATION TEST")
    print("="*80)
    print(f"Testing {len(TEST_APIS)} different APIs with agent-based generation")
    print("This will take several minutes (3-5 min per API)")
    print("="*80)

    # Check required environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ERROR: ANTHROPIC_API_KEY not set in .env")
        return

    if not os.getenv("E2B_API_KEY"):
        print("⚠️  WARNING: E2B_API_KEY not set - E2B testing will be skipped")

    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not set - mem0 learning will fail")

    print("\nStarting tests...\n")

    results = []

    # Test each API
    for i, api_config in enumerate(TEST_APIS, 1):
        print(f"\n[{i}/{len(TEST_APIS)}] Testing {api_config['name']}...")

        try:
            result = test_single_api(api_config, max_retries=1)
            results.append(result)
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user (Ctrl+C)")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error testing {api_config['name']}: {e}")
            results.append({
                'success': False,
                'error': 'UNEXPECTED_ERROR',
                'message': str(e),
                'test_metadata': {
                    'api_name': api_config['name'],
                    'api_url': api_config['url']
                }
            })

    # Print summary
    if results:
        print_summary(results)
    else:
        print("\n❌ No tests completed")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
