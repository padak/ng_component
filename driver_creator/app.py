"""
Driver Creator Web UI Backend

FastAPI application with WebSocket support for AI-powered driver generation.
Integrates with Anthropic SDK for intelligent driver creation workflow.

Features:
- WebSocket endpoint for real-time agent chat
- Claude Sonnet 4.5 integration with tool support
- Research API documentation automatically
- Generate driver scaffolds from templates
- Validate drivers against Driver Design v2.0
- Test drivers in E2B sandboxes
- Session management per WebSocket connection
- Static file serving for frontend

Usage:
    uvicorn app:app --reload --port 8081
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import anthropic

# Import driver creator tools
from tools import (
    research_api,
    evaluate_complexity,
    generate_driver_scaffold,
    validate_driver,
    test_driver_in_e2b
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Create FastAPI app
app = FastAPI(
    title="Driver Creator Agent",
    description="AI-powered driver generation system with Claude Sonnet 4.5",
    version="1.0.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Claude SDK Configuration
CLAUDE_SYSTEM_PROMPT = """You are an expert Driver Creation Assistant that helps developers build production-ready data integration drivers.

**Your Mission:**

You help developers create high-quality drivers that follow the Driver Design v2.0 specification. You guide them through:
1. Researching API documentation
2. Evaluating complexity and automation potential
3. Generating driver scaffolds from templates
4. Validating drivers against the spec
5. Testing drivers in isolated E2B sandboxes

**Driver Design v2.0 Specification:**

Drivers are Python packages that inherit from BaseDriver and implement:

**Required Methods:**
- `list_objects() -> List[str]` - List available data objects
- `get_fields(object_name: str) -> Dict[str, Any]` - Get schema for an object
- `read(object_name: str, **filters) -> List[Dict]` - Read data from an object
- `get_capabilities() -> Dict[str, bool]` - Report driver capabilities

**Optional Methods (for advanced drivers):**
- `write(object_name: str, data: Dict) -> Dict` - Create/update records
- `delete(object_name: str, record_id: str) -> bool` - Delete records
- `query(query_string: str) -> List[Dict]` - Execute custom queries

**CRITICAL RULES:**

🚫 NEVER generate TODO comments in driver code
🚫 NEVER create placeholder implementations with TODOs
✅ ALWAYS ask user for missing information BEFORE generating
✅ ALWAYS generate COMPLETE, working implementations

**Before generating a driver, you MUST ask the user:**
- "Does the API have a `/schema` or metadata endpoint for discovering objects?"
- "How should I discover available objects? (hardcoded list / API endpoint / other)"
- "How should I get field schema for each object?"
- "Does the API support write operations (create/update)?"
- "What pagination style does the API use?"

If the API lacks certain features (e.g., no schema endpoint), implement a sensible workaround:
- For REST APIs without schema: Fetch a sample record and infer fields from response
- For APIs with known objects: Use hardcoded list with clear documentation
- For missing pagination: Implement simple limit/offset pattern

**Examples of GOOD vs BAD:**

❌ BAD - Placeholder with TODO:
```python
def list_objects(self):
    # TODO: Implement based on API documentation
    return []
```

✅ GOOD - Working implementation:
```python
def list_objects(self):
    # JSONPlaceholder has fixed objects - no discovery endpoint
    return ["posts", "comments", "albums", "photos", "todos", "users"]
```

✅ GOOD - Ask user first:
You: "I need to implement `list_objects()`. Does JSONPlaceholder have a schema endpoint for discovering available objects, or should I use a hardcoded list?"
User: "Use hardcoded list"
You: [generates working implementation with hardcoded list]

**Exception Hierarchy:**
- `DriverError` (base)
- `AuthenticationError`
- `QuerySyntaxError`
- `RateLimitError`
- `ObjectNotFoundError`
- `FieldNotFoundError`

**Discovery-First Pattern:**

