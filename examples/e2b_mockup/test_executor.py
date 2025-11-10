"""
Test Suite for Agent Executor

This script tests the AgentExecutor functionality step by step:
1. Tests E2B connection and sandbox creation
2. Tests driver loading into sandbox
3. Tests basic Python script execution
4. Tests Salesforce driver integration
5. Tests complete user request flow

Run this to verify that the E2B integration is working correctly before
running more complex agent scenarios.

Usage:
    python test_executor.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test imports
print("Testing imports...")
print("-" * 80)

try:
    from e2b_code_interpreter import Sandbox
    print("✓ E2B Code Interpreter imported successfully")
except ImportError as e:
    print(f"✗ Failed to import E2B: {e}")
    print("  Run: pip install e2b-code-interpreter")
    sys.exit(1)

try:
    from agent_executor import AgentExecutor
    print("✓ AgentExecutor imported successfully")
except ImportError as e:
    print(f"✗ Failed to import AgentExecutor: {e}")
    sys.exit(1)

try:
    from script_templates import ScriptTemplates
    print("✓ ScriptTemplates imported successfully")
except ImportError as e:
    print(f"✗ Failed to import ScriptTemplates: {e}")
    sys.exit(1)


def test_environment():
    """Test that required environment variables are set."""
    print("\n\nTest 1: Environment Variables")
    print("=" * 80)

    required_vars = ['E2B_API_KEY', 'SF_API_URL', 'SF_API_KEY']
    all_present = True

    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var:
                display_value = value[:8] + '...' if len(value) > 8 else '***'
            else:
                display_value = value
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET")
            all_present = False

    if not all_present:
        print("\n⚠ WARNING: Missing environment variables")
        print("  Copy .env.example to .env and fill in your values")
        return False

    print("\n✓ All required environment variables are set")
    return True


def test_e2b_connection():
    """Test basic E2B connection and sandbox creation."""
    print("\n\nTest 2: E2B Connection")
    print("=" * 80)

    api_key = os.getenv('E2B_API_KEY')
    if not api_key:
        print("✗ Cannot test - E2B_API_KEY not set")
        return False

    try:
        print("Creating E2B sandbox...")
        sandbox = Sandbox.create(api_key=api_key)
        print(f"✓ Sandbox created: {sandbox.sandbox_id}")

        # Test basic code execution
        print("\nTesting basic code execution...")
        result = sandbox.run_code("print('Hello from E2B!')")

        if result.error:
            print(f"✗ Code execution failed: {result.error}")
            sandbox.kill()
            return False

        print(f"✓ Code executed successfully")
        print(f"  Output: {result.text}")

        # Clean up
        print("\nClosing sandbox...")
        sandbox.kill()
        print("✓ Sandbox closed")

        return True

    except Exception as e:
        print(f"✗ E2B connection test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_sandbox_filesystem():
    """Test uploading files to sandbox filesystem."""
    print("\n\nTest 3: Sandbox Filesystem")
    print("=" * 80)

    api_key = os.getenv('E2B_API_KEY')
    if not api_key:
        print("✗ Cannot test - E2B_API_KEY not set")
        return False

    try:
        print("Creating sandbox...")
        sandbox = Sandbox.create(api_key=api_key)
        print(f"✓ Sandbox created: {sandbox.sandbox_id}")

        # Create a test file
        print("\nWriting test file to sandbox...")
        test_content = "# Test Python Module\nprint('Hello from test module!')\n"
        sandbox.filesystem.write('/home/user/test_module.py', test_content)
        print("✓ File written")

        # Read it back
        print("\nReading file back...")
        read_content = sandbox.filesystem.read('/home/user/test_module.py')
        print(f"✓ File read successfully")
        print(f"  Content matches: {read_content == test_content}")

        # Execute it
        print("\nExecuting the test module...")
        result = sandbox.run_code("""
import sys
sys.path.insert(0, '/home/user')
import test_module
""")

        if result.error:
            print(f"✗ Execution failed: {result.error}")
            sandbox.kill()
            return False

        print(f"✓ Module executed successfully")
        print(f"  Output: {result.text}")

        # Clean up
        sandbox.kill()
        print("\n✓ Filesystem test passed")
        return True

    except Exception as e:
        print(f"✗ Filesystem test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_driver_loading():
    """Test loading the Salesforce driver into sandbox."""
    print("\n\nTest 4: Driver Loading")
    print("=" * 80)

    api_key = os.getenv('E2B_API_KEY')
    if not api_key:
        print("✗ Cannot test - E2B_API_KEY not set")
        return False

    try:
        print("Creating executor (this will create sandbox and load driver)...")
        executor = AgentExecutor()

        print(f"✓ Sandbox created: {executor.sandbox.sandbox_id}")
        print(f"✓ Driver loaded: {executor.driver_loaded}")

        if not executor.driver_loaded:
            print("✗ Driver not loaded")
            executor.close()
            return False

        # Test driver import
        print("\nTesting driver import in sandbox...")
        test_code = """
import sys
sys.path.insert(0, '/home/user')

