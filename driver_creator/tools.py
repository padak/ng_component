"""
Driver Creator Agent - Tool Implementations

This module provides tools for the Driver Creator Agent:
- research_api: Fetch and analyze API documentation
- evaluate_complexity: Assess automation capability
- generate_driver_scaffold: Generate driver files from templates
- validate_driver: Validate against Driver Design v2.0
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
import re
import time
from jinja2 import Environment, FileSystemLoader
from e2b_code_interpreter import Sandbox


def research_api(api_name: str, api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Research an API by fetching and analyzing its documentation.

    Args:
        api_name: Name of the API (e.g., "PostHog", "Stripe")
        api_url: Optional base URL or documentation URL

    Returns:
        Dictionary with API research data:
        {
            "api_type": "REST" | "GraphQL" | "Database",
            "auth_methods": ["api_key", "oauth", ...],
            "base_url": "https://...",
            "query_language": "HogQL" | "SQL" | "SOQL" | None,
            "endpoints": [...],
            "pagination_style": "cursor" | "offset" | "page" | "none",
            "rate_limit": "...",
            "complexity": "SIMPLE" | "MEDIUM" | "COMPLEX"
        }
    """
    result = {
        "api_name": api_name,
        "api_type": None,
        "auth_methods": [],
        "base_url": api_url or "",
        "query_language": None,
        "endpoints": [],
        "pagination_style": None,
        "rate_limit": None,
        "complexity": "MEDIUM",
        "documentation_url": None,
        "openapi_spec": None,
        "notes": []
    }

    # PostHog-specific knowledge (from Osiris analysis)
    if "posthog" in api_name.lower():
        result.update({
            "api_type": "REST",
            "auth_methods": ["api_key"],
            "base_url": "https://app.posthog.com",
            "query_language": "HogQL",
            "endpoints": [
                {"path": "/api/query", "methods": ["POST"], "description": "Execute HogQL queries"},
                {"path": "/api/event", "methods": ["GET"], "description": "Retrieve events"},
                {"path": "/api/person", "methods": ["GET"], "description": "Retrieve persons"},
                {"path": "/api/session", "methods": ["GET"], "description": "Retrieve sessions"}
            ],
            "pagination_style": "cursor",
            "rate_limit": "2400 requests/hour (90% threshold at 2160)",
            "complexity": "MEDIUM",
            "documentation_url": "https://posthog.com/docs/api",
            "notes": [
                "Uses HogQL query language (SQL-like)",
                "SEEK-based pagination (timestamp + UUID)",
                "Rate limiting: 2400 req/hour with exponential backoff",
                "Data types: events, persons, sessions, person_distinct_ids",
                "Properties are nested (need flattening)"
            ]
        })

    # Stripe-specific (example from PRD)
    elif "stripe" in api_name.lower():
        result.update({
            "api_type": "REST",
            "auth_methods": ["api_key"],
            "base_url": "https://api.stripe.com/v1",
            "query_language": None,
            "endpoints": [
                {"path": "/charges", "methods": ["GET", "POST"]},
                {"path": "/customers", "methods": ["GET", "POST", "DELETE"]},
                {"path": "/subscriptions", "methods": ["GET", "POST"]}
            ],
            "pagination_style": "cursor",
            "rate_limit": "100 requests/second",
            "complexity": "MEDIUM",
            "documentation_url": "https://stripe.com/docs/api",
            "openapi_spec": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json"
        })

    else:
        # Generic research - try to fetch documentation
        result["notes"].append(f"Generic research for {api_name}. Manual inspection recommended.")
        result["complexity"] = "COMPLEX"

    return result