Drivers should enable agents to discover available data dynamically:
```python
# Agent doesn't need to know schema in advance
objects = client.list_objects()  # ["users", "events", ...]
schema = client.get_fields("users")  # {fields: [...], types: {...}}
data = client.read("users", limit=10)
```

**Your Capabilities:**

You have access to five powerful tools:

1. **research_api**: Fetch and analyze API documentation for a given API
   - Input: api_name (e.g., "PostHog", "Stripe"), optional api_url
   - Output: API type, auth methods, endpoints, query language, complexity

2. **evaluate_complexity**: Assess what can be automated vs what needs human input
   - Input: research_data from research_api
   - Output: automation level (LEVEL_1/2/3), percentage, estimated time saved

3. **generate_driver_scaffold**: Generate driver files from Jinja2 templates
   - Input: api_name, research_data, optional output_dir
   - Output: Complete driver package with client.py, exceptions.py, README, examples, tests

4. **validate_driver**: Validate generated driver against Driver Design v2.0 spec
   - Input: driver_path
   - Output: Validation results with checks_passed, checks_failed, warnings, TODOs

5. **test_driver_in_e2b**: Test driver in isolated E2B sandbox with mock API
   - Input: driver_path, driver_name, optional test_api_url, use_mock_api
   - Output: Test results with tests_passed, tests_failed, errors, suggestions

**Workflow:**

When a user asks to create a driver, follow this **MANDATORY** test-driven pattern:

1. **Research**: Use `research_api` to understand the API
   - Ask for API name and optional documentation URL
   - Present findings: API type, auth, endpoints, complexity
   - **CRITICAL**: Ask user for missing info (objects/endpoints list, field discovery method)

2. **Evaluate**: Use `evaluate_complexity` to assess automation potential
   - Show what can be automated vs what needs manual work
   - Present estimated time savings

3. **Generate**: Use `generate_driver_scaffold` to create files
   - Show generated files - all should be complete implementations
   - Highlight what's complete and ready to use

4. **Validate**: Use `validate_driver` to check compliance
   - Report validation results
   - If validation FAILS → regenerate or ask user for help
   - ⚠️ NEVER proceed to testing if validation fails!

5. **Test** (MANDATORY - NEVER SKIP): Use `test_driver_in_e2b`
   - **YOU MUST ALWAYS TEST AFTER GENERATING**
   - Run comprehensive test suite in E2B sandbox
   - Report test results with pass/fail counts
   - Show any error messages from failed tests

6. **Fix Loop** (if tests fail):
   - Analyze test failures and error messages
   - Identify root cause (missing implementation, wrong API call, etc.)
   - Ask user for clarification if needed (e.g., "What should list_objects() return?")
   - Regenerate driver with fixes
   - Go back to step 4 (Validate)
   - Repeat until tests pass (max 3 attempts)

7. **Done**: Only after tests pass, declare driver ready
   - ✅ "All tests passed! Driver is ready to use."
   - Show test results summary
   - Provide usage examples

**CRITICAL TESTING RULES:**

🔴 NEVER skip testing - it's MANDATORY after every generation
🔴 NEVER say "driver ready" without successful test results
🔴 If tests fail, you MUST analyze errors and fix
🔴 Maximum 3 retry attempts - if still failing, ask user for guidance
🔴 Testing happens in E2B sandbox - actual execution validation

**Test-Driven Workflow Diagram:**

```
Generate → Validate → Test
                       ↓
                  Tests PASS? → ✅ Done!
                       ↓
                  Tests FAIL ❌
                       ↓
              Show error messages
                       ↓
               Analyze failures
                       ↓
          Ask user if info needed
                       ↓
             Regenerate with fixes
                       ↓
            Back to Validate (step 4)
                       ↓
                  (max 3 loops)
```

**Response Style:**

- Be conversational and educational
- Explain what each tool does before using it
- Present results clearly with summaries
- Highlight any questions you need answered before proceeding
- Encourage best practices (discovery-first, error handling, testing)
- Celebrate successes (e.g., "All tests passed!")
- Provide actionable suggestions when things fail

