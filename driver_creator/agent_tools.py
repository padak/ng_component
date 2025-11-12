"""
Agent-based driver generation tools.

This module provides sub-agent orchestration for driver generation:
- Research Agent: Analyzes API documentation
- Generator Agent: Generates complete driver code
- Tester Agent: Tests driver in E2B and debugs issues
- Learning Agent: Extracts patterns and stores in mem0
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from mem0 import Memory
from datetime import datetime


# Session logging directory
CURRENT_SESSION_DIR = None

def init_session_logging():
    """Initialize logging directory for this driver generation session"""
    global CURRENT_SESSION_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    CURRENT_SESSION_DIR = Path("logs") / f"session_{timestamp}"
    CURRENT_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📝 Session logs: {CURRENT_SESSION_DIR}\n")
    return CURRENT_SESSION_DIR

def log_agent_interaction(agent_type: str, phase: str, content: dict):
    """
    Log agent prompt/response for debugging.

    Args:
        agent_type: 'research', 'generator', 'tester', 'fixer', 'learning'
        phase: 'input' or 'output'
        content: {'prompt': str, 'response': str, 'metadata': dict}
    """
    if not CURRENT_SESSION_DIR:
        return

    log_file = CURRENT_SESSION_DIR / f"{agent_type}_{phase}.jsonl"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent_type": agent_type,
        "phase": phase,
        **content
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Also write human-readable version
    if phase == 'input' and 'prompt' in content:
        readable_file = CURRENT_SESSION_DIR / f"{agent_type}_prompt.txt"
        with open(readable_file, "a") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {log_entry['timestamp']}\n")
            f.write(f"{'='*80}\n")
            f.write(content['prompt'])
            f.write(f"\n\n")

# Model mappings (short name → full ID)
MODEL_MAPPINGS = {
    'claude-sonnet-4-5': 'claude-sonnet-4-5-20250929',
    'claude-sonnet-4': 'claude-sonnet-4-20250514',
    'claude-haiku-4-5': 'claude-haiku-4-5-20251001',
    'claude-haiku-3-5': 'claude-3-5-haiku-20241022',
}

def get_model_id(model_name: str) -> str:
    """
    Get full model ID from short name or return as-is if already full ID.

    Args:
        model_name: Short name (e.g., 'claude-haiku-4-5') or full ID

    Returns:
        Full model ID (e.g., 'claude-haiku-4-5-20251001')
    """
    return MODEL_MAPPINGS.get(model_name, model_name)

def get_agent_model(agent_type: str, default_model: str = 'claude-sonnet-4-5') -> str:
    """
    Get optimal model for specific agent type.

    Cost optimization strategy:
    - Research Agent: Haiku (12x cheaper, fast research)
    - Generator Agent: Sonnet (quality code generation)
    - Tester Agent: Haiku (fast test iterations)
    - Learning Agent: Haiku (simple pattern extraction)

    Args:
        agent_type: 'research', 'generator', 'tester', 'learning'
        default_model: Override from CLAUDE_MODEL env var

    Returns:
        Full model ID
    """
    # Check for user override
    env_model = os.getenv('CLAUDE_MODEL')
    if env_model:
        default_model = env_model

    # Multi-model strategy for cost optimization
    model_strategy = {
        'research': 'claude-haiku-4-5',      # Fast API analysis
        'generator': default_model,           # Use user's preferred model for code quality
        'tester': 'claude-haiku-4-5',        # Fast test iteration
        'learning': 'claude-haiku-4-5',      # Simple pattern extraction
        'fixer': 'claude-haiku-4-5',         # Fast code fixes
    }

    model_name = model_strategy.get(agent_type, default_model)
    return get_model_id(model_name)

# Initialize mem0 for agent learning
def get_memory_client() -> Memory:
    """Get initialized mem0 Memory client"""
    return Memory()  # Uses default config with OpenAI


def prioritize_errors(errors: List[Dict]) -> List[Dict]:
    """
    Sort errors by priority (P0 = most critical).

    Priority levels:
    - P0: Import errors, syntax errors (block everything)
    - P1: Type errors in core methods (list_objects, get_fields)
    - P2: Test failures, runtime errors
    - P3: Style issues, warnings
    """
    def get_priority(error):
        error_str = str(error.get('error', '')).lower()
        test_name = str(error.get('test', '')).lower()

        # P0: Syntax and import errors
        if any(keyword in error_str for keyword in ['syntaxerror', 'importerror', 'modulenotfounderror', 'indentationerror']):
            return 0

        # P1: Core method type errors
        if 'list_objects' in test_name or 'get_fields' in test_name:
            if 'expected str instance' in error_str or 'typeerror' in error_str:
                return 1

        # P2: Other test failures
        if 'failed' in test_name or 'error' in error_str:
            return 2

        # P3: Everything else
        return 3

    return sorted(errors, key=get_priority)


def generate_driver_with_agents(
    api_name: str,
    api_url: str,
    output_dir: Optional[str] = None,
    max_retries: int = 7  # Increased from 3 - need more iterations for complex fixes
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

    # Initialize session logging
    session_dir = init_session_logging()


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

        # Log Research Agent input
        log_agent_interaction('research', 'input', {
            'prompt': research_prompt,
            'model': get_agent_model('research'),
            'api_name': api_name,
            'api_url': api_url
        })

        # Use prompt caching for system prompt (saves 90% on repeated calls)
        research_response = claude.messages.create(
            model=get_agent_model('research'),  # Haiku for fast, cheap research
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": research_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            }],
            system=[
                {
                    "type": "text",
                    "text": "You are a Research Agent specializing in API analysis. Return ONLY valid JSON.",
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        )

        research_text = research_response.content[0].text

        # Extract JSON from response (might have markdown code blocks)
        if "```json" in research_text:
            research_text = research_text.split("```json")[1].split("```")[0].strip()
        elif "```" in research_text:
            research_text = research_text.split("```")[1].split("```")[0].strip()

        research_data = json.loads(research_text)

        # Log Research Agent output
        log_agent_interaction('research', 'output', {
            'response': research_text,
            'research_data': research_data,
            'endpoints_found': len(research_data.get('endpoints', []))
        })

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
        # NEW APPROACH: Generate files one-by-one to avoid JSON parsing issues
        # This is more reliable and produces better quality code per file

        files_to_generate = [
            {
                "path": "client.py",
                "description": f"Main {class_name}Driver class with all core methods",
                "max_tokens": 4000
            },
            {
                "path": "__init__.py",
                "description": "Package initialization, exports",
                "max_tokens": 500
            },
            {
                "path": "exceptions.py",
                "description": "Custom exception hierarchy",
                "max_tokens": 1000
            },
            {
                "path": "README.md",
                "description": "Complete documentation with examples",
                "max_tokens": 2000
            },
            {
                "path": "examples/list_objects.py",
                "description": "Example: List all available objects",
                "max_tokens": 800
            },
            {
                "path": "tests/test_client.py",
                "description": "Unit tests for the driver",
                "max_tokens": 2000
            }
        ]

        files_dict = {}

        for file_info in files_to_generate:
            file_path = file_info["path"]
            description = file_info["description"]
            max_tokens = file_info["max_tokens"]

            print(f"     Generating {file_path}...")

            # Create file-specific prompt
            file_prompt = f"""Generate {file_path} for {api_name} driver.

