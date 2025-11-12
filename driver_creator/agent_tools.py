"""
Agent-based driver generation tools.

This module provides sub-agent orchestration for driver generation:
- Research Agent: Analyzes API documentation
- Generator Agent: Generates complete driver code
- Tester Agent: Tests driver in E2B and debugs issues
- Learning Agent: Extracts patterns and stores in mem0
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from mem0 import Memory

# Initialize mem0 for agent learning
def get_memory_client() -> Memory:
    """Get initialized mem0 Memory client"""
    return Memory()  # Uses default config with OpenAI


def generate_driver_with_agents(
    api_name: str,
    api_url: str,
    output_dir: Optional[str] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Generate a complete driver using specialized sub-agents.

    This is the NEW approach - uses LLM code generation with sub-agents
    instead of templates.

    Workflow:
    1. Research Agent → API analysis
    2. Generator Agent → Complete code generation
    3. Tester Agent → E2B testing + debugging loop
    4. Learning Agent → Extract patterns → mem0

    Args:
        api_name: Name of API (e.g., "Open-Meteo")
        api_url: Base URL for API (e.g., "https://api.open-meteo.com/v1")
        output_dir: Optional output directory
        max_retries: Max test-fix iterations

    Returns:
        {
            "success": True/False,
            "driver_name": "api_name_driver",
            "output_path": "/path/to/driver",
            "files_created": ["client.py", ...],
            "test_results": {...},
            "learnings_saved": 5,
            "iterations": 2
        }
    """
    import time
    import json
    import anthropic
    from pathlib import Path

    start_time = time.time()

    # Initialize memory client
    memory = get_memory_client()
    agent_id = "driver_creator_agent"

    # Initialize Claude client for sub-agents
    claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Setup output directory
    if output_dir is None:
        output_dir = Path("generated_drivers") / f"{api_name.lower().replace(' ', '_').replace('-', '_')}_driver"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f"🚀 Agent-Based Driver Generation for {api_name}")
    print("=" * 80)

    # Step 1: Retrieve relevant memories from past generations
    print("\n🧠 Step 1: Retrieving relevant memories from past generations...")
    try:
        memories = memory.search(
            f"How to generate driver for API similar to {api_name}? Patterns, auth, testing.",
            user_id=agent_id,
            limit=5
        )
        memory_context = []
        if memories and len(memories) > 0:
            for mem in memories:
                if isinstance(mem, dict):
                    memory_context.append(mem.get('memory', mem.get('text', str(mem))))
                else:
                    memory_context.append(str(mem))
            print(f"   ✓ Found {len(memory_context)} relevant memories")
        else:
            memory_context = []
            print(f"   ℹ No previous memories found (this is the first driver)")
    except Exception as e:
        print(f"   ⚠ Could not retrieve memories: {e}")
        memory_context = []

    # Step 2: Launch Research Agent
    print("\n📚 Step 2: Launching Research Agent...")
    print(f"   Analyzing {api_url}...")

    research_prompt = RESEARCH_AGENT_PROMPT.format(
        api_name=api_name,
        api_url=api_url,
        docs_url=api_url,
        memories="\n".join([f"- {m}" for m in memory_context]) if memory_context else "No previous learnings yet"
    )

    try:
        research_response = claude.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{"role": "user", "content": research_prompt}],
            system="You are a Research Agent specializing in API analysis. Return ONLY valid JSON."
        )

        research_text = research_response.content[0].text

        # Extract JSON from response (might have markdown code blocks)
        if "```json" in research_text:
            research_text = research_text.split("```json")[1].split("```")[0].strip()
        elif "```" in research_text:
            research_text = research_text.split("```")[1].split("```")[0].strip()

        research_data = json.loads(research_text)
        print(f"   ✓ Research completed!")
        print(f"     - API Type: {research_data.get('api_type', 'Unknown')}")
        print(f"     - Auth Required: {research_data.get('requires_auth', 'Unknown')}")
        print(f"     - Endpoints: {len(research_data.get('endpoints', []))}")

    except Exception as e:
        print(f"   ✗ Research Agent failed: {e}")
        return {
            "success": False,
            "error": "RESEARCH_FAILED",
            "message": f"Research Agent failed: {str(e)}",
            "execution_time": time.time() - start_time
        }

    # Step 3: Launch Generator Agent
    print("\n🔧 Step 3: Launching Generator Agent...")
    print(f"   Generating complete driver code...")

    class_name = "".join([word.capitalize() for word in api_name.replace("-", " ").replace("_", " ").split()])

    generator_prompt = GENERATOR_AGENT_PROMPT.format(
        class_name=class_name,
        api_name=api_name,
        research_data=research_data,
        research_json=json.dumps(research_data, indent=2),
        memories="\n".join([f"- {m}" for m in memory_context]) if memory_context else "No previous learnings yet"
    )

    try:
        # Modified: Request markdown format instead of JSON to avoid escaping issues
        generator_system = """You are a Code Generator Agent. Generate COMPLETE, working Python code.

Return each file as a markdown code block with format:
### FILE: path/to/file.py
```python
# file content here
```

Example:
### FILE: client.py
```python
class Driver:
    pass
```

### FILE: __init__.py
```python
from .client import Driver
```
"""

        generator_response = claude.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            messages=[{"role": "user", "content": generator_prompt}],
            system=generator_system
        )

        generator_text = generator_response.content[0].text

        # Parse response - Claude might return JSON or markdown
        files_dict = {}
        import re

        # Save raw output for debugging
        debug_file = output_dir / "generator_output.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(generator_text)

        # Try JSON format first (Claude often returns JSON anyway)
        if "```json" in generator_text or generator_text.strip().startswith("{"):
            try:
                # Extract JSON from code block if present
                if "```json" in generator_text:
                    json_text = generator_text.split("```json")[1].split("```")[0].strip()
                elif "```" in generator_text:
                    json_text = generator_text.split("```")[1].split("```")[0].strip()
                else:
                    json_text = generator_text.strip()

                # Parse JSON
                data = json.loads(json_text)
                files_dict = data.get("files", {})
                print(f"   ✓ Parsed {len(files_dict)} files from JSON format")
            except json.JSONDecodeError as e:
                print(f"   ⚠ JSON parsing failed: {e}")
                print(f"   Trying markdown format...")

        # If JSON failed, try markdown format
        if not files_dict:
            # Pattern: ### FILE: path\n```language\ncode```
            file_pattern = r'###\s*FILE:\s*(.+?)\n```(?:\w+)?\n(.*?)\n```'
            matches = re.findall(file_pattern, generator_text, re.DOTALL)

            for file_path, content in matches:
                file_path = file_path.strip()
                files_dict[file_path] = content.strip()

            if files_dict:
                print(f"   ✓ Parsed {len(files_dict)} files from markdown format")

        if not files_dict:
            print(f"   ⚠ Could not parse any files from output")
            print(f"   Debug output saved to: {debug_file}")

        print(f"   ✓ Code generation completed!")
        print(f"     - Files generated: {len(files_dict)}")

        # Write files to disk
        files_created = []
        for file_path, content in files_dict.items():
            full_path = output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            files_created.append(str(file_path))
            print(f"     ✓ {file_path}")

    except Exception as e:
        print(f"   ✗ Generator Agent failed: {e}")
        return {
            "success": False,
            "error": "GENERATION_FAILED",
            "message": f"Generator Agent failed: {str(e)}",
            "research_data": research_data,
            "execution_time": time.time() - start_time
        }

    # Step 4: Launch Tester Agent (with retry loop)
    print(f"\n🧪 Step 4: Launching Tester Agent (max {max_retries} iterations)...")

    # Import test function
    from tools import test_driver_in_e2b

    test_results = None
    iteration = 0
    all_tests_passed = False

    # Check if E2B is available
    if not os.getenv("E2B_API_KEY"):
        print("   ⚠ E2B_API_KEY not set - skipping E2B testing")
        print("   ℹ Driver generated successfully (not tested)")
    else:
        # Test + Fix loop
        for iteration in range(1, max_retries + 1):
            print(f"\n   Iteration {iteration}/{max_retries}:")
            print(f"   Running E2B tests...")

            try:
                test_results = test_driver_in_e2b(
                    driver_path=str(output_dir),
                    driver_name=output_dir.name,
                    test_api_url=research_data.get("base_url"),
                    use_mock_api=False
                )

                tests_passed = test_results.get("tests_passed", 0)
                tests_failed = test_results.get("tests_failed", 0)

                print(f"   ✓ Tests completed: {tests_passed} passed, {tests_failed} failed")

                if test_results.get("success") and tests_failed == 0:
                    all_tests_passed = True
                    print(f"   ✅ All tests passed!")
                    break
                else:
                    print(f"   ✗ Tests failed")
                    if iteration < max_retries:
                        print(f"   🔧 Launching fix iteration...")
                        # TODO: Implement fix logic with Tester Agent
                        print(f"   ⚠ Fix loop not yet implemented - stopping here")
                        break
                    else:
                        print(f"   ✗ Max retries reached")

            except Exception as e:
                print(f"   ✗ Testing failed: {e}")
                test_results = {"success": False, "error": str(e)}
                break

    # Step 5: Launch Learning Agent (save learnings to mem0)
    print(f"\n💡 Step 5: Launching Learning Agent...")
    print(f"   Extracting learnings from generation process...")

    try:
        generation_process = {
            "files_generated": files_created,
            "iterations": iteration,
            "test_passed": all_tests_passed
        }

        learning_result = extract_learnings_to_mem0(
            api_name=api_name,
            research_data=research_data,
            generation_process=generation_process,
            test_results=test_results or {}
        )

        print(f"   ✓ Saved {learning_result.get('learnings_saved', 0)} learnings to mem0")
        for lesson in learning_result.get('lessons', []):
            print(f"     - {lesson}")

    except Exception as e:
        print(f"   ⚠ Learning Agent failed: {e}")
        learning_result = {"learnings_saved": 0, "lessons": []}

    execution_time = time.time() - start_time

    print("\n" + "=" * 80)
    if all_tests_passed:
        print(f"✅ Driver generation completed successfully in {execution_time:.1f}s!")
    else:
        print(f"⚠️  Driver generated but tests incomplete in {execution_time:.1f}s")
    print("=" * 80)

    return {
        "success": all_tests_passed if test_results else True,
        "driver_name": output_dir.name,
        "output_path": str(output_dir),
        "files_created": files_created,
        "research_data": research_data,
        "test_results": test_results,
        "learning_result": learning_result if 'learning_result' in locals() else {},
        "iterations": iteration,
        "execution_time": execution_time
    }


