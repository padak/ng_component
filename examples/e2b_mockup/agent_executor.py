"""
Agent Executor for Salesforce Driver in E2B Sandbox

This module orchestrates the execution of Salesforce operations within an E2B sandbox.
It simulates how an AI agent would:
1. Create a secure E2B sandbox environment (cloud VM)
2. Upload and start the Mock API server inside the sandbox
3. Upload the test database and Salesforce driver
4. Perform discovery operations (list objects, get fields)
5. Generate and execute Python scripts based on user requests
6. Return results and handle errors gracefully

**CRITICAL ARCHITECTURE:**
E2B sandbox is a cloud VM, NOT local Docker. Everything runs INSIDE the sandbox:
- Mock API (uvicorn) runs on localhost:8000 WITHIN the sandbox
- DuckDB database is uploaded to the sandbox
- Salesforce driver is uploaded to the sandbox
- User scripts run inside the sandbox and access localhost:8000

The executor bridges the gap between user intent and actual Salesforce operations,
providing isolation and security through E2B's sandboxed environment.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    print("ERROR: e2b-code-interpreter not installed. Run: pip install e2b-code-interpreter")
    sys.exit(1)

from script_templates import ScriptTemplates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    Orchestrates the execution of Salesforce operations in an E2B sandbox.

    This class simulates how an AI agent would interact with the Salesforce driver:
    - Creates isolated sandbox environments (cloud VM)
    - Uploads mock API, database, and driver
    - Starts mock API server inside sandbox
    - Discovers available Salesforce objects and fields
    - Generates and executes operation scripts
    - Returns structured results

    Example:
        executor = AgentExecutor(e2b_api_key="your_key")
        result = executor.execute("Get all leads from last 30 days")
        print(result['data'])
    """

    def __init__(
        self,
        e2b_api_key: Optional[str] = None,
        sf_api_key: Optional[str] = None,
        auto_setup: bool = True
    ):
        """
        Initialize the Agent Executor.

        Args:
            e2b_api_key: E2B API key (defaults to E2B_API_KEY env var)
            sf_api_key: Salesforce API key (defaults to SF_API_KEY env var)
            auto_setup: Whether to automatically setup sandbox (upload files, start API)
        """
        # Load environment variables
        load_dotenv()

        self.e2b_api_key = e2b_api_key or os.getenv('E2B_API_KEY')
        self.sf_api_key = sf_api_key or os.getenv('SF_API_KEY', 'mock_api_key_12345')
        self.auto_setup = auto_setup

        # Validate required credentials
        if not self.e2b_api_key:
            raise ValueError(
                "E2B API key is required. Set E2B_API_KEY environment variable or pass e2b_api_key parameter."
            )

        # Inside E2B sandbox, the API will be accessible at localhost:8000
        self.sandbox_sf_api_url = 'http://localhost:8000'

        logger.info(f"AgentExecutor initialized")
        logger.info(f"  SF API URL (inside sandbox): {self.sandbox_sf_api_url}")

        self.sandbox: Optional[Sandbox] = None
        self.api_process_handle: Optional[str] = None
        self.driver_loaded = False
        self.api_started = False
        self.discovered_objects: Optional[List[str]] = None
        self.object_schemas: Dict[str, Dict] = {}

        # Get base directory (where agent_executor.py lives)
        self.base_dir = Path(__file__).parent

    def create_sandbox(self) -> Sandbox:
        """
        Create a new E2B sandbox environment (cloud VM).

        Returns:
            Sandbox instance

        Raises:
            Exception: If sandbox creation fails
        """
        logger.info("Creating E2B sandbox...")

        try:
            self.sandbox = Sandbox.create(api_key=self.e2b_api_key)
            logger.info(f"Sandbox created successfully: {self.sandbox.sandbox_id}")

            # Auto-setup if enabled
            if self.auto_setup:
                logger.info("Auto-setup enabled, uploading files and starting services...")
                self.upload_files()
                self.start_mock_api()
                self.load_driver()

            return self.sandbox

        except Exception as e:
            logger.error(f"Failed to create sandbox: {str(e)}")
            raise

    def upload_files(self) -> bool:
        """
        Upload all required files to the E2B sandbox.

        This includes:
        1. Mock API files (main.py, db.py, models.py, soql_parser.py, swagger.yaml, __init__.py)
        2. Test database (salesforce.duckdb) - BINARY file
        3. Salesforce driver files (client.py, exceptions.py, __init__.py, examples/)

        Returns:
            True if all files uploaded successfully

        Raises:
            RuntimeError: If sandbox not created or upload fails
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not created. Call create_sandbox() first.")

        logger.info("Uploading files to sandbox...")

        try:
            # 1. Upload Mock API files
            logger.info("Uploading mock_api files...")
            mock_api_dir = self.base_dir / 'mock_api'

            if not mock_api_dir.exists():
                raise FileNotFoundError(f"Mock API directory not found at {mock_api_dir}")

            # Upload each Python/YAML file in mock_api (excluding test files)
            for file_path in mock_api_dir.glob('*'):
                if file_path.is_file() and not file_path.name.startswith('test_'):
                    logger.info(f"  Uploading {file_path.name}...")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    remote_path = f'/home/user/mock_api/{file_path.name}'
                    self.sandbox.files.write(remote_path, content)

            logger.info("Mock API files uploaded successfully")

            # 2. Upload test database (BINARY)
            logger.info("Uploading test database...")
            db_path = self.base_dir / 'test_data' / 'salesforce.duckdb'

            if not db_path.exists():
                raise FileNotFoundError(f"Database not found at {db_path}")

            logger.info(f"  Uploading {db_path.name} (binary)...")
            with open(db_path, 'rb') as f:
                content = f.read()

            # Write binary content
            remote_db_path = '/home/user/test_data/salesforce.duckdb'
            self.sandbox.files.write(remote_db_path, content)
            logger.info(f"Database uploaded successfully ({len(content)} bytes)")

            # 3. Upload Salesforce driver files
            logger.info("Uploading salesforce_driver files...")
            driver_dir = self.base_dir / 'salesforce_driver'

            if not driver_dir.exists():
                raise FileNotFoundError(f"Salesforce driver not found at {driver_dir}")

            # Upload driver root files
            for py_file in driver_dir.glob('*.py'):
                if py_file.name.startswith('test_'):
                    continue  # Skip test files

                logger.info(f"  Uploading {py_file.name}...")
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                remote_path = f'/home/user/salesforce_driver/{py_file.name}'
                self.sandbox.files.write(remote_path, content)

            # Upload driver examples subdirectory
            examples_dir = driver_dir / 'examples'
            if examples_dir.exists():
                logger.info("  Uploading examples/...")
                for example_file in examples_dir.glob('*.py'):
                    logger.info(f"    Uploading {example_file.name}...")
                    with open(example_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    remote_path = f'/home/user/salesforce_driver/examples/{example_file.name}'
                    self.sandbox.files.write(remote_path, content)

            logger.info("Salesforce driver files uploaded successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to upload files: {str(e)}")
            raise

    def start_mock_api(self) -> bool:
        """
        Start the Mock API server inside the E2B sandbox.

        This method:
        1. Installs required dependencies (fastapi, uvicorn, duckdb, pydantic)
        2. Starts uvicorn server in background on port 8000
        3. Waits for server to be ready
        4. Performs health check

        Returns:
            True if API started successfully

        Raises:
            RuntimeError: If sandbox not created or API startup fails
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not created. Call create_sandbox() first.")

        logger.info("Starting Mock API server inside sandbox...")

        try:
            # 1. Install dependencies
            logger.info("Installing API dependencies (fastapi, uvicorn, duckdb, pydantic)...")
            install_cmd = "pip install fastapi uvicorn duckdb pydantic pyyaml -q"
            install_result = self.sandbox.run_code(f"!{install_cmd}")

            if install_result.error:
                logger.warning(f"Dependency installation warning: {install_result.error}")
            else:
                logger.info("Dependencies installed successfully")

            # 2. Start uvicorn in background
            logger.info("Starting uvicorn server on port 8000...")
            start_cmd = "cd /home/user/mock_api && uvicorn main:app --host 0.0.0.0 --port 8000"

            # Run in background using subprocess
            start_script = f"""
import subprocess
import sys

# Start uvicorn in background
process = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000'],
    cwd='/home/user/mock_api',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    start_new_session=True
)

print(f"Started uvicorn with PID: {{process.pid}}")
"""

            result = self.sandbox.run_code(start_script)

            if result.error:
                logger.error(f"Failed to start uvicorn: {result.error}")
                raise RuntimeError(f"Failed to start Mock API: {result.error}")

            logger.info(f"Uvicorn started: {("".join(result.logs.stdout) if result.logs.stdout else "")}")
            self.api_started = True

            # 3. Wait for server to be ready
            logger.info("Waiting for API server to be ready (3 seconds)...")
            time.sleep(3)

            # 4. Health check
            logger.info("Performing health check...")
            health_check_script = """
import requests
import json

try:
    response = requests.get('http://localhost:8000/health', timeout=5)
    result = {
        'success': response.status_code == 200,
        'status_code': response.status_code,
        'body': response.json() if response.status_code == 200 else response.text
    }
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({'success': False, 'error': str(e)}))
"""

            health_result = self.sandbox.run_code(health_check_script)

            if health_result.error:
                raise RuntimeError(f"Health check failed: {health_result.error}")

            # Parse health check result from stdout (print() output)
            import json
            stdout_text = ''.join(health_result.logs.stdout) if health_result.logs.stdout else ''
            if not stdout_text:
                raise RuntimeError("Health check returned no output")
            health_data = json.loads(stdout_text.strip())

            if not health_data.get('success'):
                raise RuntimeError(f"API not responding: {health_data.get('error', 'Unknown error')}")

            logger.info(f"Health check passed: {health_data.get('body')}")
            logger.info("Mock API server is ready!")

            return True

        except Exception as e:
            logger.error(f"Failed to start Mock API: {str(e)}")
            raise

    def load_driver(self) -> bool:
        """
        Verify the Salesforce driver is available in the sandbox.

        The driver files should already be uploaded by upload_files().
        This method just verifies they're importable.

        Returns:
            True if driver loaded successfully

        Raises:
            RuntimeError: If sandbox not created or driver verification fails
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not created. Call create_sandbox() first.")

        logger.info("Verifying Salesforce driver...")

        try:
            # Install requests dependency
            logger.info("Installing driver dependencies (requests)...")
            install_result = self.sandbox.run_code("!pip install requests -q")

            if install_result.error:
                logger.warning(f"Dependency installation warning: {install_result.error}")
            else:
                logger.info("Dependencies installed successfully")

            # Verify driver is importable
            logger.info("Testing driver import...")
            test_import = """