def evaluate_complexity(research_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate what can be automated vs what needs human input.

    Args:
        research_data: Output from research_api

    Returns:
        Dictionary with complexity assessment:
        {
            "automation_level": "LEVEL_1" | "LEVEL_2" | "LEVEL_3",
            "automation_percentage": 0-100,
            "can_automate": [list of features],
            "needs_human": [list of features],
            "estimated_time_saved": "X hours (from Yh to Zh)",
            "confidence": 0.0-1.0
        }
    """
    api_name = research_data.get("api_name", "Unknown")
    api_type = research_data.get("api_type", "REST")
    query_language = research_data.get("query_language")
    complexity = research_data.get("complexity", "MEDIUM")

    result = {
        "automation_level": "LEVEL_2",
        "automation_percentage": 60,
        "can_automate": [],
        "needs_human": [],
        "estimated_time_saved": "6 hours (from 12h to 6h)",
        "confidence": 0.75
    }

    # Determine automation level based on API characteristics
    if api_type == "REST" and query_language is None:
        # Simple REST API - Level 1 (90% automation)
        result.update({
            "automation_level": "LEVEL_1",
            "automation_percentage": 90,
            "can_automate": [
                "Driver scaffold (BaseDriver implementation)",
                "Exception hierarchy",
                "list_objects() method",
                "get_fields() method",
                "call_endpoint() for REST API",
                "README with examples",
                "Basic unit tests"
            ],
            "needs_human": [
                "Review authentication mechanism",
                "Verify error messages",
                "Integration tests with real API",
                "Edge case handling"
            ],
            "estimated_time_saved": "7 hours (from 8h to 1h)",
            "confidence": 0.9
        })

    elif query_language in ["HogQL", "SQL", "SOQL", "MongoDB Query"]:
        # Query-based system - Level 2 (60% automation)
        result.update({
            "automation_level": "LEVEL_2",
            "automation_percentage": 60,
            "can_automate": [
                "Driver scaffold with query language support",
                "Basic discovery (list_objects, get_fields)",
                "read() method with query parsing",
                "README with query language syntax",
                "Example scripts with common queries",
                "Exception hierarchy"
            ],
            "needs_human": [
                "Query language parser (complex syntax)",
                "Schema relationship mapping",
                "Pagination implementation (cursor-based)",
                "Advanced query features",
                "Comprehensive testing"
            ],
            "estimated_time_saved": "7 hours (from 12h to 5h)",
            "confidence": 0.75
        })

    else:
        # Complex integration - Level 3 (40% automation)
        result.update({
            "automation_level": "LEVEL_3",
            "automation_percentage": 40,
            "can_automate": [
                "Project structure (folders, files)",
                "BaseDriver inheritance skeleton",
                "Exception hierarchy",
                "README template",
                "Basic CRUD method scaffolds"
            ],
            "needs_human": [
                "Complex authentication flows (OAuth, SAML)",
                "State management",
                "Business logic",
                "Connection pooling",
                "Rate limiting strategy",
                "Retry logic",
                "Comprehensive error handling",
                "Full test suite"
            ],
            "estimated_time_saved": "6 hours (from 14h to 8h)",
            "confidence": 0.6
        })

    return result


def generate_driver_scaffold(
    api_name: str,
    research_data: Dict[str, Any],
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate driver scaffold from templates.

    Args:
        api_name: Name of the API (used for driver name)
        research_data: Output from research_api
        output_dir: Optional output directory (defaults to generated_drivers/)

    Returns:
        Dictionary with generation results:
        {
            "driver_name": "posthog_driver",
            "output_path": "/path/to/driver",
            "files_created": 9,
            "files_complete": 7,
            "files_with_todos": 2,
            "todos": [
                {"file": "client.py", "line": 156, "description": "..."},
                ...
            ]
        }
    """
    # VALIDATION: Ensure we have required information
    # This enforces the "ask before generating" principle
    api_type = research_data.get("api_type", "REST")
    endpoints = research_data.get("endpoints", [])

    # For REST APIs without query language, we MUST have endpoints/objects list
    if api_type == "REST" and not research_data.get("query_language"):
        if not endpoints or len(endpoints) == 0:
            return {
                "success": False,
                "error": "MISSING_REQUIRED_INFO",
                "message": (
                    f"Cannot generate driver for {api_name} - missing required information!\n\n"
                    f"For REST APIs without query language, you MUST provide:\n"
                    f"- List of available endpoints/objects (research_data['endpoints'])\n\n"
                    f"Please ask the user:\n"
                    f"1. What objects/endpoints does this API provide?\n"
                    f"2. What are the main data entities? (e.g., 'forecast', 'historical', 'air_quality')\n\n"
                    f"Then update research_data['endpoints'] with the list before calling generate_driver_scaffold."
                ),
                "required_fields": ["endpoints"],
                "current_research_data": research_data
            }

    # Determine driver name
    driver_name = f"{api_name.lower().replace(' ', '_').replace('-', '_')}_driver"

    # Determine output directory
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "generated_drivers", driver_name)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Setup Jinja2 environment
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))

    # Normalize pagination style (Claude can return anything!)
    raw_pagination = research_data.get("pagination_style", "none")
    normalized_pagination = _normalize_pagination_style(raw_pagination)

    # Prepare template context
    context = {
        "api_name": api_name,
        "driver_name": driver_name,
        "driver_class": _to_class_name(driver_name),
        "base_url": research_data.get("base_url", ""),
        "api_type": research_data.get("api_type", "REST"),
        "auth_methods": research_data.get("auth_methods", ["api_key"]),
        "query_language": research_data.get("query_language"),
        "pagination_style": normalized_pagination,
        "endpoints": research_data.get("endpoints", []),
        "rate_limit": research_data.get("rate_limit"),
        "supports_write": research_data.get("api_type") == "REST",
        "supports_delete": False,  # Conservative default
    }

    files_created = []
    todos = []

    # Generate __init__.py
    init_template = env.get_template("__init__.py.j2")
    init_content = init_template.render(context)
    _write_file(output_path / "__init__.py", init_content)
    files_created.append("__init__.py")

    # Generate exceptions.py
    exceptions_template = env.get_template("exceptions.py.j2")
    exceptions_content = exceptions_template.render(context)
    _write_file(output_path / "exceptions.py", exceptions_content)
    files_created.append("exceptions.py")

    # Generate client.py (with TODOs)
    client_template = env.get_template("client.py.j2")
    client_content = client_template.render(context)
    _write_file(output_path / "client.py", client_content)
    files_created.append("client.py")

    # Extract TODOs from client.py
    client_todos = _extract_todos(client_content, "client.py")
    todos.extend(client_todos)

    # Generate README.md
    readme_template = env.get_template("README.md.j2")
    readme_content = readme_template.render(context)
    _write_file(output_path / "README.md", readme_content)
    files_created.append("README.md")

    # Generate examples/
    examples_dir = output_path / "examples"
    examples_dir.mkdir(exist_ok=True)

    example_template = env.get_template("example_script.py.j2")

    # Example 1: List objects
    example1 = example_template.render({**context, "example_type": "list_objects"})
    _write_file(examples_dir / "list_objects.py", example1)
    files_created.append("examples/list_objects.py")

    # Example 2: Query data
    example2 = example_template.render({**context, "example_type": "query_data"})
    _write_file(examples_dir / "query_data.py", example2)
    files_created.append("examples/query_data.py")

    # Generate tests/
    tests_dir = output_path / "tests"
    tests_dir.mkdir(exist_ok=True)

    test_template = env.get_template("test_client.py.j2")
    test_content = test_template.render(context)
    _write_file(tests_dir / "test_client.py", test_content)
    files_created.append("tests/test_client.py")

    # Count completion
    files_with_todos = len([f for f in files_created if any(t["file"] in f for t in todos)])
    files_complete = len(files_created) - files_with_todos

    return {
        "driver_name": driver_name,
        "output_path": str(output_path),
        "files_created": len(files_created),
        "files_complete": files_complete,
        "files_with_todos": files_with_todos,
        "file_list": files_created,
        "todos": todos
    }


