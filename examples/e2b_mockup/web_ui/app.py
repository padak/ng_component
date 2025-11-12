"""
Web UI Backend for Agent-Based Integration System

FastAPI application with WebSocket support for real-time agent chat.
Integrates with AgentExecutor for E2B sandbox execution and claude-agent-sdk for agent logic.

Features:
- WebSocket endpoint for real-time chat
- Agent creation with discovery capabilities
- Stream agent responses to frontend
- Execute scripts in E2B sandboxes
- Session management per WebSocket connection
- Static file serving for frontend

Usage:
    uvicorn web_ui.app:app --reload --port 8080
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import anthropic

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_executor import AgentExecutor
from script_templates import ScriptTemplates

# Add current directory to path for local imports (pricing.py)
sys.path.insert(0, str(Path(__file__).parent))
from pricing import calculate_cost

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# JSON serialization helper for non-standard types
def safe_json_dumps(obj: Any, **kwargs) -> str:
    """
    Safely serialize objects to JSON, handling datetime, Decimal, and other non-standard types.

    Args:
        obj: Object to serialize
        **kwargs: Additional arguments to pass to json.dumps

    Returns:
        JSON string
    """
    def json_serializer(o):
        """Handle non-standard types for JSON serialization."""
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, Decimal):
            return float(o)
        elif isinstance(o, bytes):
            return o.decode('utf-8', errors='replace')
        elif hasattr(o, '__dict__'):
            return o.__dict__
        else:
            return str(o)

    try:
        return json.dumps(obj, default=json_serializer, **kwargs)
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        # Fall back to a simple string representation
        return json.dumps({"error": "serialization_failed", "message": str(e), "data": str(obj)[:1000]})

# Create FastAPI app
app = FastAPI(
    title="Agent-Based Integration System",
    description="Web UI for AI-powered Salesforce integration agent",
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
CLAUDE_SYSTEM_PROMPT = """You are an expert Salesforce integration assistant that helps users query and analyze Salesforce data through an E2B sandbox environment.

**Your Capabilities:**

You have access to four powerful tools that allow you to interact with Salesforce:

1. **discover_objects**: Lists all available Salesforce objects (Lead, Campaign, CampaignMember, etc.)
2. **get_object_fields**: Gets the complete field schema for a specific object
3. **execute_salesforce_query**: Generates and executes Python scripts to query Salesforce data
4. **show_last_script**: Shows the Python code from the most recent query execution

**Discovery-First Approach:**

When a user asks about data you're unfamiliar with, ALWAYS follow this pattern:

1. Use `discover_objects` to see what objects are available
2. Use `get_object_fields` to understand the schema of relevant objects
3. Use `execute_salesforce_query` to generate and run the appropriate query
4. Present results in a clear, conversational manner

**Query Generation Guidelines:**

When using `execute_salesforce_query`:
- The `description` parameter should explain what data you're retrieving
- The `python_script` parameter must contain complete Python code
- You will write scripts that use the SalesforceClient from the salesforce_driver
- Scripts must use api_url='http://localhost:8000' and api_key='<api_key_here>' (placeholder)
- Always handle errors gracefully with try/except blocks
- Return results as JSON for easy parsing

**Script Template Structure:**

Every script you generate should follow this pattern:

```python
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

# Initialize client
client = SalesforceClient(
    api_url='http://localhost:8000',
    api_key='<api_key_here>'
)

try:
    # Your query logic here
    results = client.query("SELECT ... FROM ...")

    # Format and return as JSON
    output = {
        'count': len(results),
        'data': results
    }
    print(json.dumps(output, indent=2))

except Exception as e:
    error = {'error': str(e)}
    print(json.dumps(error, indent=2))
```

**Response Style:**

- Be conversational and helpful
- Explain what you're doing when executing tools
- Provide summaries of results, not just raw data
- Suggest follow-up queries that might be useful
- When showing data, highlight key insights
- **After executing a query successfully, ALWAYS offer to show the Python code**

**Code Transparency:**

After using the `execute_salesforce_query` tool successfully, you should:
1. Present the query results
2. Automatically mention that you can show the generated Python code
3. Say something like: "Would you like to see the Python script I generated? Just ask 'show me the code'"

**Examples:**

User: "Show me recent leads"
You: "I'll query the leads created recently. Let me fetch that data..."
[Use execute_salesforce_query with script to get leads from last 30 days]
"I found 45 leads created in the last 30 days. The most common status is 'New' with 28 leads...
Would you like to see the Python script I generated? Just ask 'show me the code' or 'show the script'."

User: "What data can I access?"
You: "Let me discover what Salesforce objects are available..."
[Use discover_objects]
"I have access to 3 objects: Lead (with 15 fields), Campaign (with 12 fields), and CampaignMember (with 8 fields). Would you like to explore any of these?"

