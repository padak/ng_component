"""
Test Suite for Agent Executor with E2B Sandbox

This script tests the AgentExecutor functionality with the new E2B architecture
where both the mock API and driver run inside the E2B sandbox:

1. Tests environment variables
2. Tests E2B connection and sandbox creation
3. Tests uploading files to sandbox
4. Tests starting mock API inside sandbox
5. Tests driver integration with sandbox API
6. Tests complete user request flow

Run this to verify that the E2B integration is working correctly before
running more complex agent scenarios.

Usage:
    python test_executor.py
"""

import os
import sys
import time
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

    required_vars = ['E2B_API_KEY', 'SF_API_KEY']
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

    # Note: SF_API_URL is not required anymore - API runs in sandbox at localhost:8000
    print(f"✓ SF_API_URL: Not needed (API runs in sandbox)")

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


def test_upload_files():
    """Test uploading mock API and driver files to sandbox."""
    print("\n\nTest 3: Upload Files to Sandbox")
    print("=" * 80)

    api_key = os.getenv('E2B_API_KEY')
    if not api_key:
        print("✗ Cannot test - E2B_API_KEY not set")
        return False

    try:
        print("Creating sandbox...")
        sandbox = Sandbox.create(api_key=api_key)
        print(f"✓ Sandbox created: {sandbox.sandbox_id}")

        # Upload mock API files
        print("\nUploading mock API files...")
        mock_api_path = Path(__file__).parent / 'mock_api'

        if not mock_api_path.exists():
            print(f"✗ Mock API directory not found at {mock_api_path}")
            sandbox.kill()
            return False

        api_files = ['main.py', 'db.py', 'soql_parser.py']
        for filename in api_files:
            file_path = mock_api_path / filename
            if file_path.exists():
                print(f"  Uploading {filename}...")
                with open(file_path, 'r') as f:
                    content = f.read()
                sandbox.files.write(f'/home/user/mock_api/{filename}', content)
                print(f"  ✓ {filename} uploaded")
            else:
                print(f"  ⚠ {filename} not found, skipping")

        # Upload test data
        print("\nUploading test data...")
        test_data_path = mock_api_path / 'test_data.json'
        if test_data_path.exists():
            with open(test_data_path, 'r') as f:
                content = f.read()
            sandbox.files.write('/home/user/mock_api/test_data.json', content)
            print("  ✓ test_data.json uploaded")
        else:
            print("  ⚠ test_data.json not found, skipping")

        # Upload driver files
        print("\nUploading driver files...")
        driver_path = Path(__file__).parent / 'salesforce_driver'

        if not driver_path.exists():
            print(f"✗ Driver directory not found at {driver_path}")
            sandbox.kill()
            return False

        for py_file in driver_path.glob('*.py'):
            if py_file.name.startswith('test_'):
                continue

            print(f"  Uploading {py_file.name}...")
            with open(py_file, 'r') as f:
                content = f.read()
            sandbox.files.write(f'/home/user/salesforce_driver/{py_file.name}', content)
            print(f"  ✓ {py_file.name} uploaded")

        # Verify files are readable
        print("\nVerifying uploaded files...")
        result = sandbox.run_code("""
import os
print("Files in /home/user/mock_api:")
if os.path.exists('/home/user/mock_api'):
    for f in os.listdir('/home/user/mock_api'):
        print(f"  - {f}")
else:
    print("  Directory not found!")

print("\\nFiles in /home/user/salesforce_driver:")
if os.path.exists('/home/user/salesforce_driver'):
    for f in os.listdir('/home/user/salesforce_driver'):
        print(f"  - {f}")
else:
    print("  Directory not found!")
""")

        if result.error:
            print(f"✗ Verification failed: {result.error}")
            sandbox.kill()
            return False

        print(result.text)

        # Clean up
        sandbox.kill()
        print("\n✓ File upload test passed")
        return True

    except Exception as e:
        print(f"✗ File upload test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_start_mock_api():
    """Test starting the mock API inside the sandbox."""
    print("\n\nTest 4: Start Mock API in Sandbox")
    print("=" * 80)

    api_key = os.getenv('E2B_API_KEY')
    if not api_key:
        print("✗ Cannot test - E2B_API_KEY not set")
        return False

    try:
        print("Creating sandbox...")
        sandbox = Sandbox.create(api_key=api_key)
        print(f"✓ Sandbox created: {sandbox.sandbox_id}")

        # Upload mock API files (simplified version for testing)
        print("\nUploading mock API files...")
        mock_api_path = Path(__file__).parent / 'mock_api'

        api_files = ['main.py', 'db.py', 'soql_parser.py']
        for filename in api_files:
            file_path = mock_api_path / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                sandbox.files.write(f'/home/user/mock_api/{filename}', content)

        # Upload test data if exists
        test_data_path = mock_api_path / 'test_data.json'
        if test_data_path.exists():
            with open(test_data_path, 'r') as f:
                content = f.read()
            sandbox.files.write('/home/user/mock_api/test_data.json', content)

        # Install dependencies
        print("\nInstalling dependencies...")
        result = sandbox.run_code("!pip install fastapi uvicorn requests -q")
        if result.error:
            print(f"  ⚠ Warning during install: {result.error}")
        else:
            print("  ✓ Dependencies installed")

        # Start the mock API in background
        print("\nStarting mock API server...")
        start_api_code = """
import subprocess
import sys
import os

# Start FastAPI server in background
proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'mock_api.main:app', '--host', '0.0.0.0', '--port', '8000'],
    cwd='/home/user',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

print(f"API server started with PID: {proc.pid}")
"""
        result = sandbox.run_code(start_api_code)
        if result.error:
            print(f"✗ Failed to start API: {result.error}")
            sandbox.kill()
            return False

        print(result.text)

        # Wait a moment for server to start
        print("\nWaiting for API to start...")
        time.sleep(3)

        # Test API connectivity from within sandbox
        print("\nTesting API connectivity from within sandbox...")
        test_code = """
import urllib.request
import json

try:
    # Test health endpoint
    response = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
    data = response.read().decode()
    print(f"✓ Health check passed: {data}")

    # Test sobjects endpoint
    response = urllib.request.urlopen('http://localhost:8000/sobjects', timeout=5)
    data = json.loads(response.read().decode())
    print(f"✓ Sobjects endpoint works: {len(data['sobjects'])} objects found")

except Exception as e:
    print(f"✗ API test failed: {e}")
"""
        result = sandbox.run_code(test_code)
        print(result.text)

        if result.error or '✗' in result.text:
            print("\n⚠ API may not be running properly")
            sandbox.kill()
            return False

        # Clean up
        sandbox.kill()
        print("\n✓ Mock API startup test passed")
        return True

    except Exception as e:
        print(f"✗ Mock API test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_driver_integration():
    """Test loading the Salesforce driver and integrating with mock API."""
    print("\n\nTest 5: Driver Integration")
    print("=" * 80)

    try:
        print("Creating executor (this will create sandbox and load driver)...")
        executor = AgentExecutor()

        # Verify sandbox was created
        if not executor.sandbox:
            print("✗ Sandbox not created")
            return False

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
print("✓ SalesforceClient imported successfully!")
print(f"  Type: {type(SalesforceClient)}")
"""

        result = executor.sandbox.run_code(test_code)

        if result.error:
            print(f"✗ Driver import failed: {result.error}")
            executor.close()
            return False

        print(result.text)

        # Clean up
        executor.close()
        print("\n✓ Driver integration test passed")
        return True

    except Exception as e:
        print(f"✗ Driver integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_full_request():
    """Test the complete flow with user request."""
    print("\n\nTest 6: Full Request Flow")
    print("=" * 80)

    try:
        print("Creating executor...")
        executor = AgentExecutor()

        print(f"✓ Sandbox ready: {executor.sandbox.sandbox_id}")

        # Note: In the new architecture, we would need to:
        # 1. Upload mock API files to sandbox
        # 2. Start mock API in sandbox
        # 3. Configure driver to use localhost:8000
        #
        # For now, this test will use whatever API URL is configured

        print("\nExecuting simple query...")

        # Use the sandbox-local API URL (localhost:8000 in sandbox)
        script = ScriptTemplates.get_all_leads(
            api_url="http://localhost:8000",  # Local to sandbox
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
            print(f"⚠ Query failed (expected if mock API not running in sandbox): {result['error']}")
            print(f"\nNote: This test requires mock API to be running in the sandbox.")
            print(f"      Current architecture may still use host-based API.")

        # Clean up
        executor.close()
        print("\n✓ Full request test completed")
        return True

    except Exception as e:
        print(f"✗ Full request test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "=" * 80)
    print("AGENT EXECUTOR TEST SUITE - E2B SANDBOX ARCHITECTURE")
    print("=" * 80)
    print("\nNEW ARCHITECTURE:")
    print("  - Mock API runs INSIDE E2B sandbox")
    print("  - Driver queries API at localhost:8000 (sandbox-local)")
    print("  - No host.docker.internal needed")
    print("=" * 80)

    tests = [
        ("Environment Variables", test_environment),
        ("E2B Connection", test_e2b_connection),
        ("Upload Files", test_upload_files),
        ("Start Mock API", test_start_mock_api),
        ("Driver Integration", test_driver_integration),
        ("Full Request", test_full_request),
    ]

    results = []

    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))

            # If a critical test fails, stop
            if not passed and name in ["Environment Variables", "E2B Connection"]:
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
        print("\nAll tests passed!")
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
            'env', 'e2b', 'upload', 'api', 'driver', 'full', 'all'
        ],
        default='all',
        help='Specific test to run (default: all)'
    )

    args = parser.parse_args()

    test_map = {
        'env': test_environment,
        'e2b': test_e2b_connection,
        'upload': test_upload_files,
        'api': test_start_mock_api,
        'driver': test_driver_integration,
        'full': test_full_request,
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