def validate_driver(driver_path: str) -> Dict[str, Any]:
    """
    Validate driver against Driver Design v2.0 spec.

    Args:
        driver_path: Path to driver directory

    Returns:
        Dictionary with validation results:
        {
            "valid": True/False,
            "checks_passed": int,
            "checks_failed": int,
            "warnings": int,
            "details": {
                "base_driver_inheritance": "✅ OK" | "❌ FAIL",
                "required_methods": "✅ OK" | "❌ FAIL",
                ...
            }
        }
    """
    driver_path = Path(driver_path)

    checks = {
        "driver_exists": False,
        "has_init": False,
        "has_client": False,
        "has_exceptions": False,
        "has_readme": False,
        "has_examples": False,
        "has_tests": False,
        "base_driver_inheritance": False,
        "required_methods": False,
        "exception_hierarchy": False,
        "readme_complete": False,
        "examples_count": 0,
        "todos_remaining": 0,
        "no_todos": False  # Must be True for driver to be valid
    }

    # Check driver directory exists
    if not driver_path.exists():
        return {
            "valid": False,
            "checks_passed": 0,
            "checks_failed": len(checks),
            "warnings": 0,
            "details": {"error": f"Driver path does not exist: {driver_path}"}
        }

    checks["driver_exists"] = True

    # Check required files
    checks["has_init"] = (driver_path / "__init__.py").exists()
    checks["has_client"] = (driver_path / "client.py").exists()
    checks["has_exceptions"] = (driver_path / "exceptions.py").exists()
    checks["has_readme"] = (driver_path / "README.md").exists()
    checks["has_examples"] = (driver_path / "examples").exists()
    checks["has_tests"] = (driver_path / "tests").exists()

    # Check client.py content
    if checks["has_client"]:
        client_content = (driver_path / "client.py").read_text()

        # Check BaseDriver inheritance
        checks["base_driver_inheritance"] = "BaseDriver" in client_content or "class.*Driver.*:" in client_content

        # Check required methods
        required_methods = ["list_objects", "get_fields", "read", "get_capabilities"]
        checks["required_methods"] = all(method in client_content for method in required_methods)

        # Count TODOs - any TODO is a FAILURE
        todo_count = len(re.findall(r"TODO:", client_content, re.IGNORECASE))
        checks["todos_remaining"] = todo_count
        checks["no_todos"] = (todo_count == 0)  # New check: must have zero TODOs

    # Check exceptions.py content
    if checks["has_exceptions"]:
        exceptions_content = (driver_path / "exceptions.py").read_text()

        # Check exception hierarchy
        required_exceptions = ["DriverError", "AuthenticationError", "QuerySyntaxError", "RateLimitError"]
        checks["exception_hierarchy"] = all(exc in exceptions_content for exc in required_exceptions)

    # Check README.md content
    if checks["has_readme"]:
        readme_content = (driver_path / "README.md").read_text()

        # Check required sections
        required_sections = ["## Overview", "## Quick Start", "## Authentication"]
        checks["readme_complete"] = all(section in readme_content for section in required_sections)

    # Count examples
    if checks["has_examples"]:
        examples_dir = driver_path / "examples"
        checks["examples_count"] = len(list(examples_dir.glob("*.py")))

    # Calculate results
    checks_passed = sum(1 for k, v in checks.items() if k not in ["examples_count", "todos_remaining"] and v is True)
    checks_failed = len([k for k in checks.keys() if k not in ["examples_count", "todos_remaining"]]) - checks_passed

    # Warnings (don't fail validation, but should be addressed)
    warnings = 0
    if checks["examples_count"] < 3:
        warnings += 1

    # Driver is valid only if:
    # 1. All required checks pass
    # 2. No TODOs remaining (critical!)
    valid = checks_failed == 0 and checks["no_todos"] == True

    # Format details
    details = {
        "driver_exists": "✅ OK" if checks["driver_exists"] else "❌ FAIL",
        "file_structure": "✅ OK" if checks["has_init"] and checks["has_client"] and checks["has_exceptions"] else "❌ FAIL",
        "base_driver_inheritance": "✅ OK" if checks["base_driver_inheritance"] else "❌ FAIL",
        "required_methods": "✅ OK" if checks["required_methods"] else "❌ FAIL",
        "exception_hierarchy": "✅ OK" if checks["exception_hierarchy"] else "❌ FAIL",
        "documentation": "✅ OK" if checks["readme_complete"] else "⚠️ Incomplete",
        "examples": f"✅ OK ({checks['examples_count']} examples)" if checks["examples_count"] >= 3 else f"⚠️ {checks['examples_count']} examples (need 3+)",
        "tests": "✅ OK" if checks["has_tests"] else "❌ FAIL",
        "complete_implementation": "✅ OK" if checks["no_todos"] else "❌ FAIL - TODOs found",
        "todos_remaining": f"❌ FAIL - {checks['todos_remaining']} TODOs found (driver must be complete!)" if checks["todos_remaining"] > 0 else "✅ No TODOs (complete implementation)"
    }

    return {
        "valid": valid,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "warnings": warnings,
        "details": details
    }