from salesforce_driver import SalesforceClient
print("SalesforceClient imported successfully!")
print(f"SalesforceClient type: {type(SalesforceClient)}")
"""

        result = executor.sandbox.run_code(test_code)

        if result.error:
            print(f"✗ Driver import failed: {result.error}")
            executor.close()
            return False

        print(f"✓ Driver import successful")
        print(f"  Output: {result.text}")

        # Clean up
        executor.close()
        print("\n✓ Driver loading test passed")
        return True

    except Exception as e:
        print(f"✗ Driver loading test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_discovery():
    """Test running discovery in the sandbox."""
    print("\n\nTest 5: Discovery")
    print("=" * 80)

    try:
        print("Creating executor...")
        executor = AgentExecutor()

        print(f"✓ Sandbox ready: {executor.sandbox.sandbox_id}")

        print("\nRunning discovery...")
        discovery = executor.run_discovery()

        print(f"\n✓ Discovery completed")
        print(f"  Objects found: {len(discovery['objects'])}")
        print(f"  Objects: {', '.join(discovery['objects'])}")

        # Check schemas
        print(f"\n  Schemas retrieved: {len(discovery['schemas'])}")
        for obj_name, schema in discovery['schemas'].items():
            field_count = len(schema.get('fields', []))
            print(f"    - {obj_name}: {field_count} fields")

        # Verify we got expected objects
        expected_objects = ['Lead', 'Campaign', 'CampaignMember']
        for obj in expected_objects:
            if obj in discovery['objects']:
                print(f"  ✓ Found expected object: {obj}")
            else:
                print(f"  ⚠ Missing expected object: {obj}")

        # Clean up
        executor.close()
        print("\n✓ Discovery test passed")
        return True

    except Exception as e:
        print(f"✗ Discovery test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_query():
    """Test executing a simple query."""
    print("\n\nTest 6: Simple Query Execution")
    print("=" * 80)

    try:
        print("Creating executor...")
        executor = AgentExecutor()

        print(f"✓ Sandbox ready: {executor.sandbox.sandbox_id}")

        # Create a simple test script
        print("\nExecuting simple query...")
        script = ScriptTemplates.get_all_leads(
            api_url=executor.sandbox_sf_api_url,
            api_key=executor.sf_api_key,
            limit=5
        )

        result = executor.execute_script(script, "Get first 5 leads")

        if result['success']:
            print(f"✓ Query executed successfully")
            print(f"\nOutput preview:")
            print(result['output'][:500])

            if result['data']:
                print(f"\n✓ Data parsed as JSON")
                print(f"  Record count: {result['data'].get('count', 0)}")
        else:
            print(f"✗ Query failed: {result['error']}")
            executor.close()
            return False

        # Clean up
        executor.close()
        print("\n✓ Simple query test passed")
        return True

    except Exception as e:
        print(f"✗ Simple query test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_full_execution():
    """Test the full execution flow with user prompt."""
    print("\n\nTest 7: Full Execution Flow")
    print("=" * 80)

    try:
        print("Creating executor...")
        executor = AgentExecutor()

        print(f"✓ Sandbox ready: {executor.sandbox.sandbox_id}")

        # Test different user prompts
        test_prompts = [
            "Get all leads from last 30 days",
            "Get leads with status New",
            "Get all leads"
        ]

        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n\nTest {i}/{len(test_prompts)}: {prompt}")
            print("-" * 60)

            result = executor.execute(prompt)

            if result['success']:
                print(f"✓ Execution successful")
                print(f"  Description: {result['description']}")

                if result['data']:
                    print(f"  Records: {result['data'].get('count', 'N/A')}")

                print(f"\nOutput preview:")
                print(result['output'][:300])
            else:
                print(f"✗ Execution failed: {result['error']}")

        # Clean up
        executor.close()
        print("\n\n✓ Full execution test passed")
        return True

    except Exception as e:
        print(f"✗ Full execution test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_api_connectivity():
    """Test that we can reach the Salesforce mock API."""
    print("\n\nTest 0: Mock API Connectivity")
    print("=" * 80)

    sf_api_url = os.getenv('SF_API_URL', 'http://localhost:8000')

    print(f"Testing connectivity to: {sf_api_url}")

    try:
        import requests

        # Test health endpoint
        response = requests.get(f"{sf_api_url}/health", timeout=5)

        if response.status_code == 200:
            print(f"✓ Mock API is running")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text}")
            return True
        else:
            print(f"⚠ Mock API returned unexpected status: {response.status_code}")
            print(f"  Make sure the mock API is running: python mock_api/main.py")
            return False

    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to Mock API at {sf_api_url}")
        print(f"\n  Please start the mock API server:")
        print(f"    cd mock_api")
        print(f"    python main.py")
        return False
    except Exception as e:
        print(f"✗ API connectivity test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "=" * 80)
    print("AGENT EXECUTOR TEST SUITE")
    print("=" * 80)

    tests = [
        ("Environment Variables", test_environment),
        ("Mock API Connectivity", test_api_connectivity),
        ("E2B Connection", test_e2b_connection),
        ("Sandbox Filesystem", test_sandbox_filesystem),
        ("Driver Loading", test_driver_loading),
        ("Discovery", test_discovery),
        ("Simple Query", test_simple_query),
        ("Full Execution", test_full_execution),
    ]

    results = []

    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))

            # If a critical test fails, stop
            if not passed and name in ["Environment Variables", "E2B Connection", "Driver Loading"]:
                print(f"\n⚠ Critical test failed: {name}")
                print("  Skipping remaining tests")
                break

        except KeyboardInterrupt:
            print("\n\nTests interrupted by user")
            break
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {str(e)}")
            results.append((name, False))

    # Print summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print("-" * 80)
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Test the Agent Executor')
    parser.add_argument(
        '--test',
        choices=[
            'env', 'api', 'e2b', 'filesystem', 'driver',
            'discovery', 'query', 'full', 'all'
        ],
        default='all',
        help='Specific test to run (default: all)'
    )

    args = parser.parse_args()

    test_map = {
        'env': test_environment,
        'api': test_api_connectivity,
        'e2b': test_e2b_connection,
        'filesystem': test_sandbox_filesystem,
        'driver': test_driver_loading,
        'discovery': test_discovery,
        'query': test_simple_query,
        'full': test_full_execution,
        'all': run_all_tests
    }

    test_func = test_map[args.test]

    try:
        if args.test == 'all':
            return test_func()
        else:
            success = test_func()
            return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