import sys
sys.path.insert(0, '/home/user')

from salesforce_driver import SalesforceClient
print("Driver imported successfully!")
"""

            result = self.sandbox.run_code(test_import)

            if result.error:
                raise RuntimeError(f"Driver import failed: {result.error}")

            logger.info(f"Driver verification: {("".join(result.logs.stdout) if result.logs.stdout else "")}")
            self.driver_loaded = True

            return True

        except Exception as e:
            logger.error(f"Failed to verify driver: {str(e)}")
            raise

    def run_discovery(self) -> Dict[str, Any]:
        """
        Run discovery to find available Salesforce objects and their schemas.

        This is typically the first operation an agent would perform to understand
        what data is available in the Salesforce instance.

        Returns:
            Dictionary containing:
                - objects: List of available object names
                - schemas: Dict mapping object names to their field schemas

        Raises:
            RuntimeError: If sandbox/driver not loaded
        """
        if not self.sandbox or not self.driver_loaded:
            raise RuntimeError("Sandbox and driver must be loaded. Call create_sandbox() first.")

        logger.info("Running discovery to find available objects...")

        # Build discovery script
        discovery_code = f"""
import sys
sys.path.insert(0, '/home/user')

from salesforce_driver import SalesforceClient

# Initialize client (API is at localhost:8000 inside sandbox)
client = SalesforceClient(
    api_url='{self.sandbox_sf_api_url}',
    api_key='{self.sf_api_key}'
)