def test_driver_in_e2b(
    driver_path: str,
    driver_name: str,
    test_api_url: Optional[str] = None,
    test_credentials: Optional[Dict[str, str]] = None,
    use_mock_api: bool = False,
    mock_api_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Test a generated driver in an E2B sandbox.

    This function creates an E2B sandbox, uploads the driver files,
    optionally starts a mock API, and runs a comprehensive test suite
    to verify the driver works correctly.

    Args:
        driver_path: Path to the driver directory
        driver_name: Name of the driver (e.g., "posthog_driver")
        test_api_url: URL of the test API (default: http://localhost:8000)
        test_credentials: Dict of credentials to pass to driver (e.g., {"api_key": "..."})
        use_mock_api: Whether to upload and start a mock API in the sandbox
        mock_api_path: Path to mock API directory (required if use_mock_api=True)

    Returns:
        Dictionary with test results:
        {
            "success": True/False,
            "tests_passed": 4,
            "tests_failed": 1,
            "output": "...",
            "errors": [...],
            "suggestions": [...],
            "execution_time": 12.5,
            "sandbox_id": "..."
        }
    """
    start_time = time.time()

    # Validate inputs
    driver_path = Path(driver_path)
    if not driver_path.exists():
        return {
            "success": False,
            "tests_passed": 0,
            "tests_failed": 0,
            "output": "",
            "errors": [f"Driver path does not exist: {driver_path}"],
            "suggestions": ["Ensure the driver directory exists and contains generated files"],
            "execution_time": 0.0,
            "sandbox_id": None
        }

    # Get E2B API key
    e2b_api_key = os.environ.get('E2B_API_KEY')
    if not e2b_api_key:
        return {
            "success": False,
            "tests_passed": 0,
            "tests_failed": 0,
            "output": "",
            "errors": ["E2B_API_KEY environment variable not set"],
            "suggestions": ["Set E2B_API_KEY in your environment or .env file"],
            "execution_time": 0.0,
            "sandbox_id": None
        }

    # Set default values
    if test_api_url is None:
        test_api_url = "http://localhost:8000"

    if test_credentials is None:
        test_credentials = {"api_key": "test_key_12345"}

    sandbox = None
    sandbox_id = None

    try:
        # Step 1: Create E2B sandbox
        print(f"Creating E2B sandbox for testing {driver_name}...")
        sandbox = Sandbox.create(api_key=e2b_api_key)
        sandbox_id = sandbox.sandbox_id
        print(f"Sandbox created: {sandbox_id}")

        # Step 2: Upload driver files
        print(f"Uploading driver files from {driver_path}...")
        remote_driver_path = f"/home/user/{driver_name}"

        # Upload all Python files in driver root
        for py_file in driver_path.glob("*.py"):
            print(f"  Uploading {py_file.name}...")
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            sandbox.files.write(f"{remote_driver_path}/{py_file.name}", content)

        # Upload examples directory if it exists
        examples_dir = driver_path / "examples"
        if examples_dir.exists():
            print(f"  Uploading examples/...")
            for example_file in examples_dir.glob("*.py"):
                with open(example_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                sandbox.files.write(f"{remote_driver_path}/examples/{example_file.name}", content)

        # Upload tests directory if it exists
        tests_dir = driver_path / "tests"
        if tests_dir.exists():
            print(f"  Uploading tests/...")
            for test_file in tests_dir.glob("*.py"):
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                sandbox.files.write(f"{remote_driver_path}/tests/{test_file.name}", content)

        print("Driver files uploaded successfully")

        # Step 3: Upload and start mock API if requested
        if use_mock_api:
            if not mock_api_path:
                raise ValueError("mock_api_path is required when use_mock_api=True")

            mock_api_path = Path(mock_api_path)
            if not mock_api_path.exists():
                raise ValueError(f"Mock API path does not exist: {mock_api_path}")

            print(f"Uploading mock API from {mock_api_path}...")

            # Upload all mock API files
            for file_path in mock_api_path.glob("*"):
                if file_path.is_file() and not file_path.name.startswith('test_'):
                    print(f"  Uploading {file_path.name}...")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    sandbox.files.write(f"/home/user/mock_api/{file_path.name}", content)

            # Install dependencies
            print("Installing mock API dependencies...")
            install_result = sandbox.run_code("!pip install fastapi uvicorn duckdb pydantic pyyaml requests -q")
            if install_result.error:
                print(f"Warning during installation: {install_result.error}")

            # Start mock API
            print("Starting mock API server...")
            start_api_script = """
import subprocess
import sys

process = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000'],
    cwd='/home/user/mock_api',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    start_new_session=True
)

print(f"Started mock API with PID: {process.pid}")
"""
            api_start_result = sandbox.run_code(start_api_script)
            if api_start_result.error:
                raise RuntimeError(f"Failed to start mock API: {api_start_result.error}")

            # Wait for API to be ready
            print("Waiting for API to be ready...")
            time.sleep(3)

            # Health check
            health_check_script = """
import requests
import json

try:
    response = requests.get('http://localhost:8000/health', timeout=5)
    result = {
        'success': response.status_code == 200,
        'status_code': response.status_code
    }
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({'success': False, 'error': str(e)}))
"""
            health_result = sandbox.run_code(health_check_script)
            health_output = ''.join(health_result.logs.stdout) if health_result.logs.stdout else ''
            if health_output:
                health_data = json.loads(health_output.strip())
                if not health_data.get('success'):
                    raise RuntimeError(f"Mock API health check failed: {health_data.get('error')}")

            print("Mock API is ready!")

        else:
            # Install requests dependency for driver
            print("Installing driver dependencies...")
            install_result = sandbox.run_code("!pip install requests -q")
            if install_result.error:
                print(f"Warning during installation: {install_result.error}")

        # Step 4: Generate and run test script
        print("Generating test script...")

        # Convert driver_name to class name (e.g., posthog_driver -> PosthogDriver)
        class_name = _to_class_name(driver_name)

        # Build credentials string
        creds_str = ", ".join([f"{k}='{v}'" for k, v in test_credentials.items()])

        # Generate comprehensive test script
        test_script = f"""