def extract_learnings_to_mem0(
    api_name: str,
    research_data: Dict[str, Any],
    generation_process: Dict[str, Any],
    test_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract learnings from driver generation and store in mem0.

    Args:
        api_name: API name
        research_data: Research agent output
        generation_process: What was generated and how
        test_results: E2B test results

    Returns:
        {
            "learnings_saved": 3,
            "lessons": [
                "Public APIs don't need fake API keys",
                "Use base_url from research for testing",
                ...
            ]
        }
    """

    memory = get_memory_client()
    agent_id = "driver_creator_agent"

    # Build conversation representing the learning
    messages = []

    # Add context about what we did
    messages.append({
        "role": "user",
        "content": f"I generated a driver for {api_name} API ({research_data.get('base_url')})"
    })

    # Add what we learned from tests
    if not test_results.get("success"):
        errors = test_results.get("errors", [])
        messages.append({
            "role": "assistant",
            "content": f"The tests failed with these errors: {errors}"
        })

        # Add the fix
        messages.append({
            "role": "user",
            "content": "How did you fix it?"
        })

        messages.append({
            "role": "assistant",
            "content": f"I fixed it by: {generation_process.get('fixes_applied', 'investigating the errors')}"
        })

    # Add general learnings
    messages.append({
        "role": "user",
        "content": "What should we remember for next time?"
    })

    # Extract patterns
    patterns = []

    # Pattern 1: Auth detection
    if not research_data.get("requires_auth"):
        patterns.append(f"{api_name} is a public API - no authentication needed")

    # Pattern 2: Testing approach
    if research_data.get("base_url"):
        patterns.append(f"For public APIs, use real URL ({research_data['base_url']}) in tests, not localhost")

    # Pattern 3: API patterns
    if research_data.get("api_type"):
        patterns.append(f"{api_name} follows {research_data['api_type']} pattern")

    messages.append({
        "role": "assistant",
        "content": " ".join(patterns)
    })

    # Save to mem0
    result = memory.add(
        messages,
        user_id=agent_id,
        metadata={
            "api_name": api_name,
            "category": "driver_generation",
            "success": test_results.get("success", False)
        }
    )

    return {
        "learnings_saved": len(patterns),
        "lessons": patterns,
        "mem0_result": result
    }


# Prompt templates for sub-agents

RESEARCH_AGENT_PROMPT = """
You are a Research Agent specializing in API analysis for driver generation.

Your mission: Deeply understand the target API to enable perfect driver generation.

**Input:**
- API Name: {api_name}
- Base URL: {api_url}
- Documentation URL: {docs_url}

**Your Analysis Steps:**

1. **Fetch Documentation**
   - GET the base URL
   - Look for /docs, /api-docs, /swagger, /openapi
   - Read any README or documentation

2. **Identify API Type**
   - REST API (JSON over HTTP)
   - GraphQL (queries)
   - gRPC (protobuf)
   - Database (SQL, NoSQL)
   - SOAP (XML)
   - WebSocket
   - File-based (S3, CSV)

3. **Authentication Analysis**
   - Does it need auth? (Try calling without credentials)
   - Type: API key, OAuth2, Bearer token, Basic auth, None
   - How is it passed? (Header, Query param, Body)
   - Key name: (api_key, token, authorization, etc.)

4. **Discover Endpoints/Objects**
   - List all available endpoints
   - For each: method, path, parameters, response schema
   - Required vs optional parameters
   - Example requests/responses

5. **Rate Limits & Quotas**
   - Requests per second/minute/hour
   - How limits are communicated (headers?)
   - Retry-After support?

6. **Error Handling**
   - HTTP status codes used
   - Error response format
   - Common error scenarios

7. **Pagination Pattern**
   - None (small datasets)
   - Offset/Limit (SQL-style)
   - Cursor-based (next_token)
   - Page numbers
   - Time-based

**Output Format:**

Return structured JSON:
```json
{{
    "api_name": "...",
    "api_type": "REST|GraphQL|Database|gRPC|...",
    "base_url": "...",
    "requires_auth": true|false,
    "auth_type": "api_key|oauth2|bearer|basic|none",
    "auth_location": "header|query|body",
    "auth_key_name": "api_key|authorization|...",
    "endpoints": [
        {{
            "name": "get_forecast",
            "path": "/forecast",
            "method": "GET",
            "description": "Get weather forecast",
            "required_params": ["latitude", "longitude"],
            "optional_params": ["hourly", "daily"],
            "response_schema": {{...}}
        }}
    ],
    "rate_limits": {{
        "per_second": 10,
        "per_minute": 100,
        "headers": ["X-RateLimit-Remaining"]
    }},
    "pagination": "none|offset|cursor|page|time",
    "error_codes": [401, 403, 404, 429, 500],
    "notes": [
        "Any important observations",
        "Special patterns or quirks"
    ],
    "confidence": 0.9
}}
```

**Previous Learnings (from mem0):**
{memories}

Now, analyze {api_name}!
"""

GENERATOR_AGENT_PROMPT = """
You are a Code Generator Agent specializing in driver implementation.

Your mission: Generate a COMPLETE, WORKING driver following Driver Design v2.0.

**Input:**
- Research Data: {research_data}
- Driver Design v2.0 Specification
- Example Drivers (Salesforce, PostgreSQL)
- Memories from past generations

**Your Job:**

Generate these files:

1. **client.py** (main driver, ~500-800 lines):
   - Class: {class_name}Driver
   - __init__(api_url, api_key=None, ...)
   - from_env() classmethod
   - get_capabilities() → DriverCapabilities
   - list_objects() → List[str]
   - get_fields(object_name) → Dict[str, Any]
   - read() or query() depending on API type
   - _api_call() with retry logic
   - _validate_connection() (fail fast!)
   - Error handling with custom exceptions

2. **__init__.py** (package):
   - Export {class_name}Driver
   - Export custom exceptions
   - __version__ = "1.0.0"

3. **exceptions.py** (error hierarchy):
   - DriverError (base)
   - AuthenticationError
   - ConnectionError
   - QuerySyntaxError
   - RateLimitError
   - ObjectNotFoundError
   - etc.

4. **README.md** (documentation):
   - Overview
   - Installation
   - Quick Start
   - Authentication
   - Examples
   - API Reference
   - Troubleshooting

5. **examples/** (working examples):
   - list_objects.py
   - query_data.py
   - error_handling.py

6. **tests/test_client.py** (unit tests):
   - Test initialization
   - Test list_objects
   - Test get_fields
   - Test error handling
   - Mock API responses

**Key Principles:**

1. **Adapt to API Type**
   - REST: Use requests, call_endpoint()
   - GraphQL: Use query strings
   - Database: Use connection pools
   - Public API: No api_key required!

2. **Fail Fast**
   - Validate connection in __init__
   - Check credentials immediately
   - Clear error messages

3. **Discovery-First**
   - list_objects() must work
   - get_fields() must return schema
   - No hardcoded schemas!

4. **Error Handling**
   - Catch specific exceptions
   - Retry on rate limits (429)
   - Exponential backoff
   - Clear error messages

5. **Match API Patterns**
   - If public API → no api_key!
   - If no /health → try main endpoint
   - If no pagination → don't add it!

**Research Data:**
```json
{research_json}
```

**Previous Learnings:**
{memories}

**Example Structure (Salesforce):**
```python
class SalesforceDriver:
    def __init__(self, api_url: str, api_key: str, ...):
        self.api_url = api_url
        self.api_key = api_key
        self.session = requests.Session()
        self._validate_connection()  # Fail fast!

    def list_objects(self) -> List[str]:
        # Discovery implementation
        ...
```

Now, generate COMPLETE driver for {api_name}!

Return each file as:
```json
{{
    "files": {{
        "client.py": "...complete code...",
        "__init__.py": "...complete code...",
        "exceptions.py": "...complete code...",
        "README.md": "...complete markdown...",
        "examples/list_objects.py": "...complete code...",
        "tests/test_client.py": "...complete code..."
    }}
}}
```
"""

TESTER_AGENT_PROMPT = """
You are a Testing & Debugging Agent specializing in driver validation.

Your mission: Test the generated driver and fix any issues.

**Input:**
- Generated Driver Code
- E2B Test Results
- Error Messages

**Your Job:**

1. **Analyze Test Results**
   - Which tests passed?
   - Which tests failed?
   - What are the error messages?
   - What is the root cause?

2. **Identify Patterns**
   - Connection errors → check URLs
   - Auth errors → check credentials
   - 404 errors → check endpoints
   - Rate limits → add retries
   - Schema errors → fix discovery

3. **Generate Fixes**
   - Specific code changes
   - Line-by-line diffs
   - Explanation of fix

4. **Validate Fix**
   - Will this fix the issue?
   - Are there side effects?
   - Should we add tests?

**Test Results:**
```json
{test_results}
```

**Error Analysis:**

Error: {error_message}

Root Cause: Analyze...

Fix: Provide code...

**Previous Similar Issues:**
{memories}

Now, debug and fix!
"""

LEARNING_AGENT_PROMPT = """
You are a Learning Agent specializing in pattern extraction.

Your mission: Extract reusable lessons from driver generation process.

**Input:**
- API Name: {api_name}
- Research Data: {research_data}
- Generation Process: {process}
- Test Results: {test_results}
- Iterations: {iterations}

**Your Job:**

Extract learnings in these categories:

1. **API Patterns**
   - "{api_name} is a public/private API"
   - "{api_name} uses REST/GraphQL/..."
   - "{api_name} has no rate limits"

2. **Authentication Patterns**
   - "Public APIs don't need api_key parameter"
   - "OAuth2 APIs need token refresh"
   - "Bearer tokens go in Authorization header"

3. **Testing Patterns**
   - "Public APIs: use real URL for tests"
   - "Mock APIs: use localhost:8000"
   - "No /health endpoint: try main endpoint"

4. **Error Patterns**
   - "Connection refused → check test_api_url"
   - "404 on /health → ignore and continue"
   - "429 rate limit → add exponential backoff"

5. **Code Patterns**
   - "Field discovery: try /schema then /sample"
   - "Pagination: check response for 'next' token"
   - "Errors: always provide 'details' dict"

**Output Format:**

Return lessons as clear, actionable statements:

```json
{{
    "lessons": [
        "For {api_name}-like APIs (public, REST), don't require api_key",
        "When testing public APIs, use base_url from research_data",
        "If API has no /health, check main endpoint instead",
        ...
    ],
    "patterns": {{
        "api_type": "public_rest",
        "auth": "none",
        "testing": "use_real_url"
    }},
    "confidence": 0.9
}}
```

These lessons will be saved to mem0 for future driver generations!

Now, extract learnings!
"""