# List all available objects
print("Discovering objects...")
objects = client.list_objects()
print(f"Found {{len(objects)}} objects: {{', '.join(objects)}}")

# Get schema for each object
schemas = {{}}
for obj_name in objects:
    print(f"\\nGetting schema for {{obj_name}}...")
    try:
        schema = client.get_fields(obj_name)
        schemas[obj_name] = schema
        field_count = len(schema.get('fields', []))
        print(f"  {{obj_name}} has {{field_count}} fields")
    except Exception as e:
        print(f"  Warning: Could not get schema for {{obj_name}}: {{e}}")

print(f"\\nDiscovery complete! Objects: {{objects}}")
"""

        try:
            result = self.sandbox.run_code(discovery_code)

            if result.error:
                logger.error(f"Discovery failed: {result.error}")
                raise RuntimeError(f"Discovery execution failed: {result.error}")

            logger.info("Discovery output:")
            logger.info(("".join(result.logs.stdout) if result.logs.stdout else ""))

            # Extract structured data
            extract_code = f"""
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

client = SalesforceClient(
    api_url='{self.sandbox_sf_api_url}',
    api_key='{self.sf_api_key}'
)

objects = client.list_objects()

# Get basic schema info for each object
schemas = {{}}
for obj_name in objects:
    try:
        schema = client.get_fields(obj_name)
        # Store simplified schema (just field names and types)
        schemas[obj_name] = {{
            'name': schema.get('name'),
            'fields': [
                {{'name': f['name'], 'type': f['type'], 'label': f.get('label', f['name'])}}
                for f in schema.get('fields', [])
            ]
        }}
    except:
        pass