**File Purpose:** {description}

**Research Data:**
```json
{json.dumps(research_data, indent=2)}
```

**Driver Class Name:** {class_name}Driver

**Requirements for this file:**
"""

            # Add specific requirements per file type
            if file_path == "client.py":
                file_prompt += f"""
- Class name: {class_name}Driver
- Methods: __init__, from_env, get_capabilities, list_objects, get_fields, query/read
- Include retry logic with exponential backoff
- Validate connection in __init__ (fail fast!)
- Match API type from research (REST/GraphQL/Database/etc.)
- If public API (no auth required), make api_key optional with default None
- Use requests.Session() for connection pooling
- Clear error messages with custom exceptions
"""
                file_prompt += """
**⚠️⚠️⚠️ CRITICAL REQUIREMENTS - READ THIS 3 TIMES BEFORE WRITING CODE ⚠️⚠️⚠️**

**🚨 COMMON MISTAKE TO AVOID 🚨**
DO NOT copy the research_data structure directly into list_objects()!
If research_data contains List[Dict], you MUST extract ONLY the 'name' field!

**⚠️ IF YOU RETURN List[Dict] FROM list_objects(), THE CODE WILL FAIL! ⚠️**

**BEFORE YOU WRITE ANY CODE:**
1. Read these requirements 3 times
2. Understand that list_objects() MUST return List[str] (list of strings)
3. If research_data has Dict objects, EXTRACT ONLY THE 'name' field
4. Do NOT return the entire dictionary structure

