"""
Agent Executor for Salesforce Driver in E2B Sandbox

This module orchestrates the execution of Salesforce operations within an E2B sandbox.
It simulates how an AI agent would:
1. Create a secure E2B sandbox environment
2. Load the Salesforce driver into the sandbox
3. Perform discovery operations (list objects, get fields)
4. Generate and execute Python scripts based on user requests
5. Return results and handle errors gracefully

The executor bridges the gap between user intent and actual Salesforce operations,
providing isolation and security through E2B's sandboxed environment.
"""

import os
import sys
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
    - Creates isolated sandbox environments
    - Uploads and configures the driver
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
        sf_api_url: Optional[str] = None,
        sf_api_key: Optional[str] = None,
        auto_load_driver: bool = True
    ):
        """
        Initialize the Agent Executor.

        Args:
            e2b_api_key: E2B API key (defaults to E2B_API_KEY env var)
            sf_api_url: Salesforce API URL (defaults to SF_API_URL env var)
            sf_api_key: Salesforce API key (defaults to SF_API_KEY env var)
            auto_load_driver: Whether to automatically load driver on sandbox creation
        """
        # Load environment variables
        load_dotenv()

        self.e2b_api_key = e2b_api_key or os.getenv('E2B_API_KEY')
        self.sf_api_url = sf_api_url or os.getenv('SF_API_URL', 'http://localhost:8000')
        self.sf_api_key = sf_api_key or os.getenv('SF_API_KEY')
        self.auto_load_driver = auto_load_driver

        # Validate required credentials
        if not self.e2b_api_key:
            raise ValueError(
                "E2B API key is required. Set E2B_API_KEY environment variable or pass e2b_api_key parameter."
            )

        if not self.sf_api_key:
            raise ValueError(
                "Salesforce API key is required. Set SF_API_KEY environment variable or pass sf_api_key parameter."
            )

        # Convert localhost URL to docker-accessible URL for sandbox
        # In E2B sandbox, localhost on host is accessible via host.docker.internal
        self.sandbox_sf_api_url = self.sf_api_url.replace('localhost', 'host.docker.internal')

        logger.info(f"AgentExecutor initialized")
        logger.info(f"  SF API URL (host): {self.sf_api_url}")
        logger.info(f"  SF API URL (sandbox): {self.sandbox_sf_api_url}")

        self.sandbox: Optional[Sandbox] = None
        self.driver_loaded = False
        self.discovered_objects: Optional[List[str]] = None
        self.object_schemas: Dict[str, Dict] = {}

    def create_sandbox(self) -> Sandbox:
        """
        Create a new E2B sandbox environment.

        Returns:
            Sandbox instance

        Raises:
            Exception: If sandbox creation fails
        """
        logger.info("Creating E2B sandbox...")

        try:
            self.sandbox = Sandbox.create(api_key=self.e2b_api_key)
            logger.info(f"Sandbox created successfully: {self.sandbox.sandbox_id}")

            # Auto-load driver if enabled
            if self.auto_load_driver:
                self.load_driver()

            return self.sandbox

        except Exception as e:
            logger.error(f"Failed to create sandbox: {str(e)}")
            raise

    def load_driver(self) -> bool:
        """
        Upload and configure the Salesforce driver in the sandbox.

        This method:
        1. Locates the salesforce_driver directory
        2. Uploads all Python files to the sandbox
        3. Installs required dependencies (requests)
        4. Verifies the driver is importable

        Returns:
            True if driver loaded successfully

        Raises:
            RuntimeError: If sandbox not created or driver loading fails
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not created. Call create_sandbox() first.")

        logger.info("Loading Salesforce driver into sandbox...")

        try:
            # Get the salesforce_driver directory path
            driver_path = Path(__file__).parent / 'salesforce_driver'

            if not driver_path.exists():
                raise FileNotFoundError(f"Salesforce driver not found at {driver_path}")

            # Upload each Python file in the driver
            logger.info(f"Uploading driver files from {driver_path}...")

            for py_file in driver_path.glob('*.py'):
                if py_file.name.startswith('test_'):
                    continue  # Skip test files

                logger.info(f"  Uploading {py_file.name}...")

                # Read file content
                with open(py_file, 'r') as f:
                    content = f.read()

                # Write to sandbox
                remote_path = f'/home/user/salesforce_driver/{py_file.name}'
                self.sandbox.filesystem.write(remote_path, content)

            logger.info("Driver files uploaded successfully")

            # Install required dependencies
            logger.info("Installing dependencies (requests)...")
            install_result = self.sandbox.run_code("!pip install requests -q")

            if install_result.error:
                logger.warning(f"Dependency installation warning: {install_result.error}")
            else:
                logger.info("Dependencies installed successfully")

            # Verify driver is importable
            logger.info("Verifying driver import...")
            test_import = """
import sys
sys.path.insert(0, '/home/user')

from salesforce_driver import SalesforceClient
print("Driver imported successfully!")
"""

            result = self.sandbox.run_code(test_import)

            if result.error:
                raise RuntimeError(f"Driver import failed: {result.error}")

            logger.info(f"Driver verification: {result.text}")
            self.driver_loaded = True

            return True

        except Exception as e:
            logger.error(f"Failed to load driver: {str(e)}")
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

# Initialize client with sandbox-accessible URL
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
            logger.info(result.text)

            # Parse the output to extract objects
            # In a real implementation, we'd use result.results or structured output
            # For now, we'll run a simpler query to get the data

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

            # Parse JSON output
            import json
            discovery_data = json.loads(extract_result.text.strip())

            self.discovered_objects = discovery_data['objects']
            self.object_schemas = discovery_data['schemas']

            logger.info(f"Discovery complete: Found {len(self.discovered_objects)} objects")

            return discovery_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse discovery output: {e}")
            logger.error(f"Output was: {extract_result.text}")
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
            result = self.sandbox.run_code(script)

            response = {
                'success': not bool(result.error),
                'output': result.text,
                'error': result.error if result.error else None,
                'data': None
            }

            # Try to parse output as JSON
            if result.text and not result.error:
                try:
                    import json
                    response['data'] = json.loads(result.text.strip())
                except json.JSONDecodeError:
                    # Output is not JSON, keep as text
                    pass

            if result.error:
                logger.error(f"Script execution failed: {result.error}")
            else:
                logger.info(f"Script executed successfully")
                logger.info(f"Output: {result.text[:500]}...")

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

# Initialize client
client = SalesforceClient(
    api_url='{self.sandbox_sf_api_url}',
    api_key='{self.sf_api_key}'
)

# Custom operation based on user prompt: {user_prompt}
# For this mockup, we'll execute a simple query
result = client.query("SELECT Id, Name, Email, Company FROM Lead LIMIT 10")

print(json.dumps(result, indent=2))
'''

        return script, f"Custom operation: {user_prompt}"

    def close(self):
        """
        Clean up resources and close the sandbox.
        """
        if self.sandbox:
            logger.info(f"Closing sandbox {self.sandbox.sandbox_id}...")
            try:
                self.sandbox.kill()
                logger.info("Sandbox closed successfully")
            except Exception as e:
                logger.warning(f"Error closing sandbox: {e}")
            finally:
                self.sandbox = None
                self.driver_loaded = False

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