result = {{
    'objects': objects,
    'schemas': schemas
}}

print(json.dumps(result))
"""

            extract_result = self.sandbox.run_code(extract_code)

            if extract_result.error:
                raise RuntimeError(f"Failed to extract discovery data: {extract_result.error}")

            # Parse JSON output from stdout (print() output)
            import json
            stdout_text = ''.join(extract_result.logs.stdout) if extract_result.logs.stdout else ''
            if not stdout_text:
                raise RuntimeError("Discovery returned no output")
            discovery_data = json.loads(stdout_text.strip())

            self.discovered_objects = discovery_data['objects']
            self.object_schemas = discovery_data['schemas']

            logger.info(f"Discovery complete: Found {len(self.discovered_objects)} objects")

            return discovery_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse discovery output: {e}")
            logger.error(f"Output was: {extract_("".join(result.logs.stdout) if result.logs.stdout else "")}")
            raise
        except Exception as e:
            logger.error(f"Discovery failed: {str(e)}")
            raise

    def execute_script(self, script: str, description: str = "Custom script") -> Dict[str, Any]:
        """
        Execute a Python script in the sandbox.

        Args:
            script: Python code to execute
            description: Human-readable description of what the script does

        Returns:
            Dictionary containing:
                - success: Boolean indicating if execution succeeded
                - output: Text output from the script
                - error: Error message if execution failed
                - data: Parsed data if available
        """
        if not self.sandbox or not self.driver_loaded:
            raise RuntimeError("Sandbox and driver must be loaded. Call create_sandbox() first.")

        logger.info(f"Executing script: {description}")
        logger.info(f"Script preview:\n{script[:200]}...")

        try:
            # Execute with PYTHONPATH set to /home/user
            result = self.sandbox.run_code(
                script,
                envs={'PYTHONPATH': '/home/user'}
            )

            # Get output from stdout (print() output)
            stdout_text = ''.join(result.logs.stdout) if result.logs.stdout else ''

            response = {
                'success': not bool(result.error),
                'output': stdout_text,
                'error': result.error if result.error else None,
                'data': None
            }

            # Try to parse output as JSON
            # Scripts often print descriptive text followed by JSON on the last line(s)
            if stdout_text and not result.error:
                try:
                    import json
                    import re

                    # Try parsing the entire output first
                    try:
                        response['data'] = json.loads(stdout_text.strip())
                    except json.JSONDecodeError:
                        # Failed - try to extract JSON from the end of output
                        # Look for last complete JSON object/array
                        # Find last occurrence of standalone { or [
                        lines = stdout_text.strip().split('\n')

                        # Try parsing from the end backwards
                        for i in range(len(lines) - 1, -1, -1):
                            try:
                                # Try to parse from this line to the end
                                json_text = '\n'.join(lines[i:])
                                response['data'] = json.loads(json_text)
                                break  # Success!
                            except json.JSONDecodeError:
                                continue

                except Exception:
                    # Output is not JSON, keep as text
                    pass

            if result.error:
                logger.error(f"Script execution failed: {result.error}")
            else:
                logger.info(f"Script executed successfully")
                logger.info(f"Output: {stdout_text[:500] if stdout_text else '(no output)'}...")

            return response

        except Exception as e:
            logger.error(f"Failed to execute script: {str(e)}")
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'data': None
            }

    def execute(self, user_prompt: str, use_template: bool = True) -> Dict[str, Any]:
        """
        Main execution method - orchestrates the entire flow.

        This method simulates how an AI agent would handle a user request:
        1. Parse the user intent
        2. Create sandbox if needed
        3. Run discovery if needed
        4. Generate appropriate script (from template or custom)
        5. Execute the script
        6. Return results

        Args:
            user_prompt: Natural language description of what to do
                        (e.g., "Get all leads from last 30 days")
            use_template: Whether to use predefined templates (True) or
                         generate custom scripts (False)

        Returns:
            Dictionary containing execution results and metadata
        """
        logger.info("="*80)
        logger.info(f"EXECUTING USER REQUEST: {user_prompt}")
        logger.info("="*80)

        try:
            # Step 1: Create sandbox if needed
            if not self.sandbox:
                logger.info("Step 1: Creating sandbox...")
                self.create_sandbox()
            else:
                logger.info("Step 1: Using existing sandbox")

            # Step 2: Run discovery if needed
            if not self.discovered_objects:
                logger.info("Step 2: Running discovery...")
                discovery = self.run_discovery()
                logger.info(f"  Found objects: {', '.join(discovery['objects'])}")
            else:
                logger.info("Step 2: Using cached discovery data")

            # Step 3: Generate script based on user prompt
            logger.info("Step 3: Generating script...")

            if use_template:
                script, description = self._generate_from_template(user_prompt)
            else:
                script, description = self._generate_custom_script(user_prompt)

            logger.info(f"  Generated: {description}")

            # Step 4: Execute the script
            logger.info("Step 4: Executing script in sandbox...")
            result = self.execute_script(script, description)

            # Step 5: Package and return results
            logger.info("Step 5: Packaging results...")

            response = {
                'success': result['success'],
                'user_prompt': user_prompt,
                'description': description,
                'output': result['output'],
                'error': result['error'],
                'data': result['data'],
                'sandbox_id': self.sandbox.sandbox_id if self.sandbox else None,
                'discovered_objects': self.discovered_objects
            }

            logger.info("="*80)
            if result['success']:
                logger.info("EXECUTION COMPLETED SUCCESSFULLY")
            else:
                logger.info("EXECUTION FAILED")
            logger.info("="*80)

            return response

        except Exception as e:
            logger.error(f"Execution failed with exception: {str(e)}")
            return {
                'success': False,
                'user_prompt': user_prompt,
                'description': 'Failed to execute',
                'output': '',
                'error': str(e),
                'data': None,
                'sandbox_id': self.sandbox.sandbox_id if self.sandbox else None,
                'discovered_objects': self.discovered_objects
            }

    def _generate_from_template(self, user_prompt: str) -> Tuple[str, str]:
        """
        Generate a script from predefined templates based on user prompt.

        Args:
            user_prompt: User's natural language request

        Returns:
            Tuple of (script_code, description)
        """
        prompt_lower = user_prompt.lower()

        # Match user prompt to appropriate template
        if 'recent leads' in prompt_lower or 'leads from last' in prompt_lower:
            # Extract days if specified
            days = 30  # default
            if 'days' in prompt_lower:
                import re
                match = re.search(r'(\d+)\s*days?', prompt_lower)
                if match:
                    days = int(match.group(1))

            script = ScriptTemplates.get_recent_leads(
                api_url=self.sandbox_sf_api_url,
                api_key=self.sf_api_key,
                days=days
            )
            description = f"Get leads from last {days} days"

        elif 'campaign' in prompt_lower and 'leads' in prompt_lower:
            # Extract campaign name
            campaign_name = "Summer Campaign"  # default
            if 'campaign' in prompt_lower:
                import re
                # Try to extract campaign name in quotes or after "campaign"
                match = re.search(r'campaign[:\s]+["\']?([^"\']+)["\']?', prompt_lower)
                if match:
                    campaign_name = match.group(1).strip()

            script = ScriptTemplates.get_campaign_with_leads(
                api_url=self.sandbox_sf_api_url,
                api_key=self.sf_api_key,
                campaign_name=campaign_name
            )
            description = f"Get campaign '{campaign_name}' with its leads"

        elif 'status' in prompt_lower and 'lead' in prompt_lower:
            # Extract status
            status = "New"  # default
            for s in ['new', 'qualified', 'unqualified', 'working']:
                if s in prompt_lower:
                    status = s.capitalize()
                    break

            script = ScriptTemplates.get_leads_by_status(
                api_url=self.sandbox_sf_api_url,
                api_key=self.sf_api_key,
                status=status
            )
            description = f"Get leads with status '{status}'"

        elif 'all leads' in prompt_lower or 'list leads' in prompt_lower:
            script = ScriptTemplates.get_all_leads(
                api_url=self.sandbox_sf_api_url,
                api_key=self.sf_api_key
            )
            description = "Get all leads"

        else:
            # Default: get all leads
            script = ScriptTemplates.get_all_leads(
                api_url=self.sandbox_sf_api_url,
                api_key=self.sf_api_key
            )
            description = f"Execute query: {user_prompt}"

        return script, description

    def _generate_custom_script(self, user_prompt: str) -> Tuple[str, str]:
        """
        Generate a custom script based on user prompt.

        In a real AI agent, this would use Claude or another LLM to generate
        the script. For this mockup, we'll create a simple template.

        Args:
            user_prompt: User's natural language request

        Returns:
            Tuple of (script_code, description)
        """
        # For mockup purposes, we'll create a simple query script
        # In production, this would be generated by an LLM

        script = f'''
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

# Initialize client (API at localhost:8000 inside sandbox)
client = SalesforceClient(
    api_url='{self.sandbox_sf_api_url}',
    api_key='{self.sf_api_key}'
)

# Custom operation based on user prompt: {user_prompt}
# For this mockup, we'll execute a simple query
result = client.query("SELECT Id, FirstName, LastName, Email, Company FROM Lead LIMIT 10")

print(json.dumps(result, indent=2))
'''

        return script, f"Custom operation: {user_prompt}"

    def stop_mock_api(self) -> bool:
        """
        Stop the Mock API server running in the sandbox.

        Returns:
            True if API stopped successfully
        """
        if not self.sandbox or not self.api_started:
            logger.info("No API to stop")
            return True

        logger.info("Stopping Mock API server...")

        try:
            # Kill uvicorn process
            stop_script = """