**Example: Extracting object names from research data**

If research_data['endpoints'] looks like:
```python
[
    {{"name": "forecast", "path": "/forecast", "method": "GET"}},
    {{"name": "marine", "path": "/marine", "method": "GET"}},
    {{"name": "air_quality", "path": "/air_quality", "method": "GET"}}
]
```

Then list_objects() should be:
```python
def list_objects(self) -> List[str]:
    \"\"\"Return list of available object names.\"\"\"
    # ✅ CORRECT - Extract ONLY the names as strings:
    return ['forecast', 'marine', 'air_quality']

    # ❌ WRONG - Do NOT return the full dictionaries:
    # return research_data['endpoints']  # This returns List[Dict]!

    # ❌ WRONG - Do NOT return dict objects:
    # return [{{"name": "forecast"}}, {{"name": "marine"}}]
```

**1. list_objects() signature (MUST FOLLOW EXACTLY):**
   ```python
   def list_objects(self) -> List[str]:
       \"\"\"Return list of object names (strings only).

       Returns:
           List[str]: List of available object names

       Example:
           >>> driver.list_objects()
           ['users', 'posts', 'comments']  # ✅ Strings only!
       \"\"\"
       # If API has no schema endpoint, hardcode known objects as STRINGS:
       return ['object1', 'object2', 'object3']  # ✅ Simple strings!

       # NEVER do this:
       # return [{{'name': 'object1'}}]  # ❌ WRONG - Dict objects!
   ```

**2. get_fields(object_name: str) signature:**
   ```python
   def get_fields(self, object_name: str) -> Dict[str, Any]:
       \"\"\"Return field schema for object.

       Args:
           object_name: Name of the object

       Returns:
           Dict[str, Any]: Field definitions with metadata
       \"\"\"
       return {{
           "field_name": {{
               "type": "string",
               "required": True,
               "nullable": False
           }}
       }}
   ```

**3. If API doesn't provide metadata:**
   - list_objects(): Return hardcoded list of endpoint names as STRINGS ONLY
   - get_fields(): Return empty dict {{}} or infer from sample data
   - Document this limitation in docstrings

**4. Extracting endpoint names from research_data:**
   ```python
   # research_data['endpoints'] is now simplified: [{{'name': 'forecast', 'path': '/forecast', 'method': 'GET'}}]
   # Extract just the names using list comprehension:
   endpoint_names = [ep['name'] for ep in research_data.get('endpoints', [])]
   # Returns: ['forecast', 'marine', 'air_quality']  # ✅ CORRECT - strings only!
   ```

**VALIDATION CHECKLIST (self-check before returning code):**
- [ ] Did you write `return [...]` with STRINGS ONLY in list_objects()?
- [ ] NOT `return [{...}]` with dicts in list_objects()?
- [ ] If research_data has dicts, did you EXTRACT only the 'name' field?
- [ ] list_objects() returns List[str] (NOT List[Dict], NOT Dict, NOT anything else)
- [ ] get_fields() returns Dict[str, Any]
- [ ] No import errors (all imports are valid)
- [ ] Proper indentation (no mixed tabs/spaces)

