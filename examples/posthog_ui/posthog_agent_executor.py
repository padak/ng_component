"""
PostHog Agent Executor - Manages E2B sandboxes for PostHog driver execution.

This module handles:
- Creating E2B sandboxes (cloud VMs)
- Uploading PostHog driver code to sandbox
- Installing dependencies
- Executing HogQL query scripts
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from e2b_code_interpreter import Sandbox
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostHogAgentExecutor:
    """
    Executes PostHog queries in E2B sandboxes.

    Architecture:
    - PostHog driver code uploaded to /home/user/posthog_driver/
    - Scripts execute with PYTHONPATH=/home/user
    - Queries run against PostHog cloud API
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the PostHog Agent Executor.

        Args:
            api_key: E2B API key (if not provided, will use E2B_API_KEY env var)
        """
        self.e2b_api_key = api_key or os.getenv('E2B_API_KEY')
        if not self.e2b_api_key:
            raise ValueError(
                "E2B_API_KEY is required. "
                "Get your API key from https://e2b.dev/ and set it in your .env file."
            )

        # PostHog credentials from environment
        self.posthog_api_key = os.getenv('POSTHOG_API_KEY')
        self.posthog_project_id = os.getenv('POSTHOG_PROJECT_ID')
        self.posthog_region = os.getenv('POSTHOG_REGION', 'us')

        if not self.posthog_api_key or not self.posthog_project_id:
            raise ValueError(
                "POSTHOG_API_KEY and POSTHOG_PROJECT_ID are required. "
                "Set them in your .env file."
            )

        # Determine PostHog host URL
        if self.posthog_region == 'us':
            self.posthog_host = 'https://us.posthog.com'
        elif self.posthog_region == 'eu':
            self.posthog_host = 'https://eu.posthog.com'
        else:
            self.posthog_host = os.getenv('POSTHOG_CUSTOM_BASE_URL', 'https://us.posthog.com')

        logger.info(f"PostHogAgentExecutor initialized")
        logger.info(f"PostHog Host: {self.posthog_host}")
        logger.info(f"Project ID: {self.posthog_project_id}")

        self.sandbox: Optional[Sandbox] = None

    def create_sandbox(self):
        """
        Create E2B sandbox and upload PostHog driver.
        """
        logger.info("Creating E2B sandbox...")

        # Create sandbox (use constructor, not .create())
        self.sandbox = Sandbox(api_key=self.e2b_api_key)
        logger.info(f"Sandbox created: {self.sandbox.sandbox_id}")

        # Upload PostHog driver
        logger.info("Uploading PostHog driver to sandbox...")
        self._upload_driver()

        # Install dependencies
        logger.info("Installing dependencies...")
        self._install_dependencies()

        logger.info("Sandbox ready for PostHog queries!")

    def _upload_driver(self):
        """Upload PostHog driver code to sandbox."""
        # Path to PostHog driver directory
        driver_dir = Path(__file__).parent.parent / "posthog_driver" / "posthog_driver"

        if not driver_dir.exists():
            raise FileNotFoundError(f"PostHog driver directory not found: {driver_dir}")

        # Upload all Python files
        for py_file in driver_dir.glob("*.py"):
            target_path = f"/home/user/posthog_driver/{py_file.name}"
            content = py_file.read_text()
            self.sandbox.files.write(target_path, content)
            logger.info(f"  Uploaded: {py_file.name}")

    def _install_dependencies(self):
        """Install required Python packages."""
        install_code = """
import subprocess
import sys

packages = ['requests', 'python-dotenv']

for package in packages:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', package])