import subprocess
import signal
import os

# Find and kill uvicorn processes
result = subprocess.run(['pkill', '-f', 'uvicorn'], capture_output=True)
print(f"Stopped uvicorn processes")
"""

            result = self.sandbox.run_code(stop_script)

            if result.error:
                logger.warning(f"Error stopping API: {result.error}")
            else:
                logger.info("API stopped successfully")

            self.api_started = False
            return True

        except Exception as e:
            logger.warning(f"Error stopping Mock API: {e}")
            return False

    def close(self):
        """
        Clean up resources and close the sandbox.
        """
        if self.sandbox:
            logger.info(f"Closing sandbox {self.sandbox.sandbox_id}...")
            try:
                # Stop API first
                self.stop_mock_api()

                # Close sandbox
                self.sandbox.kill()
                logger.info("Sandbox closed successfully")
            except Exception as e:
                logger.warning(f"Error closing sandbox: {e}")
            finally:
                self.sandbox = None
                self.driver_loaded = False
                self.api_started = False

    def __enter__(self):
        """Context manager entry"""
        self.create_sandbox()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False


def main():
    """
    Example usage of the AgentExecutor.
    """
    print("Agent Executor - Example Usage")
    print("="*80)

    # Check for E2B API key
    if not os.getenv('E2B_API_KEY'):
        print("ERROR: E2B_API_KEY environment variable not set")
        print("Please set it in your .env file or environment")
        return

    try:
        # Create executor (can also use context manager)
        executor = AgentExecutor()

        # Example 1: Get recent leads
        print("\nExample 1: Get recent leads")
        print("-"*80)
        result = executor.execute("Get all leads from last 30 days")

        if result['success']:
            print(f"SUCCESS: {result['description']}")
            print(f"Output:\n{result['output'][:500]}...")
        else:
            print(f"FAILED: {result['error']}")

        # Example 2: Get campaign with leads
        print("\n\nExample 2: Get campaign with leads")
        print("-"*80)
        result = executor.execute("Get leads for Summer Campaign")

        if result['success']:
            print(f"SUCCESS: {result['description']}")
            if result['data']:
                print(f"Retrieved {len(result['data'])} records")
        else:
            print(f"FAILED: {result['error']}")

        # Clean up
        executor.close()

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