**FINAL CHECK BEFORE RETURNING:**
Open the code you generated and verify:
1. Find the list_objects() method
2. Look at the return statement
3. Confirm it returns a simple list like: ['name1', 'name2', 'name3']
4. NOT a list of dicts like: [{{'name': 'name1'}}, ...]
5. If you see {{}} braces in the return, YOU DID IT WRONG!

**If unsure, read CRITICAL REQUIREMENTS again from the top!**
""".format(class_name=class_name)

            elif file_path == "__init__.py":
                file_prompt += f"""
- Export {class_name}Driver
- Export all custom exceptions
- Set __version__ = "1.0.0"

**⚠️ CRITICAL:**
- Import from .client (NOT .driver)
- Proper indentation (4 spaces, no tabs)
- No trailing commas in single-item imports

Example:
```python
from .client import {class_name}Driver
from .exceptions import (
    DriverError,
    AuthenticationError
)
```
"""

            elif file_path == "exceptions.py":
                file_prompt += """
- Base: DriverError(Exception)
- Specific: AuthenticationError, ConnectionError, QuerySyntaxError, RateLimitError, ObjectNotFoundError
- Each exception should have helpful error messages
"""

            elif file_path == "README.md":
                file_prompt += f"""
- Overview of {api_name} driver
- Installation instructions
- Quick start example
- Authentication setup (if needed)
- Usage examples
- API reference
- Troubleshooting common issues
"""

            elif file_path.startswith("examples/"):
                file_prompt += f"""
- Complete working example
- Include imports
- Show how to initialize driver
- Demonstrate the specific functionality
- Add error handling
- Make it runnable as standalone script
"""

            elif file_path.startswith("tests/"):
                file_prompt += f"""
- Use pytest framework
- Test all core methods: __init__, list_objects, get_fields, query/read
- Mock API responses with unittest.mock
- Test error handling
- Test connection validation
- Include fixtures for setup/teardown
"""

            file_prompt += f"""

**Previous Learnings:**
{chr(10).join([f"- {m}" for m in memory_context]) if memory_context else "No previous learnings yet"}