User: "Show me the code you used"
You: "Here's the Python script I executed..."
[Use show_last_script]
"""

# Claude Tools Configuration
CLAUDE_TOOLS = [
    {
        "name": "discover_objects",
        "description": "Discovers all available Salesforce objects and their schemas. Use this when you need to understand what data is available in the Salesforce instance. Returns a list of object names and their field counts.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_object_fields",
        "description": "Gets the complete field schema for a specific Salesforce object. Use this to understand what fields are available before constructing queries. Returns detailed field information including types, labels, and requirements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "The name of the Salesforce object (e.g., 'Lead', 'Campaign', 'CampaignMember')"
                }
            },
            "required": ["object_name"]
        }
    },
    {
        "name": "execute_salesforce_query",
        "description": "Generates and executes a Python script to query Salesforce data. You should generate the complete Python code that uses the SalesforceClient to perform the desired operation. The script will be executed in an E2B sandbox with access to the Salesforce driver.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what this query does (e.g., 'Get leads from last 30 days')"
                },
                "python_script": {
                    "type": "string",
                    "description": "Complete Python script to execute. Must import SalesforceClient, initialize it with api_url='http://localhost:8000' and api_key='<api_key_here>', execute queries, and print results as JSON."
                }
            },
            "required": ["description", "python_script"]
        }
    },
    {
        "name": "show_last_script",
        "description": "Shows the Python code from the most recently executed query. Use this when the user asks to see the code, script, or wants to know how something was done.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


class AgentSession:
    """
    Manages an agent session for a WebSocket connection.

    Each session has its own AgentExecutor instance for E2B sandbox isolation.
    """

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.executor: Optional[AgentExecutor] = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # Legacy message history (keep for backward compatibility)
        self.message_history: List[Dict[str, str]] = []

        # Claude SDK integration (use AsyncAnthropic for async/await support)
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_api_key:
            self.claude_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)

            # Get model from environment or use default
            model_env = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')

            # Map short model names to full model IDs with dates
            model_mapping = {
                'claude-sonnet-4-5': 'claude-sonnet-4-5-20250929',
                'claude-sonnet-4': 'claude-sonnet-4-20250514',
                'claude-haiku-4-5': 'claude-haiku-4-5-20251001',
                'claude-haiku-3-5': 'claude-3-5-haiku-20241022',
                'claude-sonnet-3-5': 'claude-3-5-sonnet-20241022',
            }

            # Use mapping if short name provided, otherwise use as-is (for full IDs)
            self.claude_model = model_mapping.get(model_env, model_env)

            # Get prompt caching preference (default: enabled)
            caching_env = os.getenv('ENABLE_PROMPT_CACHING', 'true').lower()
            self.enable_prompt_caching = caching_env in ('true', '1', 'yes', 'on')

            # Check if model supports prompt caching
            # According to Anthropic docs (https://docs.claude.com/en/docs/build-with-claude/prompt-caching)
            # Models supporting caching: Opus 4.1/4/3, Sonnet 4.5/4/3.7, Haiku 4.5/3.5/3
            self.model_supports_caching = any([
                'claude-3-5-sonnet' in self.claude_model,
                'claude-sonnet-4-5' in self.claude_model,
                'claude-sonnet-4' in self.claude_model,
                'claude-3-5-haiku' in self.claude_model,
                'claude-haiku-4-5' in self.claude_model,  # Haiku 4.5 DOES support caching!
                'claude-3-opus' in self.claude_model,
                'claude-opus-4' in self.claude_model
            ])

            if self.enable_prompt_caching and not self.model_supports_caching:
                logger.warning(
                    f"Prompt caching enabled but model {self.claude_model} does not support it. "
                    f"Caching only works with: Sonnet 3.5/4.5, Haiku 3.5, or Opus 3."
                )

            logger.info(f"Claude async client initialized for session {self.session_id} with model {self.claude_model}, caching={self.enable_prompt_caching}, model_supports_caching={self.model_supports_caching}")
        else:
            self.claude_client = None
            self.claude_model = None
            self.enable_prompt_caching = False
            logger.warning(f"No ANTHROPIC_API_KEY - Claude mode disabled for session {self.session_id}")

        # Conversation state for Claude
        self.conversation_history: List[Dict[str, Any]] = []
        self.last_executed_script: Optional[str] = None

        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_creation_tokens = 0
        self.total_cache_read_tokens = 0

        # Cost tracking (USD)
        self.total_cost = 0.0

        logger.info(f"Created session {self.session_id}")

    async def initialize(self):
        """Initialize the AgentExecutor (creates E2B sandbox)."""
        try:
            await self.send_status("Initializing agent environment...")

            # Create executor in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def create_executor_with_sandbox():
                executor = AgentExecutor()
                executor.create_sandbox()  # Create sandbox with auto-setup
                return executor

            self.executor = await loop.run_in_executor(
                None,
                create_executor_with_sandbox
            )

            # Send detailed initialization success message with system info for sidebar
            sandbox_id = self.executor.sandbox.sandbox_id

            # Send system information to populate sidebar (not as a chat message)
            # Determine caching status message
            if self.enable_prompt_caching and self.model_supports_caching:
                caching_status = "Enabled ✓ (Ephemeral, 5 min)"
            elif self.enable_prompt_caching and not self.model_supports_caching:
                caching_status = "⚠️ Enabled but NOT SUPPORTED by this model"
            else:
                caching_status = "Disabled ✗"

            system_info = (
                f"**E2B Sandbox:** `{sandbox_id}`\n"
                f"**Database:** DuckDB with 180 test records\n"
                f"**Salesforce Driver:** Loaded successfully\n"
                f"**Mock API:** Running on `localhost:8000` (inside sandbox)\n"
                f"**Available Objects:** Account, Lead, Opportunity, Campaign\n\n"
                f"**Model:** {self.claude_model if self.claude_model else 'Pattern Matching (No API Key)'}\n"
                f"**Prompt Caching:** {caching_status}\n\n"
                f"**Environment:**\n"
                f"- `SF_API_URL`: {self.executor.sandbox_sf_api_url}\n"
                f"- `SF_API_KEY`: {'*' * 8} (configured)\n"
                f"- `E2B_API_KEY`: {'*' * 8} (configured)"
            )
            await self.send_status(system_info)

            logger.info(f"Session {self.session_id} initialized with sandbox {sandbox_id}")

            return True

        except Exception as e:
            error_msg = str(e)

            # Provide specific error messages for common initialization failures
            if 'E2B_API_KEY' in error_msg or 'api_key' in error_msg.lower():
                user_msg = (
                    "❌ **E2B API Key Error**: Unable to initialize sandbox. "
                    "Please ensure E2B_API_KEY is set in your .env file. "
                    f"Get your key from https://e2b.dev/"
                )
            elif 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                user_msg = (
                    "⏱️ **E2B Sandbox Timeout**: Sandbox creation took too long. "
                    "This might be due to high E2B load. Please refresh and try again."
                )
            elif 'network' in error_msg.lower() or 'connection' in error_msg.lower():
                user_msg = (
                    "🌐 **Network Error**: Unable to connect to E2B servers. "
                    "Please check your internet connection and try again."
                )
            elif 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
                user_msg = (
                    "⚠️ **E2B Quota Exceeded**: You've reached your E2B sandbox limit. "
                    "Please wait for existing sandboxes to expire or upgrade your plan."
                )
            else:
                user_msg = f"❌ **Failed to initialize agent**: {error_msg}"

            logger.error(f"Session {self.session_id}: Initialization failed: {error_msg}", exc_info=True)
            await self.send_error(user_msg)
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

            if tool_name == "discover_objects":
                # Run discovery
                result = await loop.run_in_executor(
                    None,
                    self.executor.run_discovery
                )

                # Format for Claude
                objects_summary = []
                for obj_name in result.get('objects', []):
                    schema = result.get('schemas', {}).get(obj_name, {})
                    field_count = len(schema.get('fields', []))
                    objects_summary.append({
                        'name': obj_name,
                        'field_count': field_count
                    })

                tool_result = {
                    'success': True,
                    'objects': objects_summary,
                    'total_count': len(result.get('objects', []))
                }

            elif tool_name == "get_object_fields":
                object_name = tool_input['object_name']

                # Generate and execute discovery script
                script = ScriptTemplates.discover_schema(
                    api_url=self.executor.sandbox_sf_api_url,
                    api_key=self.executor.sf_api_key,
                    object_name=object_name
                )

                exec_result = await loop.run_in_executor(
                    None,
                    lambda: self.executor.execute_script(
                        script,
                        f"Get {object_name} schema"
                    )
                )

                if exec_result['success'] and exec_result['data']:
                    schema = exec_result['data'].get('schema', {})
                    tool_result = {
                        'success': True,
                        'object_name': object_name,
                        'schema': schema
                    }
                else:
                    tool_result = {
                        'success': False,
                        'error': exec_result.get('error', 'Unknown error')
                    }

            elif tool_name == "execute_salesforce_query":
                description = tool_input['description']
                python_script = tool_input['python_script']

                # Replace placeholder API key in the script
                python_script = python_script.replace(
                    '<api_key_here>',
                    self.executor.sf_api_key
                )

                # Store the script for show_last_script
                self.last_executed_script = python_script

                # Execute the script
                exec_result = await loop.run_in_executor(
                    None,
                    lambda: self.executor.execute_script(python_script, description)
                )

                tool_result = {
                    'success': exec_result['success'],
                    'description': description,
                    'output': exec_result.get('output', ''),
                    'data': exec_result.get('data'),
                    'error': exec_result.get('error')
                }

                # Also send result to frontend
                if exec_result['success']:
                    await self.send_result({
                        'success': True,
                        'data': exec_result.get('data'),
                        'description': description
                    })

            elif tool_name == "show_last_script":
                if self.last_executed_script:
                    tool_result = {
                        'success': True,
                        'script': self.last_executed_script
                    }
                else:
                    tool_result = {
                        'success': False,
                        'message': 'No script has been executed yet in this session.'
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

        except asyncio.TimeoutError:
            error_msg = f"Tool '{tool_name}' timed out. The operation took too long to complete."
            logger.error(f"Session {self.session_id}: {error_msg}")
            await self.send_tool_status(tool_name, "failed")
            return {
                'success': False,
                'error': error_msg
            }

        except Exception as e:
            error_msg = str(e)

            # Check if this is a sandbox timeout/expiration error
            sandbox_expired = (
                'timed out' in error_msg.lower() or
                'timeout' in error_msg.lower() or
                'expired' in error_msg.lower() or
                'not found' in error_msg.lower() or
                '502' in error_msg  # Bad Gateway often means sandbox is gone
            )

            if sandbox_expired and 'sandbox' in error_msg.lower():
                logger.warning(f"Session {self.session_id}: Sandbox expired, attempting to recreate...")

                # Notify user
                await self.send_agent_message("⏱️ The sandbox has expired. Let me create a new one and retry...")

                try:
                    # Recreate the sandbox
                    await self.initialize()

                    # Retry the tool execution once
                    logger.info(f"Session {self.session_id}: Retrying tool '{tool_name}' with new sandbox")
                    return await self.execute_tool_call(tool_name, tool_input)

                except Exception as retry_error:
                    logger.error(f"Session {self.session_id}: Failed to recreate sandbox: {retry_error}")
                    await self.send_tool_status(tool_name, "failed")
                    return {
                        'success': False,
                        'error': f"Failed to recreate sandbox after timeout: {str(retry_error)}"
                    }

            # Provide specific error messages for common tool failures
            if 'sandbox' in error_msg.lower():
                user_error = f"E2B sandbox error during '{tool_name}': {error_msg}"
            elif 'timeout' in error_msg.lower():
                user_error = f"Timeout executing '{tool_name}': Operation took too long"
            elif 'connection' in error_msg.lower() or 'network' in error_msg.lower():
                user_error = f"Network error during '{tool_name}': Unable to connect to E2B"
            else:
                user_error = f"Tool execution error: {error_msg}"

            logger.error(f"Session {self.session_id}: Tool '{tool_name}' failed: {error_msg}", exc_info=True)
            await self.send_tool_status(tool_name, "failed")
            return {
                'success': False,
                'error': user_error
            }

    async def process_message_with_claude(self, user_message: str):
        """
        Process user message using Claude API with streaming and tool support.

        This replaces the pattern-matching logic with intelligent agent behavior.
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
            max_iterations = 15  # Allow enough iterations for complex multi-tool queries
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Create streaming request
                response_text = ""

                # Prepare system prompt (with or without caching)
                if self.enable_prompt_caching:
                    # Enable prompt caching (90% cost reduction on cached tokens)
                    system_param = [
                        {
                            "type": "text",
                            "text": CLAUDE_SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"}
                        }
                    ]
                    logger.info(f"Session {self.session_id}: Caching enabled, system_param format: list with cache_control")
                else:
                    # Standard system prompt (no caching)
                    system_param = CLAUDE_SYSTEM_PROMPT
                    logger.info(f"Session {self.session_id}: Caching disabled, system_param format: string")

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

                                # Stream to WebSocket (safely)
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

                    # Log the complete usage object for debugging
                    logger.info(f"Session {self.session_id} - Claude API usage object: {usage}")
                    logger.info(f"  - input_tokens: {usage.input_tokens}")
                    logger.info(f"  - output_tokens: {usage.output_tokens}")

                    # Track cache metrics (handle both old and new SDK formats)
                    # New SDK (0.39+): usage.cache_creation.ephemeral_5m_input_tokens / ephemeral_1h_input_tokens
                    # Old SDK: usage.cache_creation_input_tokens (flat structure)
                    cache_creation = 0
                    cache_read = 0

                    # Try new SDK format first (nested cache_creation object)
                    if hasattr(usage, 'cache_creation') and usage.cache_creation:
                        cache_obj = usage.cache_creation
                        # Log the cache_creation object for debugging
                        logger.info(f"  - cache_creation object: {cache_obj}")

                        # Try ephemeral_5m first (5-minute cache)
                        ephemeral_5m = getattr(cache_obj, 'ephemeral_5m_input_tokens', 0) or 0
                        # Try ephemeral_1h (1-hour cache)
                        ephemeral_1h = getattr(cache_obj, 'ephemeral_1h_input_tokens', 0) or 0

                        # Total cache creation is sum of both TTLs
                        cache_creation = ephemeral_5m + ephemeral_1h

                        if ephemeral_5m > 0:
                            logger.info(f"  - ephemeral_5m_input_tokens: {ephemeral_5m} (5-minute cache)")
                        if ephemeral_1h > 0:
                            logger.info(f"  - ephemeral_1h_input_tokens: {ephemeral_1h} (1-hour cache)")

                    # Fall back to old SDK format (flat structure)
                    if cache_creation == 0:
                        cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
                        if cache_creation > 0:
                            logger.info(f"  - cache_creation_input_tokens (old format): {cache_creation}")

                    # Cache read tokens (same in both formats)
                    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0

                    # Log cache metrics summary
                    if cache_creation > 0:
                        logger.info(f"  - TOTAL cache_creation: {cache_creation} (CACHE CREATED)")
                    if cache_read > 0:
                        logger.info(f"  - cache_read_input_tokens: {cache_read} (CACHE HIT!)")

                    if cache_creation == 0 and cache_read == 0 and self.enable_prompt_caching:
                        logger.warning(f"  - No cache metrics found. Caching enabled: {self.enable_prompt_caching}")
                        logger.warning(f"  - Usage object attributes: {dir(usage)}")

                    self.total_input_tokens += usage.input_tokens
                    self.total_output_tokens += usage.output_tokens
                    self.total_cache_creation_tokens += cache_creation
                    self.total_cache_read_tokens += cache_read

                    # Calculate costs for this request
                    request_usage = {
                        "input_tokens": usage.input_tokens,
                        "cache_creation_input_tokens": cache_creation,
                        "cache_read_input_tokens": cache_read,
                        "output_tokens": usage.output_tokens
                    }
                    request_cost = calculate_cost(request_usage, self.claude_model)

                    # Calculate total session cost
                    total_usage = {
                        "input_tokens": self.total_input_tokens,
                        "cache_creation_input_tokens": self.total_cache_creation_tokens,
                        "cache_read_input_tokens": self.total_cache_read_tokens,
                        "output_tokens": self.total_output_tokens
                    }
                    total_cost_breakdown = calculate_cost(total_usage, self.claude_model)
                    self.total_cost = total_cost_breakdown['total_cost']

                    # Log cost information
                    logger.info(f"  - Request cost: ${request_cost['total_cost']:.4f}")
                    logger.info(f"  - Total session cost: ${self.total_cost:.4f}")

                    # Send usage update to frontend (safely)
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
                        "cost": {
                            "request_cost": request_cost['total_cost'],
                            "request_breakdown": request_cost,
                            "total_cost": self.total_cost,
                            "total_breakdown": total_cost_breakdown
                        },
                        "timestamp": datetime.now().isoformat()
                    })

                # Check if Claude wants to use tools
                if final_message.stop_reason == "tool_use":
                    logger.info(f"Session {self.session_id}: Claude requested tool use, processing...")

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

                                logger.info(f"Tool {tool_name} completed, serializing result...")

                                # Use safe JSON serialization to handle datetime, Decimal, etc.
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": safe_json_dumps(tool_result)
                                })

                                logger.info(f"Tool {tool_name} result serialized successfully")

                    except Exception as tool_error:
                        logger.error(f"Session {self.session_id}: Error processing tools: {tool_error}", exc_info=True)
                        await self.send_error(f"Tool execution error: {str(tool_error)}")
                        break  # Exit the while loop on tool error

                    # Add assistant message and tool results to history
                    logger.info(f"Session {self.session_id}: Adding {len(tool_results)} tool results to conversation history")
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_message.content
                    })

                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                    # Continue loop to get Claude's response to tool results
                    logger.info(f"Session {self.session_id}: Continuing conversation loop (iteration {iteration}/{max_iterations})...")
                    continue

                else:
                    # No more tools - final response received

                    # Add complete response to history
                    if response_text:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response_text
                        })

                        # Note: Don't send agent_message here - frontend already has
                        # the complete message from streaming agent_delta events

                    break

            # Check if we hit max iterations without a final response
            if iteration >= max_iterations:
                logger.warning(f"Session {self.session_id}: Reached max iterations ({max_iterations}) without final response")
                await self.send_agent_message(
                    "⚠️ I reached the maximum number of conversation turns. "
                    "The query was complex and required many steps. Please try asking your question again, "
                    "or try breaking it into smaller parts."
                )

            await self.send_typing(False)

        except anthropic.APIStatusError as e:
            # Handle specific API errors with user-friendly messages
            error_type = getattr(e, 'type', None) or (e.response.json() if hasattr(e, 'response') else {}).get('error', {}).get('type')

            if 'overloaded' in str(e).lower() or error_type == 'overloaded_error':
                user_msg = (
                    "⚠️ **Claude API is temporarily overloaded** (high traffic). "
                    "Please wait 30-60 seconds and try again. Your session is still active."
                )
                logger.warning(f"Session {self.session_id}: Claude API overloaded")
            elif e.status_code == 429:
                user_msg = (
                    "⚠️ **Rate limit reached**. The API is receiving too many requests. "
                    "Please wait a moment and try again."
                )
                logger.warning(f"Session {self.session_id}: Rate limit hit (429)")
            elif e.status_code == 401:
                user_msg = (
                    "❌ **Authentication error**. Your ANTHROPIC_API_KEY is invalid or expired. "
                    "Please check your .env file."
                )
                logger.error(f"Session {self.session_id}: Authentication failed (401)")
            elif e.status_code == 500:
                user_msg = (
                    "❌ **Claude API server error**. The API is experiencing internal issues. "
                    "Please try again in a few moments."
                )
                logger.error(f"Session {self.session_id}: Claude API 500 error")
            elif e.status_code == 503:
                user_msg = (
                    "⚠️ **Service temporarily unavailable**. The Claude API is down for maintenance. "
                    "Please try again later."
                )
                logger.error(f"Session {self.session_id}: Claude API unavailable (503)")
            else:
                user_msg = f"❌ **Claude API error** ({e.status_code}): {str(e)}"
                logger.warning(f"Session {self.session_id}: Claude API error {e.status_code}: {str(e)}")

            await self.send_error(user_msg)
            await self.send_typing(False)

        except asyncio.TimeoutError:
            user_msg = (
                "⏱️ **Request timed out**. The operation took too long to complete. "
                "This might be due to network issues or high API load. Please try again."
            )
            logger.error(f"Session {self.session_id}: Timeout in Claude processing")
            await self.send_error(user_msg)
            await self.send_typing(False)

        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = str(e)

            # Check for common network errors
            if 'connection' in error_msg.lower() or 'network' in error_msg.lower():
                user_msg = (
                    "🌐 **Network error**. Unable to connect to Claude API. "
                    "Please check your internet connection and try again."
                )
            else:
                user_msg = f"❌ **Unexpected error**: {error_msg}"

            logger.error(f"Session {self.session_id}: Claude processing failed: {error_msg}", exc_info=True)
            await self.send_error(user_msg)
            await self.send_typing(False)

    async def process_message(self, user_message: str):
        """
        Process a user message - routes to Claude or pattern matching fallback.

        If ANTHROPIC_API_KEY is available, uses Claude SDK for intelligent responses.
        Otherwise falls back to pattern-matching logic.
        """
        # Check if Claude is available
        if self.claude_client:
            try:
                await self.process_message_with_claude(user_message)
                return
            except Exception as e:
                logger.warning(f"Claude failed, falling back to pattern matching: {e}")
                # Fall through to pattern matching

        # Pattern matching fallback
        await self.process_message_with_patterns(user_message)

    async def process_message_with_patterns(self, user_message: str):
        """
        Process message using pattern matching (legacy/fallback mode).

        Original implementation that matches user messages to pre-defined templates.
        """
        try:
            # Add to history
            self.message_history.append({"role": "user", "content": user_message})

            # Send typing indicator
            await self.send_typing(True)

            # Parse intent and execute
            # In production, this would use Claude API to understand intent
            # For now, we'll use simple pattern matching

            user_lower = user_message.lower()

            # Check for discovery requests
            if any(phrase in user_lower for phrase in ['what objects', 'list objects', 'available objects', 'what data']):
                await self.handle_discovery()

            # Check for field discovery
            elif 'fields' in user_lower and any(obj in user_lower for obj in ['lead', 'campaign', 'member']):
                # Extract object name
                object_name = 'Lead'  # default
                if 'campaign' in user_lower and 'member' not in user_lower:
                    object_name = 'Campaign'
                elif 'member' in user_lower or 'campaignmember' in user_lower:
                    object_name = 'CampaignMember'

                await self.handle_field_discovery(object_name)

            # Check for query requests
            elif any(phrase in user_lower for phrase in ['get', 'show', 'find', 'list', 'query']):
                await self.handle_query_request(user_message)

            # Help or greeting
            elif any(phrase in user_lower for phrase in ['help', 'hello', 'hi', 'what can you do']):
                await self.send_agent_message(
                    "Hello! I'm your Salesforce integration assistant. I can help you:\n\n"
                    "- Query leads (e.g., 'Get leads from last 30 days')\n"
                    "- Filter by status (e.g., 'Show me all New leads')\n"
                    "- Get campaign data (e.g., 'Get leads for Summer Campaign')\n"
                    "- Discover available data (e.g., 'What objects are available?')\n"
                    "- Explore schemas (e.g., 'What fields does Lead have?')\n\n"
                    "What would you like to explore?"
                )

            else:
                # Default: try to execute as a query
                await self.handle_query_request(user_message)

            await self.send_typing(False)

        except Exception as e:
            logger.error(f"Session {self.session_id} error processing message: {str(e)}", exc_info=True)
            await self.send_error(f"Error processing message: {str(e)}")
            await self.send_typing(False)

    async def handle_discovery(self):
        """Run object discovery and report results."""
        try:
            await self.send_agent_message("Let me discover what Salesforce objects are available...")
            await self.send_tool_status("discover_objects", "running")

            # Run discovery in thread pool
            loop = asyncio.get_event_loop()
            discovery = await loop.run_in_executor(
                None,
                self.executor.run_discovery
            )

            await self.send_tool_status("discover_objects", "completed")

            # Format response
            objects = discovery.get('objects', [])
            response = f"I found {len(objects)} Salesforce objects:\n\n"

            for i, obj in enumerate(objects, 1):
                schema = discovery.get('schemas', {}).get(obj, {})
                field_count = len(schema.get('fields', []))
                response += f"{i}. **{obj}** ({field_count} fields)\n"

            response += f"\nWould you like to explore any of these objects in detail?"

            await self.send_agent_message(response)

        except Exception as e:
            logger.error(f"Discovery failed: {str(e)}", exc_info=True)
            await self.send_error(f"Discovery failed: {str(e)}")

    async def handle_field_discovery(self, object_name: str):
        """Get field schema for a specific object."""
        try:
            await self.send_agent_message(f"Let me get the schema for the {object_name} object...")
            await self.send_tool_status("get_fields", "running")

            # Generate and execute discovery script
            script = ScriptTemplates.discover_schema(
                api_url=self.executor.sandbox_sf_api_url,
                api_key=self.executor.sf_api_key,
                object_name=object_name
            )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.executor.execute_script(script, f"Get {object_name} schema")
            )

            await self.send_tool_status("get_fields", "completed")

            if result['success'] and result['data']:
                schema = result['data'].get('schema', {})
                fields = schema.get('fields', [])

                response = f"The **{object_name}** object has {len(fields)} fields:\n\n"

                # Show first 10 fields
                for field in fields[:10]:
                    name = field.get('name', 'unknown')
                    field_type = field.get('type', 'unknown')
                    label = field.get('label', name)
                    response += f"- **{name}** ({field_type}): {label}\n"

                if len(fields) > 10:
                    response += f"\n... and {len(fields) - 10} more fields.\n"

                response += f"\nYou can query this object using these fields!"

                await self.send_agent_message(response)
            else:
                await self.send_error(f"Failed to get schema: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Field discovery failed: {str(e)}", exc_info=True)
            await self.send_error(f"Field discovery failed: {str(e)}")

    async def handle_query_request(self, user_message: str):
        """Execute a query based on user request."""
        try:
            await self.send_agent_message("I'll query that data for you...")
            await self.send_tool_status("execute_query", "running")

            # Execute using AgentExecutor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.executor.execute(user_message)
            )

            await self.send_tool_status("execute_query", "completed")

            if result['success']:
                # Send results
                await self.send_result(result)

                # Send summary message
                if result['data']:
                    data = result['data']
                    count = data.get('count', 0)

                    summary = f"I found {count} records. "

                    # Add status breakdown if available
                    if 'status_breakdown' in data:
                        summary += "Here's the breakdown by status:\n\n"
                        for status, status_count in data['status_breakdown'].items():
                            summary += f"- {status}: {status_count}\n"

                    # Add sample leads info
                    if 'leads' in data and data['leads']:
                        summary += f"\nShowing a sample of the results below."

                    await self.send_agent_message(summary)
                else:
                    await self.send_agent_message("Query completed successfully!")

            else:
                await self.send_error(f"Query failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            await self.send_error(f"Query execution failed: {str(e)}")

    async def send_agent_message(self, content: str):
        """Send an agent text message to the frontend."""
        await self._safe_send({
            "type": "agent_message",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Add to history
        self.message_history.append({"role": "assistant", "content": content})

    async def _safe_send(self, data: Dict[str, Any]) -> bool:
        """
        Safely send data via WebSocket, handling disconnection gracefully.

        Returns:
            bool: True if sent successfully, False if WebSocket is closed
        """
        try:
            # Check if WebSocket is still connected
            if self.websocket.client_state.name != "CONNECTED":
                logger.debug(f"Session {self.session_id}: WebSocket not connected, skipping send")
                return False

            await self.websocket.send_json(data)
            return True
        except Exception as e:
            # WebSocket closed during send - this is normal during cleanup
            logger.debug(f"Session {self.session_id}: Failed to send message (WebSocket closed): {e}")
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

    async def send_result(self, result: Dict[str, Any]):
        """Send query results to the frontend."""
        await self._safe_send({
            "type": "result",
            "success": result['success'],
            "data": result.get('data'),
            "description": result.get('description'),
            "timestamp": datetime.now().isoformat()
        })

    async def send_typing(self, is_typing: bool):
        """Send typing indicator to the frontend."""
        await self._safe_send({
            "type": "typing",
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat()
        })

    async def cleanup(self):
        """Clean up the session resources."""
        if self.executor:
            try:
                logger.info(f"Cleaning up session {self.session_id}...")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.executor.close)
                logger.info(f"Session {self.session_id} cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up session {self.session_id}: {str(e)}")


# WebSocket endpoint
@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with the agent.

    Message format from client:
        {"type": "message", "content": "user message"}

    Message formats to client:
        {"type": "agent_message", "content": "agent text"}
        {"type": "status", "content": "status message"}
        {"type": "tool", "tool": "tool_name", "status": "running|completed"}
        {"type": "result", "success": true, "data": {...}}
        {"type": "error", "error": "error message"}
        {"type": "typing", "is_typing": true|false}
    """
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    session = AgentSession(websocket)

    try:
        # Initialize the session
        initialized = await session.initialize()

        if not initialized:
            logger.error("Session initialization failed")
            await websocket.close(code=1011, reason="Failed to initialize agent")
            return

        # Send welcome message
        await session.send_agent_message(
            "Hello! I'm your Salesforce integration assistant. "
            "I can help you query and analyze your Salesforce data. "
            "What would you like to know?"
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
                # Respond to ping to keep connection alive
                try:
                    await websocket.send_json({"type": "pong"})
                except Exception:
                    # WebSocket closed, will be handled by outer exception handler
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
        # Clean up session
        await session.cleanup()
        logger.info(f"Session {session.session_id} closed")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "agent-integration-web-ui",
        "timestamp": datetime.now().isoformat()
    }


# API info endpoint
@app.get("/api/info")
async def api_info():
    """Get API information."""
    return {
        "name": "Agent-Based Integration System",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/chat",
            "health": "/health",
            "info": "/api/info"
        },
        "features": [
            "Real-time WebSocket chat",
            "E2B sandbox execution",
            "Salesforce data discovery",
            "SOQL query execution",
            "Session management"
        ]
    }


# Root endpoint - serve a simple page if no static files
@app.get("/")
async def root():
    """Root endpoint."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agent-Based Integration System</title>
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
        <h1>Agent-Based Integration System</h1>
        <p class="status">✓ Server is running</p>

        <h2>WebSocket Endpoint</h2>
        <div class="endpoint">ws://localhost:8080/chat</div>

        <h2>API Endpoints</h2>
        <div class="endpoint">GET /health - Health check</div>
        <div class="endpoint">GET /api/info - API information</div>

        <h2>Features</h2>
        <ul>
            <li>Real-time WebSocket chat interface</li>
            <li>E2B sandbox execution for secure script running</li>
            <li>Salesforce data discovery and querying</li>
            <li>Session management per connection</li>
        </ul>

        <h2>Getting Started</h2>
        <p>Connect to the WebSocket endpoint to start chatting with the agent.</p>
        <p>Frontend will be available at <code>/static/</code> once created.</p>

        <hr>
        <p><small>Agent-Based Integration System v1.0.0</small></p>
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
    logger.info("Agent-Based Integration System - Web UI Backend")
    logger.info("="*80)
    logger.info("Server starting...")
    logger.info(f"WebSocket endpoint: ws://localhost:8080/chat")
    logger.info(f"Health check: http://localhost:8080/health")
    logger.info(f"API info: http://localhost:8080/api/info")

    # Check for E2B API key
    if not os.getenv('E2B_API_KEY'):
        logger.warning("⚠️  E2B_API_KEY not set! WebSocket connections will fail.")
        logger.warning("   Please set E2B_API_KEY in your .env file")
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
        port=8080,
        reload=True,
        log_level="info"
    )