print('Dependencies installed successfully')
"""
        result = self.sandbox.run_code(install_code)

        if result.error:
            logger.error(f"Failed to install dependencies: {result.error}")
            raise RuntimeError(f"Dependency installation failed: {result.error}")

        logger.info("Dependencies installed successfully")

    def execute_script(self, script: str, description: str = "Execute PostHog query") -> Dict[str, Any]:
        """
        Execute a PostHog query script in the sandbox.

        Args:
            script: Python code to execute (should use PostHogDriver)
            description: Human-readable description of the query

        Returns:
            Dictionary with:
            - success: bool
            - data: Query results (if successful)
            - output: Script output
            - error: Error message (if failed)
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not created. Call create_sandbox() first.")

        logger.info(f"Executing: {description}")
        logger.debug(f"Script:\n{script}")

        try:
            # Set environment variables for PostHog
            envs = {
                'POSTHOG_API_KEY': self.posthog_api_key,
                'POSTHOG_PROJECT_ID': self.posthog_project_id,
                'POSTHOG_REGION': self.posthog_region,
                'POSTHOG_HOST': self.posthog_host,
                'PYTHONPATH': '/home/user'
            }

            # Execute the script
            result = self.sandbox.run_code(script, envs=envs)

            # Collect output
            stdout = '\n'.join(result.logs.stdout) if result.logs.stdout else ''
            stderr = '\n'.join(result.logs.stderr) if result.logs.stderr else ''
            output = stdout + stderr

            if result.error:
                logger.error(f"Script execution failed: {result.error}")
                return {
                    'success': False,
                    'error': str(result.error),
                    'output': output
                }

            # Try to parse JSON output
            data = None
            if stdout.strip():
                try:
                    data = json.loads(stdout.strip())
                except json.JSONDecodeError:
                    # If not JSON, return as plain text
                    data = {'result': stdout.strip()}

            return {
                'success': True,
                'data': data,
                'output': output,
                'description': description
            }

        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'output': ''
            }

    def run_discovery(self) -> Dict[str, Any]:
        """
        Run discovery to list available PostHog resources.

        Returns:
            Dictionary with:
            - objects: List of resource names
            - schemas: Dictionary of resource schemas
        """
        script = f"""
import sys
sys.path.insert(0, '/home/user')
from posthog_driver.client import PostHogDriver
import json

# Initialize driver
driver = PostHogDriver(
    api_url='{self.posthog_host}',
    api_key='{self.posthog_api_key}',
    project_id='{self.posthog_project_id}'
)

# Discover objects
objects = driver.list_objects()

# Get schemas for each object
schemas = {{}}
for obj in objects:
    try:
        schemas[obj] = driver.get_fields(obj)
    except Exception as e:
        schemas[obj] = {{'error': str(e)}}

result = {{
    'objects': objects,
    'schemas': schemas
}}

print(json.dumps(result, indent=2))
"""

        result = self.execute_script(script, "Discover PostHog resources")

        if result['success'] and result['data']:
            return result['data']
        else:
            return {
                'objects': [],
                'schemas': {},
                'error': result.get('error', 'Discovery failed')
            }

    def close(self):
        """Clean up sandbox resources."""
        if self.sandbox:
            try:
                logger.info(f"Killing sandbox {self.sandbox.sandbox_id}...")
                self.sandbox.kill()
                logger.info("Sandbox killed successfully")
            except Exception as e:
                logger.error(f"Error killing sandbox: {e}")
            finally:
                self.sandbox = None


# Example usage
if __name__ == "__main__":
    executor = PostHogAgentExecutor()

    try:
        # Create sandbox
        executor.create_sandbox()

        # Run discovery
        print("\n=== Discovering PostHog Resources ===")
        discovery = executor.run_discovery()
        print(json.dumps(discovery, indent=2))

        # Example query
        print("\n=== Running Example Query ===")
        query_script = f"""
import sys
sys.path.insert(0, '/home/user')
from posthog_driver.client import PostHogDriver
import json

driver = PostHogDriver(
    api_url='{executor.posthog_host}',
    api_key='{executor.posthog_api_key}',
    project_id='{executor.posthog_project_id}'
)

# Query recent events
results = driver.read('''
    SELECT event, count() as total
    FROM events
    WHERE timestamp >= now() - INTERVAL 7 DAY
    GROUP BY event
    ORDER BY total DESC
    LIMIT 10
''')

print(json.dumps({{'count': len(results), 'events': results}}, indent=2))
"""

        result = executor.execute_script(query_script, "Get top events from last 7 days")
        print(json.dumps(result, indent=2))

    finally:
        executor.close()