Return ONLY the code for {file_path}. No JSON wrapper, no markdown code blocks.
Start directly with the code (or markdown for README).
"""

            try:

                # Log Generator Agent input
                log_agent_interaction('generator', 'input', {
                    'prompt': file_prompt,
                    'file_path': file_path,
                    'model': get_agent_model('generator')
                })

                # Use prompt caching - cache research_data and base instructions
                # This saves 90% on cost for files 2-6 (same research data)
                file_response = claude.messages.create(
                    model=get_agent_model('generator'),  # User's preferred model for code quality
                    max_tokens=max_tokens,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": file_prompt,
                                "cache_control": {"type": "ephemeral"}
                            }
                        ]
                    }],
                    system=[
                        {
                            "type": "text",
                            "text": "You are a Code Generator Agent. Return ONLY the requested file content, no wrappers.",
                            "cache_control": {"type": "ephemeral"}
                        }
                    ]
                )

                file_content = file_response.content[0].text.strip()

                # Clean up markdown code blocks if Claude added them anyway
                if file_content.startswith("```"):
                    # Remove opening ```python or ```markdown
                    lines = file_content.split('\n')
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    # Remove closing ```
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    file_content = '\n'.join(lines).strip()


                # Log Generator Agent output
                log_agent_interaction('generator', 'output', {
                    'file_path': file_path,
                    'code_length': len(file_content),
                    'response': file_content[:500]  # First 500 chars
                })

                files_dict[file_path] = file_content
                print(f"       ✓ {file_path} ({len(file_content)} chars)")

            except Exception as e:
                print(f"       ✗ Failed to generate {file_path}: {e}")
                # Continue with other files even if one fails
                continue

        print(f"   ✓ Code generation completed!")
        print(f"     - Files generated: {len(files_dict)}/{len(files_to_generate)}")

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

    # Step 3.5: Validate generated code BEFORE testing
    print(f"\n🔍 Step 3.5: Validating generated code...")

    validation_errors = []

    # Check client.py exists
    client_py_path = output_dir / "client.py"
    if client_py_path.exists():
        client_code = client_py_path.read_text()

        # Check 1: list_objects() returns List[str], not List[Dict]
        if 'def list_objects(self) -> List[str]:' in client_code:
            # Look for the return statement in list_objects
            import re
            # Find list_objects function
            match = re.search(r'def list_objects\(self\).*?(?=\n    def |\nclass |\Z)', client_code, re.DOTALL)
            if match:
                func_body = match.group(0)
                # Check for Dict return patterns
                if re.search(r"return \[{['\"]name['\"]:", func_body):
                    validation_errors.append({
                        "file": "client.py",
                        "issue": "list_objects() returns List[Dict] instead of List[str]",
                        "fix": "Extract only 'name' fields from dicts, e.g., return [obj['name'] for obj in objects]"
                    })
                    print(f"   ⚠️  VALIDATION ERROR: list_objects() returns Dict instead of str!")

        # Check 2: No obvious syntax errors
        try:
            compile(client_code, 'client.py', 'exec')
            print(f"   ✓ client.py syntax is valid")
        except SyntaxError as e:
            validation_errors.append({
                "file": "client.py",
                "issue": f"Syntax error: {e}",
                "fix": "Fix syntax error before testing"
            })
            print(f"   ⚠️  VALIDATION ERROR: Syntax error in client.py!")

    if validation_errors:
        print(f"\n⚠️  Found {len(validation_errors)} validation error(s) BEFORE testing")
        print(f"   These would cause test failures. Consider fixing before E2B tests.")
        # Don't block - still run tests, but warn user
    else:
        print(f"   ✓ Pre-test validation passed!")

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

                        # Analyze errors and generate fix
                        errors = test_results.get("errors", [])
                        if not errors:
                            print(f"   ⚠ No specific errors to fix - stopping here")
                            break

                        # Prioritize errors (fix critical ones first)
                        errors = prioritize_errors(errors)
                        print(f"   📋 Prioritized {len(errors)} error(s) (P0=critical → P3=minor)")
                        for i, err in enumerate(errors[:3], 1):  # Show top 3
                            priority = ['P0 🔴', 'P1 🟡', 'P2 🟢', 'P3 ⚪'][min(3, i-1)]
                            error_display = err.get('error', str(err))[:60] if isinstance(err, dict) else str(err)[:60]
                            test_name = err.get('test', 'unknown') if isinstance(err, dict) else 'unknown'
                            print(f"      {priority} {test_name}: {error_display}...")

                        print(f"   📋 Analyzing {len(errors)} error(s)...")

                        # Create fix prompt for Tester Agent
                        # Handle both dict and string error formats
                        error_lines = []
                        for err in errors:
                            if isinstance(err, dict):
                                test_name = err.get('test', 'unknown')
                                error_msg = err.get('error', 'unknown')
                                error_lines.append(f"- {test_name}: {error_msg}")
                            else:
                                # String error
                                error_lines.append(f"- {err}")
                        error_summary = "\n".join(error_lines)

                        # Read ALL files being tested to show Tester Agent current state
                        current_files_content = {}
                        # We need to identify which files have edits
                        # For now, read common files that are usually edited
                        common_files_to_check = ["client.py", "__init__.py", "exceptions.py", "tests/test_client.py"]

                        for file_to_check in common_files_to_check:
                            check_path = output_dir / file_to_check
                            if check_path.exists():
                                try:
                                    with open(check_path, 'r', encoding='utf-8') as f:
                                        current_files_content[file_to_check] = f.read()
                                except Exception as e:
                                    print(f"   ⚠ Could not read {file_to_check}: {e}")

                        # Build current code section for prompt
                        current_code_section = ""
                        for file_name, file_content in current_files_content.items():
                            current_code_section += f"""
**Current {file_name}:**
```python
{file_content}
```

"""

                        fix_prompt = f"""You are a Tester & Debugger Agent. Analyze test failures and suggest EXACT code edits.

**Driver:** {api_name}
**Test Results:** {tests_passed} passed, {tests_failed} failed