import sys
sys.path.insert(0, '/home/user')

from {driver_name} import {class_name}
import json

# Test tracking
tests_passed = 0
tests_failed = 0
errors = []

print("="*80)
print("DRIVER TEST SUITE: {driver_name}")
print("="*80)

try:
    # TEST 1: Driver initialization
    print("\\nTest 1: Driver Initialization")
    print("-" * 40)
    try:
        client = {class_name}(
            api_url='{test_api_url}',
            {creds_str}
        )
        print("✓ Driver initialized successfully")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Driver initialization failed: {{e}}")
        errors.append({{"test": "initialization", "error": str(e)}})
        tests_failed += 1
        raise  # Can't continue without a client

    # TEST 2: list_objects()
    print("\\nTest 2: list_objects()")
    print("-" * 40)
    try:
        objects = client.list_objects()

        if not isinstance(objects, list):
            raise TypeError(f"Expected list, got {{type(objects).__name__}}")

        if len(objects) == 0:
            print("⚠ Warning: No objects found (may be expected for some APIs)")

        print(f"✓ list_objects() returned {{len(objects)}} objects")
        if objects:
            print(f"  First few objects: {{', '.join(objects[:3])}}")

        tests_passed += 1
        first_object = objects[0] if objects else None

    except Exception as e:
        print(f"✗ list_objects() failed: {{e}}")
        errors.append({{"test": "list_objects", "error": str(e)}})
        tests_failed += 1
        first_object = None

    # TEST 3: get_fields()
    print("\\nTest 3: get_fields()")
    print("-" * 40)
    if first_object:
        try:
            schema = client.get_fields(first_object)

            if not isinstance(schema, dict):
                raise TypeError(f"Expected dict, got {{type(schema).__name__}}")

            if 'fields' not in schema:
                raise KeyError("Schema missing 'fields' key")

            field_count = len(schema.get('fields', []))
            print(f"✓ get_fields('{{first_object}}') returned schema with {{field_count}} fields")

            if field_count > 0:
                first_field = schema['fields'][0]
                print(f"  First field: {{first_field.get('name', 'unknown')}} ({{first_field.get('type', 'unknown')}})")

            tests_passed += 1

        except Exception as e:
            print(f"✗ get_fields() failed: {{e}}")
            errors.append({{"test": "get_fields", "error": str(e)}})
            tests_failed += 1
    else:
        print("⊘ Skipped (no objects available)")

    # TEST 4: read() with simple query
    print("\\nTest 4: read() with simple query")
    print("-" * 40)
    if first_object:
        try:
            # Try a simple query (implementation depends on driver)
            # For query-based drivers, use query language
            # For REST-based drivers, use endpoint notation

            # Attempt a simple read
            results = client.read(first_object, limit=5)

            if not isinstance(results, list):
                raise TypeError(f"Expected list, got {{type(results).__name__}}")

            print(f"✓ read('{{first_object}}') returned {{len(results)}} records")

            if results:
                print(f"  First record keys: {{', '.join(list(results[0].keys())[:5])}}")

            tests_passed += 1

        except Exception as e:
            print(f"✗ read() failed: {{e}}")
            errors.append({{"test": "read", "error": str(e)}})
            tests_failed += 1
    else:
        print("⊘ Skipped (no objects available)")

    # TEST 5: Error handling (invalid object)
    print("\\nTest 5: Error Handling (invalid object)")
    print("-" * 40)
    try:
        # Try to query a non-existent object
        try:
            client.get_fields("NonExistentObject12345")
            print("✗ Expected exception for invalid object, but none was raised")
            tests_failed += 1
            errors.append({{"test": "error_handling", "error": "No exception raised for invalid object"}})
        except Exception as expected_error:
            # Check if it's a proper driver exception (not a generic error)
            error_name = type(expected_error).__name__

            if 'Driver' in error_name or 'Error' in error_name:
                print(f"✓ Properly raised {{error_name}} for invalid object")
                tests_passed += 1
            else:
                print(f"⚠ Raised {{error_name}} (expected a custom driver exception)")
                print(f"  Error message: {{str(expected_error)[:100]}}")
                tests_passed += 1  # Still counts as pass, but with warning

    except Exception as e:
        print(f"✗ Error handling test failed: {{e}}")
        errors.append({{"test": "error_handling", "error": str(e)}})
        tests_failed += 1