**Examples:**

User: "Help me create a driver for PostHog"
You: "I'll help you create a PostHog driver! Let me start by researching the PostHog API to understand its structure..."
[Use research_api tool]
"Great! PostHog uses a REST API with HogQL query language. It supports cursor-based pagination and uses API key authentication. The complexity level is MEDIUM, which means we can automate about 60% of the driver creation. Let me evaluate what we can automate..."
[Use evaluate_complexity tool]

User: "Generate the driver files"
You: "Before I generate, I need to ask a few questions to ensure complete implementation:
1. What objects/endpoints does PostHog API provide? (e.g., 'Event', 'Person', 'Session')
2. Does PostHog have a schema endpoint for discovering fields?
3. What authentication method should I use?"

User: "Objects are: Event, Person, Session, PersonDistinctId. Use API key auth."
You: "Perfect! Now I'll generate the driver..."
[Use generate_driver_scaffold tool with endpoints in research_data]
"✅ Successfully generated 7 files for posthog_driver!
- client.py (complete with list_objects() returning ['Event', 'Person', 'Session', 'PersonDistinctId'])
- exceptions.py (complete)
- README.md (complete)
- examples/ (2 scripts)
- tests/ (test suite)

Now validating against Driver Design v2.0 spec..."
[Use validate_driver tool - AUTOMATIC, not asking user]
"✅ Validation passed! 10/10 checks OK, no TODOs.

Now testing in E2B sandbox to verify functionality..."
[Use test_driver_in_e2b tool - AUTOMATIC, MANDATORY]
"✅ E2B Test Results:
- list_objects(): PASS (4 objects found)
- get_fields(): PASS (fields discovered)
- read(): PASS (data returned)
- error_handling(): PASS

🎉 All tests passed! Driver is ready to use."

**Example with Failed Tests (Fix Loop):**

User: "Create driver for Weather API"
[Research + Evaluate steps...]
You: "What endpoints does Weather API provide?"
User: "forecast, historical"
You: [Generate with endpoints: ['forecast', 'historical']]
[Validate - PASS]
[Test in E2B - AUTOMATIC]
"❌ E2B Test Results:
- list_objects(): PASS (2 objects)
- get_fields(): FAIL - AttributeError: 'NoneType' object has no attribute 'get'
- Tests: 1 passed, 1 failed

Analyzing error... The issue is in get_fields() - the API returns null for unknown objects. Let me fix this and regenerate..."
[Regenerate driver with null check fix]
[Validate - PASS]
[Test in E2B - AUTOMATIC RETRY]
"✅ E2B Test Results (Retry 1):
- list_objects(): PASS
- get_fields(): PASS (fixed null handling)
- read(): PASS
- Tests: 3 passed, 0 failed

🎉 All tests passed! Driver is ready to use."

**Important Notes:**