**CURRENT CODE (what's in the files NOW):**
{current_code_section}

**Errors:**
{error_summary}

**Test Output:**
{test_results.get('output', 'N/A')[:2000]}

**Your Task:**
1. READ the current code above carefully
2. FIND the exact lines causing the errors
3. Provide old_string that EXACTLY matches what's in the file (including indentation!)
4. Provide new_string with the fix

**Common Issues:**
- `list_objects()` should return `List[str]` (e.g., `["users", "posts"]`), NOT `List[Dict]`
- `get_fields()` should return field schema as Dict
- Connection errors: check API URL format
- Auth errors: check if API really needs auth

Return JSON:
```json
{{
    "analysis": "Root cause analysis...",
    "edits": [
        {{
            "file": "client.py",
            "issue": "list_objects() returns List[Dict] instead of List[str]",
            "old_string": "            return [{{'name': 'forecast', ...}}, {{'name': 'air-quality', ...}}]",
            "new_string": "            return ['forecast', 'air-quality']",
            "explanation": "Extract only object names as strings, not full dict objects"
        }}
    ]
}}
```

**CRITICAL for old_string:**
- Copy EXACT text from current code above (with correct whitespace)
- Include enough context to make it unique
- Match indentation precisely (count spaces!)
"""

                        try:
                            print(f"   🤖 Asking Tester Agent for fix suggestions...")


                            # Log Tester Agent input
                            log_agent_interaction('tester', 'input', {
                                'prompt': fix_prompt,
                                'errors': errors,
                                'iteration': iteration
                            })

                            # Use prompt caching for error analysis
                            fix_response = claude.messages.create(
                                model=get_agent_model('tester'),  # Haiku for fast test iteration
                                max_tokens=3000,
                                messages=[{
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": fix_prompt,
                                            "cache_control": {"type": "ephemeral"}
                                        }
                                    ]
                                }],
                                system=[
                                    {
                                        "type": "text",
                                        "text": "You are a Tester & Debugger Agent. Analyze errors and return ONLY valid JSON.",
                                        "cache_control": {"type": "ephemeral"}
                                    }
                                ]
                            )

                            fix_text = fix_response.content[0].text

                            # Extract JSON from response
                            if "```json" in fix_text:
                                fix_text = fix_text.split("```json")[1].split("```")[0].strip()
                            elif "```" in fix_text:
                                fix_text = fix_text.split("```")[1].split("```")[0].strip()

                            fix_data = json.loads(fix_text)

                            # Log Tester Agent output
                            log_agent_interaction('tester', 'output', {
                                'analysis': fix_data.get('analysis'),
                                'edits_suggested': len(fix_data.get('edits', [])),
                                'response': fix_text
                            })


                            print(f"   📝 Analysis: {fix_data.get('analysis', 'N/A')[:100]}...")

                            edits = fix_data.get('edits', [])
                            if not edits:
                                print(f"   ⚠ No specific edits suggested - stopping here")
                                break

                            print(f"   🔧 Edits to apply: {len(edits)}")

                            # Group edits by file
                            files_to_fix = {}
                            for edit in edits:
                                file = edit['file']
                                if file not in files_to_fix:
                                    files_to_fix[file] = []
                                files_to_fix[file].append(edit)

                            # Apply edits file by file
                            for file_to_fix, file_edits in files_to_fix.items():
                                print(f"   ✏️  Applying {len(file_edits)} edit(s) to {file_to_fix}...")

                                # Strip driver name prefix if present to avoid double nesting
                                driver_name = output_dir.name
                                if file_to_fix.startswith(f"{driver_name}/"):
                                    relative_file_path = file_to_fix[len(driver_name)+1:]
                                else:
                                    relative_file_path = file_to_fix

                                file_path = output_dir / relative_file_path

                                if not file_path.exists():
                                    print(f"       ✗ File not found: {file_path}")
                                    continue

                                # Read current file content
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    current_content = f.read()

                                # Apply each edit sequentially
                                modified_content = current_content
                                edit_success_count = 0

                                for i, edit in enumerate(file_edits, 1):
                                    old_string = edit['old_string']
                                    new_string = edit['new_string']
                                    issue = edit.get('issue', 'unknown')

                                    # Check if old_string exists in current content
                                    if old_string not in modified_content:
                                        print(f"       ⚠ Edit {i}: old_string not found")
                                        print(f"         Issue: {issue[:80]}")
                                        print(f"         Looking for: {old_string[:100]}...")

                                        # Try to find it with Tester Agent help
                                        print(f"       🔍 Asking Tester Agent to locate the code...")

                                        locate_prompt = f"""Find the exact code to fix in this file.

**File:** {file_to_fix}
**Issue:** {issue}
**Current file content:**
```python
{modified_content}
```

**What we're trying to fix:**
{edit.get('explanation', 'N/A')}

**Your task:**
1. Find the problematic code in the file above
2. Return the EXACT old_string (with correct indentation!)
3. Return the corrected new_string

Return JSON:
```json
{{
    "old_string": "exact code from file...",
    "new_string": "corrected code..."
}}
```
"""

                                        try:

                                            # Log Code Locator input
                                            log_agent_interaction('fixer', 'input', {
                                                'prompt': locate_prompt,
                                                'issue': issue,
                                                'file': file_to_fix
                                            })

                                            locate_response = claude.messages.create(
                                                model=get_agent_model('fixer'),  # Haiku for fast code location
                                                max_tokens=2000,
                                                messages=[{"role": "user", "content": locate_prompt}],
                                                system="You are a Code Locator. Return ONLY valid JSON with exact code strings."
                                            )

                                            locate_text = locate_response.content[0].text
                                            if "```json" in locate_text:
                                                locate_text = locate_text.split("```json")[1].split("```")[0].strip()
                                            elif "```" in locate_text:
                                                locate_text = locate_text.split("```")[1].split("```")[0].strip()

                                            locate_data = json.loads(locate_text)
                                            old_string = locate_data['old_string']
                                            new_string = locate_data['new_string']

                                            # Log Code Locator output
                                            log_agent_interaction('fixer', 'output', {
                                                'old_string_length': len(old_string),
                                                'new_string_length': len(new_string),
                                                'found': old_string in modified_content
                                            })



                                            if old_string not in modified_content:
                                                print(f"       ✗ Still not found - skipping edit {i}")
                                                continue

                                            print(f"       ✓ Located code successfully")

                                        except Exception as e:
                                            print(f"       ✗ Failed to locate code: {str(e)}")
                                            continue

                                    # Apply the edit (replace first occurrence only)
                                    modified_content = modified_content.replace(old_string, new_string, 1)
                                    edit_success_count += 1
                                    print(f"       ✓ Edit {i}/{len(file_edits)}: {issue[:60]}...")

                                # Write modified file back
                                if edit_success_count > 0:
                                    with open(file_path, 'w', encoding='utf-8') as f:
                                        f.write(modified_content)
                                    print(f"       ✅ {file_to_fix} updated ({edit_success_count}/{len(file_edits)} edits applied)")
                                else:
                                    print(f"       ✗ No edits applied to {file_to_fix}")

                            print(f"   ✅ Fixes applied, retrying tests...")

                        except Exception as e:
                            print(f"   ✗ Fix generation failed: {e}")
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

**CRITICAL: For endpoints array, provide MINIMAL structure:**
- Each endpoint should have ONLY: name (string), path (string), method (string)
- Do NOT include full schema, parameters, description, or response details in endpoints array
- Put detailed info in separate 'endpoint_details' field if needed for documentation

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
            "name": "forecast",
            "path": "/forecast",
            "method": "GET"
        }},
        {{
            "name": "marine",
            "path": "/marine",
            "method": "GET"
        }}
    ],
    "endpoint_details": {{
        "forecast": {{
            "description": "Get weather forecast",
            "required_params": ["latitude", "longitude"],
            "optional_params": ["hourly", "daily"],
            "response_schema": {{...}}
        }},
        "marine": {{
            "description": "Get marine weather data",
            "required_params": ["latitude", "longitude"],
            "optional_params": ["hourly", "daily"],
            "response_schema": {{...}}
        }}
    }},
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