except Exception as e:
    print(f"\\n✗ CRITICAL ERROR: {{e}}")
    errors.append({{"test": "critical", "error": str(e)}})

# Final summary
print("\\n" + "="*80)
print("TEST SUMMARY")
print("="*80)
print(f"Tests Passed: {{tests_passed}}")
print(f"Tests Failed: {{tests_failed}}")
print(f"Total Tests: {{tests_passed + tests_failed}}")

if tests_failed == 0:
    print("\\n✓ ALL TESTS PASSED")
else:
    print(f"\\n✗ {{tests_failed}} TEST(S) FAILED")
    print("\\nErrors:")
    for err in errors:
        print(f"  - {{err['test']}}: {{err['error']}}")

# Output JSON result for parsing
result = {{
    "tests_passed": tests_passed,
    "tests_failed": tests_failed,
    "total_tests": tests_passed + tests_failed,
    "errors": errors,
    "success": tests_failed == 0
}}

print("\\n" + "="*80)
print("JSON_RESULT_START")
print(json.dumps(result, indent=2))
print("JSON_RESULT_END")
"""

        # Step 5: Execute test script
        print("Executing test suite...")
        print("=" * 80)

        result = sandbox.run_code(
            test_script,
            envs={'PYTHONPATH': '/home/user'}
        )

        # Get output
        output = ''.join(result.logs.stdout) if result.logs.stdout else ''

        print(output)
        print("=" * 80)

        # Parse results
        if result.error:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "tests_passed": 0,
                "tests_failed": 0,
                "output": output,
                "errors": [f"Script execution failed: {result.error}"],
                "suggestions": [
                    "Check driver imports and dependencies",
                    "Verify driver class name matches convention",
                    "Ensure all required methods are implemented"
                ],
                "execution_time": execution_time,
                "sandbox_id": sandbox_id
            }

        # Extract JSON result from output
        tests_passed = 0
        tests_failed = 0
        errors = []
        suggestions = []

        try:
            # Find JSON result in output
            if 'JSON_RESULT_START' in output and 'JSON_RESULT_END' in output:
                json_start = output.index('JSON_RESULT_START') + len('JSON_RESULT_START')
                json_end = output.index('JSON_RESULT_END')
                json_str = output[json_start:json_end].strip()

                parsed_result = json.loads(json_str)
                tests_passed = parsed_result.get('tests_passed', 0)
                tests_failed = parsed_result.get('tests_failed', 0)
                errors = [err.get('error', 'Unknown error') for err in parsed_result.get('errors', [])]

            else:
                # Fallback: parse from text output
                if 'ALL TESTS PASSED' in output:
                    # Try to extract number from "Tests Passed: X"
                    import re
                    match = re.search(r'Tests Passed:\s*(\d+)', output)
                    if match:
                        tests_passed = int(match.group(1))
                else:
                    # Try to extract counts
                    import re
                    passed_match = re.search(r'Tests Passed:\s*(\d+)', output)
                    failed_match = re.search(r'Tests Failed:\s*(\d+)', output)

                    if passed_match:
                        tests_passed = int(passed_match.group(1))
                    if failed_match:
                        tests_failed = int(failed_match.group(1))

        except Exception as parse_error:
            print(f"Warning: Could not parse test results: {parse_error}")

        # Generate suggestions based on errors
        if tests_failed > 0:
            if any('initialization' in str(e).lower() for e in errors):
                suggestions.append("Check driver __init__ method and required parameters")
            if any('list_objects' in str(e).lower() for e in errors):
                suggestions.append("Verify list_objects() implementation and API endpoint")
            if any('get_fields' in str(e).lower() for e in errors):
                suggestions.append("Check get_fields() method and schema format")
            if any('read' in str(e).lower() for e in errors):
                suggestions.append("Verify read() method implementation and query handling")
            if any('import' in str(e).lower() or 'module' in str(e).lower()):
                suggestions.append("Ensure all required dependencies are installed")
        else:
            suggestions.append("All tests passed! Driver is ready for use.")

        execution_time = time.time() - start_time

        return {
            "success": tests_failed == 0,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "output": output,
            "errors": errors,
            "suggestions": suggestions,
            "execution_time": execution_time,
            "sandbox_id": sandbox_id
        }

    except Exception as e:
        execution_time = time.time() - start_time

        # Provide specific error messages
        error_msg = str(e)
        if 'E2B_API_KEY' in error_msg:
            suggestions = ["Set E2B_API_KEY environment variable"]
        elif 'timeout' in error_msg.lower():
            suggestions = ["E2B sandbox timed out - try again"]
        elif 'sandbox' in error_msg.lower():
            suggestions = ["E2B sandbox error - check E2B service status"]
        else:
            suggestions = ["Check error details and driver configuration"]

        return {
            "success": False,
            "tests_passed": 0,
            "tests_failed": 0,
            "output": "",
            "errors": [error_msg],
            "suggestions": suggestions,
            "execution_time": execution_time,
            "sandbox_id": sandbox_id
        }

    finally:
        # Clean up sandbox
        if sandbox:
            try:
                print(f"Cleaning up sandbox {sandbox_id}...")
                sandbox.kill()
                print("Sandbox cleaned up successfully")
            except Exception as cleanup_error:
                print(f"Warning: Error during sandbox cleanup: {cleanup_error}")


# Helper functions

def _normalize_pagination_style(style: str) -> str:
    """
    Normalize pagination style to known enum values.

    Maps various Claude outputs to standardized pagination types.
    """
    if not style:
        return "none"

    style_lower = str(style).lower().replace("-", "_").replace(" ", "_")

    # Known mappings
    STYLE_MAP = {
        "none": "none",
        "no": "none",
        "not_supported": "none",

        "offset": "offset",
        "limit_offset": "offset",
        "offset_based": "offset",

        "cursor": "cursor",
        "cursor_based": "cursor",
        "token": "cursor",
        "next_token": "cursor",

        "page": "page_number",
        "page_number": "page_number",
        "page_based": "page_number",
        "pagination": "page_number",

        "time": "time_based",
        "time_based": "time_based",
        "timestamp": "time_based",
        "date": "time_based",

        "time_range": "time_range",
        "date_range": "time_range",
        "range": "time_range",

        "parameter": "page_number",  # Common REST API pattern
        "query_parameter": "page_number",
    }

    # Try exact match
    if style_lower in STYLE_MAP:
        return STYLE_MAP[style_lower]

    # Try partial match
    for key, value in STYLE_MAP.items():
        if key in style_lower or style_lower in key:
            return value

    # Default fallback
    return "none"


def _to_class_name(driver_name: str) -> str:
    """Convert driver_name to ClassName format."""
    parts = driver_name.replace("_driver", "").split("_")
    return "".join(part.capitalize() for part in parts) + "Driver"


def _write_file(path: Path, content: str):
    """Write content to file."""
    path.write_text(content)


def _extract_todos(content: str, filename: str) -> List[Dict[str, Any]]:
    """Extract TODO markers from file content."""
    todos = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        if "TODO:" in line or "TODO " in line:
            # Extract TODO description
            todo_match = re.search(r"TODO:?\s*(.*)", line, re.IGNORECASE)
            if todo_match:
                description = todo_match.group(1).strip()
                todos.append({
                    "file": filename,
                    "line": i,
                    "description": description
                })

    return todos