- Always use the discovery-first pattern in examples
- Emphasize error handling and exception hierarchy
- Recommend comprehensive testing before production use
- Ask clarifying questions before generating code to ensure complete implementations
- Explain trade-offs for different automation levels
- For E2B testing, offer to use mock API if available
"""

# Claude Tools Configuration
CLAUDE_TOOLS = [
    {
        "name": "research_api",
        "description": "Fetch and analyze API documentation for a given API name. Returns API type (REST/GraphQL/Database), authentication methods, endpoints, query language support, pagination style, rate limits, and complexity assessment. Use this as the first step when creating a driver.",
        "input_schema": {
            "type": "object",
            "properties": {
                "api_name": {
                    "type": "string",
                    "description": "Name of the API to research (e.g., 'PostHog', 'Stripe', 'HubSpot')"
                },
                "api_url": {
                    "type": "string",
                    "description": "Optional base URL or documentation URL for the API"
                }
            },
            "required": ["api_name"]
        }
    },
    {
        "name": "evaluate_complexity",
        "description": "Evaluate automation capability and complexity for a driver based on API research. Returns automation level (LEVEL_1: 90%, LEVEL_2: 60%, LEVEL_3: 40%), list of what can be automated, what needs human input, and estimated time savings. Use this after researching the API.",
        "input_schema": {
            "type": "object",
            "properties": {
                "research_data": {
                    "type": "object",
                    "description": "The research data object returned from research_api tool"
                }
            },
            "required": ["research_data"]
        }
    },
    {
        "name": "generate_driver_scaffold",
        "description": "Generate a complete driver package from templates based on API research. Creates client.py, exceptions.py, README.md, examples/, and tests/ directories. Returns list of generated files, TODOs, and completion status. Use this after evaluating complexity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "api_name": {
                    "type": "string",
                    "description": "Name of the API (used for driver naming, e.g., 'PostHog' -> 'posthog_driver')"
                },
                "research_data": {
                    "type": "object",
                    "description": "The research data object returned from research_api tool"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Optional output directory path (defaults to generated_drivers/<driver_name>)"
                }
            },
            "required": ["api_name", "research_data"]
        }
    },
    {
        "name": "validate_driver",
        "description": "Validate a generated driver against the Driver Design v2.0 specification. Checks for required files, BaseDriver inheritance, required methods, exception hierarchy, README completeness, and counts remaining TODOs. Returns validation results with pass/fail status and detailed feedback.",
        "input_schema": {
            "type": "object",
            "properties": {
                "driver_path": {
                    "type": "string",
                    "description": "Path to the driver directory to validate"
                }
            },
            "required": ["driver_path"]
        }
    },
    {
        "name": "test_driver_in_e2b",
        "description": "Test a generated driver in an isolated E2B sandbox environment. Uploads the driver, optionally starts a mock API, and runs a comprehensive test suite covering initialization, list_objects(), get_fields(), read(), and error handling. Returns test results with pass/fail counts, errors, and suggestions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "driver_path": {
                    "type": "string",
                    "description": "Path to the driver directory to test"
                },
                "driver_name": {
                    "type": "string",
                    "description": "Name of the driver (e.g., 'posthog_driver')"
                },
                "test_api_url": {
                    "type": "string",
                    "description": "URL of the test API (defaults to http://localhost:8000 inside sandbox)"
                },
                "use_mock_api": {
                    "type": "boolean",
                    "description": "Whether to upload and start a mock API in the sandbox (default: false)"
                }
            },
            "required": ["driver_path", "driver_name"]
        }
    }
]

# Model mapping (same as web_ui)
MODEL_MAP = {
    "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-haiku-4-5": "claude-haiku-4-5-20251001",
    "claude-haiku-3-5": "claude-3-5-haiku-20241022",
    "claude-sonnet-3-5": "claude-3-5-sonnet-20241022",
}


class DriverCreatorSession:
    """
    Manages a driver creator session for a WebSocket connection.

    Each session has its own conversation history and token tracking.
    """

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # Claude SDK integration (use AsyncAnthropic for async/await support)
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_api_key:
            self.claude_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)

            # Get model from environment or use default
            model_env = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')

            # Use mapping if short name provided, otherwise use as-is
            self.claude_model = MODEL_MAP.get(model_env, model_env)

            # Get prompt caching preference (default: enabled)
            caching_env = os.getenv('ENABLE_PROMPT_CACHING', 'true').lower()
            self.enable_prompt_caching = caching_env in ('true', '1', 'yes', 'on')

            # Check if model supports prompt caching
            self.model_supports_caching = any([
                'claude-3-5-sonnet' in self.claude_model,
                'claude-sonnet-4-5' in self.claude_model,
                'claude-sonnet-4' in self.claude_model,
                'claude-3-5-haiku' in self.claude_model,
                'claude-haiku-4-5' in self.claude_model,
                'claude-3-opus' in self.claude_model,
                'claude-opus-4' in self.claude_model
            ])

            if self.enable_prompt_caching and not self.model_supports_caching:
                logger.warning(
                    f"Prompt caching enabled but model {self.claude_model} does not support it."
                )

            logger.info(f"Claude async client initialized for session {self.session_id} with model {self.claude_model}, caching={self.enable_prompt_caching}")
        else:
            self.claude_client = None
            self.claude_model = None
            self.enable_prompt_caching = False
            logger.warning(f"No ANTHROPIC_API_KEY - Claude mode disabled for session {self.session_id}")

        # Conversation state for Claude
        self.conversation_history: List[Dict[str, Any]] = []

        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_creation_tokens = 0
        self.total_cache_read_tokens = 0

        logger.info(f"Created driver creator session {self.session_id}")

    async def initialize(self):
        """Initialize the session."""
        try:
            await self.send_status("Initializing Driver Creator Agent...")

            # Send system information
            caching_status = "Enabled ✓" if self.enable_prompt_caching and self.model_supports_caching else "Disabled ✗"

            system_info = (
                f"**Driver Creator Agent**\n\n"
                f"**Model:** {self.claude_model if self.claude_model else 'No API Key - Limited Mode'}\n"
                f"**Prompt Caching:** {caching_status}\n"
                f"**Tools Available:** 5 (research, evaluate, generate, validate, test)\n\n"
                f"**Driver Design:** v2.0 (BaseDriver, discovery-first pattern)\n"
                f"**E2B Testing:** {'Enabled ✓' if os.getenv('E2B_API_KEY') else 'Disabled ✗ (set E2B_API_KEY)'}\n\n"
                f"Ready to help you create production-ready drivers!"
            )
            await self.send_status(system_info)

            logger.info(f"Session {self.session_id} initialized")
            return True

        except Exception as e:
            logger.error(f"Session {self.session_id}: Initialization failed: {str(e)}", exc_info=True)
            await self.send_error(f"Failed to initialize: {str(e)}")
            return False

    async def execute_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call from Claude and return the result.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Arguments passed to the tool

        Returns:
            Dictionary with tool execution results
        """
        try:
            # Send tool status to frontend
            await self.send_tool_status(tool_name, "running")

            loop = asyncio.get_event_loop()

            if tool_name == "research_api":
                api_name = tool_input['api_name']
                api_url = tool_input.get('api_url')

                result = await loop.run_in_executor(
                    None,
                    lambda: research_api(api_name, api_url)
                )

                tool_result = {
                    'success': True,
                    'data': result
                }

            elif tool_name == "evaluate_complexity":
                research_data = tool_input['research_data']

                result = await loop.run_in_executor(
                    None,
                    lambda: evaluate_complexity(research_data)
                )

                tool_result = {
                    'success': True,
                    'data': result
                }

            elif tool_name == "generate_driver_scaffold":
                api_name = tool_input['api_name']
                research_data = tool_input['research_data']
                output_dir = tool_input.get('output_dir')

                result = await loop.run_in_executor(
                    None,
                    lambda: generate_driver_scaffold(api_name, research_data, output_dir)
                )

                tool_result = {
                    'success': True,
                    'data': result
                }

            elif tool_name == "validate_driver":
                driver_path = tool_input['driver_path']

                result = await loop.run_in_executor(
                    None,
                    lambda: validate_driver(driver_path)
                )

                tool_result = {
                    'success': result.get('valid', False),
                    'data': result
                }

            elif tool_name == "test_driver_in_e2b":
                driver_path = tool_input['driver_path']
                driver_name = tool_input['driver_name']
                test_api_url = tool_input.get('test_api_url')
                use_mock_api = tool_input.get('use_mock_api', False)

                # Check for E2B API key
                if not os.getenv('E2B_API_KEY'):
                    tool_result = {
                        'success': False,
                        'error': 'E2B_API_KEY not set. Please configure E2B API key to run tests.'
                    }
                else:
                    result = await loop.run_in_executor(
                        None,
                        lambda: test_driver_in_e2b(
                            driver_path=driver_path,
                            driver_name=driver_name,
                            test_api_url=test_api_url,
                            use_mock_api=use_mock_api
                        )
                    )

                    tool_result = {
                        'success': result.get('success', False),
                        'data': result
                    }

            else:
                tool_result = {
                    'success': False,
                    'error': f'Unknown tool: {tool_name}'
                }

            # Send completion status
            await self.send_tool_status(
                tool_name,
                "completed" if tool_result.get('success') else "failed"
            )

            return tool_result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Session {self.session_id}: Tool '{tool_name}' failed: {error_msg}", exc_info=True)
            await self.send_tool_status(tool_name, "failed")
            return {
                'success': False,
                'error': error_msg
            }

    async def process_message_with_claude(self, user_message: str):
        """
        Process user message using Claude API with streaming and tool support.
        """
        try:
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })

            # Send typing indicator
            await self.send_typing(True)

            # Call Claude API with streaming
            max_iterations = 15
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                response_text = ""

                # Prepare system prompt (with or without caching)
                if self.enable_prompt_caching:
                    system_param = [
                        {
                            "type": "text",
                            "text": CLAUDE_SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"}
                        }
                    ]
                else:
                    system_param = CLAUDE_SYSTEM_PROMPT

                async with self.claude_client.messages.stream(
                    model=self.claude_model,
                    max_tokens=4096,
                    system=system_param,
                    messages=self.conversation_history,
                    tools=CLAUDE_TOOLS
                ) as stream:

                    async for event in stream:
                        # Handle content block delta (streaming text)
                        if event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                text_delta = event.delta.text
                                response_text += text_delta

                                # Stream to WebSocket
                                await self._safe_send({
                                    "type": "agent_delta",
                                    "delta": text_delta,
                                    "timestamp": datetime.now().isoformat()
                                })

                    # Get final message
                    final_message = await stream.get_final_message()

                # Track token usage
                if hasattr(final_message, 'usage') and final_message.usage:
                    usage = final_message.usage

                    cache_creation = 0
                    cache_read = 0

                    # Try new SDK format (nested cache_creation object)
                    if hasattr(usage, 'cache_creation') and usage.cache_creation:
                        cache_obj = usage.cache_creation
                        ephemeral_5m = getattr(cache_obj, 'ephemeral_5m_input_tokens', 0) or 0
                        ephemeral_1h = getattr(cache_obj, 'ephemeral_1h_input_tokens', 0) or 0
                        cache_creation = ephemeral_5m + ephemeral_1h

                    # Fall back to old SDK format
                    if cache_creation == 0:
                        cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0

                    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0

                    self.total_input_tokens += usage.input_tokens
                    self.total_output_tokens += usage.output_tokens
                    self.total_cache_creation_tokens += cache_creation
                    self.total_cache_read_tokens += cache_read

                    # Send usage update to frontend
                    await self._safe_send({
                        "type": "usage",
                        "usage": {
                            "input_tokens": usage.input_tokens,
                            "output_tokens": usage.output_tokens,
                            "cache_creation_tokens": cache_creation,
                            "cache_read_tokens": cache_read,
                            "total_input_tokens": self.total_input_tokens,
                            "total_output_tokens": self.total_output_tokens,
                            "total_cache_creation_tokens": self.total_cache_creation_tokens,
                            "total_cache_read_tokens": self.total_cache_read_tokens
                        },
                        "timestamp": datetime.now().isoformat()
                    })

                # Check if Claude wants to use tools
                if final_message.stop_reason == "tool_use":
                    logger.info(f"Session {self.session_id}: Claude requested tool use")

                    # Execute each tool call
                    tool_results = []

                    try:
                        for block in final_message.content:
                            if block.type == "tool_use":
                                tool_name = block.name
                                tool_input = block.input
                                tool_id = block.id

                                logger.info(f"Executing tool: {tool_name}")

                                # Execute tool
                                tool_result = await self.execute_tool_call(
                                    tool_name,
                                    tool_input
                                )

                                # Send tool result to frontend
                                await self._safe_send({
                                    "type": "tool_result",
                                    "tool": tool_name,
                                    "success": tool_result.get('success', False),
                                    "result": tool_result.get('data', tool_result)
                                })

                                # Serialize result for Claude API
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": json.dumps(tool_result)
                                })

                    except Exception as tool_error:
                        logger.error(f"Session {self.session_id}: Tool error: {tool_error}", exc_info=True)
                        await self.send_error(f"Tool execution error: {str(tool_error)}")
                        break

                    # Add assistant message and tool results to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_message.content
                    })

                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                    # Continue loop
                    continue

                else:
                    # No more tools - final response
                    if response_text:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response_text
                        })

                    break

            # Check if we hit max iterations
            if iteration >= max_iterations:
                logger.warning(f"Session {self.session_id}: Reached max iterations ({max_iterations})")
                await self.send_agent_message(
                    "⚠️ I reached the maximum number of conversation turns. "
                    "Please try asking your question again or breaking it into smaller parts."
                )

            await self.send_typing(False)

        except anthropic.APIStatusError as e:
            # Handle API errors
            if 'overloaded' in str(e).lower():
                user_msg = "⚠️ Claude API is temporarily overloaded. Please wait and try again."
            elif e.status_code == 429:
                user_msg = "⚠️ Rate limit reached. Please wait a moment and try again."
            elif e.status_code == 401:
                user_msg = "❌ Authentication error. Check your ANTHROPIC_API_KEY."
            else:
                user_msg = f"❌ Claude API error ({e.status_code}): {str(e)}"

            logger.error(f"Session {self.session_id}: API error: {str(e)}")
            await self.send_error(user_msg)
            await self.send_typing(False)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Session {self.session_id}: Error: {error_msg}", exc_info=True)
            await self.send_error(f"❌ Unexpected error: {error_msg}")
            await self.send_typing(False)

    async def process_message(self, user_message: str):
        """Process a user message."""
        if self.claude_client:
            await self.process_message_with_claude(user_message)
        else:
            await self.send_error("❌ ANTHROPIC_API_KEY not set. Please configure API key.")

    async def send_agent_message(self, content: str):
        """Send an agent text message to the frontend."""
        await self._safe_send({
            "type": "agent_message",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    async def _safe_send(self, data: Dict[str, Any]) -> bool:
        """Safely send data via WebSocket."""
        try:
            if self.websocket.client_state.name != "CONNECTED":
                return False
            await self.websocket.send_json(data)
            return True
        except Exception:
            return False

    async def send_status(self, status: str):
        """Send a status update to the frontend."""
        await self._safe_send({
            "type": "status",
            "content": status,
            "timestamp": datetime.now().isoformat()
        })

    async def send_error(self, error: str):
        """Send an error message to the frontend."""
        await self._safe_send({
            "type": "error",
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    async def send_tool_status(self, tool: str, status: str):
        """Send tool execution status to the frontend."""
        await self._safe_send({
            "type": "tool",
            "tool": tool,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })

    async def send_typing(self, is_typing: bool):
        """Send typing indicator to the frontend."""
        await self._safe_send({
            "type": "typing",
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat()
        })


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with the driver creator agent.

    Message format from client:
        {"type": "message", "content": "user message"}

    Message formats to client:
        {"type": "agent_message", "content": "agent text"}
        {"type": "agent_delta", "delta": "streaming text"}
        {"type": "status", "content": "status message"}
        {"type": "tool", "tool": "tool_name", "status": "running|completed|failed"}
        {"type": "error", "error": "error message"}
        {"type": "typing", "is_typing": true|false}
        {"type": "usage", "usage": {...}}
    """
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    session = DriverCreatorSession(websocket)

    try:
        # Initialize the session
        initialized = await session.initialize()

        if not initialized:
            logger.error("Session initialization failed")
            await websocket.close(code=1011, reason="Failed to initialize")
            return

        # Send welcome message
        await session.send_agent_message(
            "Hello! I'm your Driver Creator Assistant. "
            "I can help you build production-ready data integration drivers using the Driver Design v2.0 specification.\n\n"
            "Tell me which API you'd like to create a driver for, and I'll guide you through the process!"
        )

        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            message_type = data.get('type')

            if message_type == 'message':
                content = data.get('content', '').strip()

                if not content:
                    continue

                logger.info(f"Received message: {content[:100]}...")

                # Process the message
                await session.process_message(content)

            elif message_type == 'ping':
                try:
                    await websocket.send_json({"type": "pong"})
                except Exception:
                    pass

            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session.session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        try:
            await session.send_error(f"Connection error: {str(e)}")
        except:
            pass

    finally:
        logger.info(f"Session {session.session_id} closed")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "driver-creator-agent",
        "timestamp": datetime.now().isoformat()
    }


# API info endpoint
@app.get("/api/info")
async def api_info():
    """Get API information."""
    return {
        "name": "Driver Creator Agent",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws",
            "health": "/health",
            "info": "/api/info"
        },
        "features": [
            "Real-time WebSocket chat",
            "Claude Sonnet 4.5 integration",
            "API documentation research",
            "Driver scaffold generation",
            "Driver validation",
            "E2B sandbox testing",
            "Session management"
        ]
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Driver Creator Agent</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                line-height: 1.6;
            }
            h1 { color: #333; }
            .endpoint {
                background: #f5f5f5;
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                font-family: monospace;
            }
            .status {
                color: #28a745;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <h1>Driver Creator Agent</h1>
        <p class="status">✓ Server is running</p>

        <h2>WebSocket Endpoint</h2>
        <div class="endpoint">ws://localhost:8081/ws</div>

        <h2>API Endpoints</h2>
        <div class="endpoint">GET /health - Health check</div>
        <div class="endpoint">GET /api/info - API information</div>

        <h2>Features</h2>
        <ul>
            <li>AI-powered driver generation with Claude Sonnet 4.5</li>
            <li>API documentation research</li>
            <li>Complexity evaluation and automation assessment</li>
            <li>Driver scaffold generation from templates</li>
            <li>Driver validation against Design v2.0 spec</li>
            <li>E2B sandbox testing</li>
        </ul>

        <h2>Getting Started</h2>
        <p>Visit <code>/static/</code> for the web interface.</p>

        <hr>
        <p><small>Driver Creator Agent v1.0.0</small></p>
    </body>
    </html>
    """)


# Mount static files directory (if it exists)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info(f"Mounted static files from {static_dir}")
else:
    logger.warning(f"Static directory not found: {static_dir}")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("="*80)
    logger.info("Driver Creator Agent - Web UI Backend")
    logger.info("="*80)
    logger.info("Server starting...")
    logger.info(f"WebSocket endpoint: ws://localhost:8081/ws")
    logger.info(f"Health check: http://localhost:8081/health")
    logger.info(f"API info: http://localhost:8081/api/info")

    # Check for API keys
    if not os.getenv('ANTHROPIC_API_KEY'):
        logger.warning("⚠️  ANTHROPIC_API_KEY not set! Agent will not function.")
        logger.warning("   Please set ANTHROPIC_API_KEY in your .env file")
    else:
        logger.info("✓ ANTHROPIC_API_KEY found")

    if not os.getenv('E2B_API_KEY'):
        logger.warning("⚠️  E2B_API_KEY not set! E2B testing will not work.")
        logger.warning("   Set E2B_API_KEY to enable driver testing")
    else:
        logger.info("✓ E2B_API_KEY found")

    logger.info("="*80)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Server shutting down...")


if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info"
    )
