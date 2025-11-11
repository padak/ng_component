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

**Examples:**

User: "Show me recent leads"
You: "I'll query the leads created recently. Let me fetch that data..."
[Use execute_salesforce_query with script to get leads from last 30 days]
"I found 45 leads created in the last 30 days. The most common status is 'New' with 28 leads..."

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
            logger.info(f"Claude async client initialized for session {self.session_id}")
        else:
            self.claude_client = None
            logger.warning(f"No ANTHROPIC_API_KEY - Claude mode disabled for session {self.session_id}")

        # Conversation state for Claude
        self.conversation_history: List[Dict[str, Any]] = []
        self.last_executed_script: Optional[str] = None

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

            # Send detailed initialization success message
            sandbox_id = self.executor.sandbox.sandbox_id
            await self.send_status(f"Agent ready! (Sandbox: {sandbox_id})")

            # Send welcome message with system info
            import os
            welcome_msg = (
                "**System Information:**\n\n"
                f"**E2B Sandbox:** `{sandbox_id}`\n"
                f"**Database:** DuckDB with 180 test records\n"
                f"**Salesforce Driver:** Loaded successfully\n"
                f"**Mock API:** Running on `localhost:8000` (inside sandbox)\n"
                f"**Available Objects:** Account, Lead, Opportunity\n\n"
                f"**Environment:**\n"
                f"- `SF_API_URL`: {self.executor.sandbox_sf_api_url}\n"
                f"- `SF_API_KEY`: {'*' * 8} (configured)\n"
                f"- `E2B_API_KEY`: {'*' * 8} (configured)\n\n"
                "Ready to query your Salesforce data! Try asking:\n"
                "- 'Get all leads'\n"
                "- 'Show me leads from last 30 days'\n"
                "- 'What objects are available?'"
            )
            await self.send_agent_message(welcome_msg)

            logger.info(f"Session {self.session_id} initialized with sandbox {sandbox_id}")

            return True

        except Exception as e:
            error_msg = f"Failed to initialize agent: {str(e)}"
            logger.error(f"Session {self.session_id}: {error_msg}")
            await self.send_error(error_msg)
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

        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            await self.send_tool_status(tool_name, "failed")
            return {
                'success': False,
                'error': str(e)
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
            max_iterations = 5  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Create streaming request
                response_text = ""

                async with self.claude_client.messages.stream(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=4096,
                    system=CLAUDE_SYSTEM_PROMPT,
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
                                await self.websocket.send_json({
                                    "type": "agent_delta",
                                    "delta": text_delta,
                                    "timestamp": datetime.now().isoformat()
                                })

                    # Get final message
                    final_message = await stream.get_final_message()

                # Check if Claude wants to use tools
                if final_message.stop_reason == "tool_use":

                    # Execute each tool call
                    tool_results = []

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

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": json.dumps(tool_result)
                            })

                    # Add assistant message and tool results to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_message.content
                    })

                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                    # Continue loop to get Claude's response to tool results
                    continue

                else:
                    # No more tools - final response received

                    # Add complete response to history
                    if response_text:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response_text
                        })

                        # Send complete message
                        await self.send_agent_message(response_text)

                    break

            await self.send_typing(False)

        except anthropic.APIStatusError as e:
            # Handle specific API errors with user-friendly messages
            error_type = getattr(e, 'type', None) or (e.response.json() if hasattr(e, 'response') else {}).get('error', {}).get('type')

            if 'overloaded' in str(e).lower() or error_type == 'overloaded_error':
                user_msg = (
                    "⚠️ Claude API is temporarily overloaded (high traffic). "
                    "Please wait 30-60 seconds and try again. Your session is still active."
                )
            elif e.status_code == 429:
                user_msg = "⚠️ Rate limit reached. Please wait a moment and try again."
            elif e.status_code == 401:
                user_msg = "❌ Authentication error. Please check your ANTHROPIC_API_KEY."
            else:
                user_msg = f"❌ Claude API error ({e.status_code}): {str(e)}"

            logger.warning(f"Claude API error: {str(e)}")
            await self.send_error(user_msg)
            await self.send_typing(False)

        except Exception as e:
            logger.error(f"Claude processing failed: {str(e)}", exc_info=True)
            await self.send_error(f"Error processing message: {str(e)}")
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
        await self.websocket.send_json({
            "type": "agent_message",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Add to history
        self.message_history.append({"role": "assistant", "content": content})

    async def send_status(self, status: str):
        """Send a status update to the frontend."""
        await self.websocket.send_json({
            "type": "status",
            "content": status,
            "timestamp": datetime.now().isoformat()
        })

    async def send_error(self, error: str):
        """Send an error message to the frontend."""
        await self.websocket.send_json({
            "type": "error",
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    async def send_tool_status(self, tool: str, status: str):
        """Send tool execution status to the frontend."""
        await self.websocket.send_json({
            "type": "tool",
            "tool": tool,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })

    async def send_result(self, result: Dict[str, Any]):
        """Send query results to the frontend."""
        await self.websocket.send_json({
            "type": "result",
            "success": result['success'],
            "data": result.get('data'),
            "description": result.get('description'),
            "timestamp": datetime.now().isoformat()
        })

    async def send_typing(self, is_typing: bool):
        """Send typing indicator to the frontend."""
        await self.websocket.send_json({
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
                await websocket.send_json({"type": "pong"})

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
