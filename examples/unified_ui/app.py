"""
Unified Data Analytics Agent - Web UI Backend

FastAPI application with WebSocket support for multi-datasource analytics chat.
Supports both Salesforce (via AgentExecutor) and PostHog (via PostHogAgentExecutor).

Features:
- WebSocket endpoint for real-time chat
- Multi-data source support (Salesforce, PostHog)
- Claude Sonnet 4.5 integration with dynamic query generation
- Stream agent responses to frontend
- Execute scripts in E2B sandboxes
- Session management per WebSocket connection
- Data source switching mid-conversation

Usage:
    uvicorn app:app --reload --port 8080
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

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "e2b_mockup"))
sys.path.insert(0, str(Path(__file__).parent.parent / "posthog_ui"))

from agent_executor import AgentExecutor
from posthog_agent_executor import PostHogAgentExecutor

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# JSON serialization helper
def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize objects to JSON, handling datetime, Decimal, and other non-standard types."""
    def json_serializer(o):
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
        return json.dumps({"error": "serialization_failed", "message": str(e), "data": str(obj)[:1000]})


# Create FastAPI app
app = FastAPI(
    title="Unified Data Analytics Agent",
    description="AI-powered multi-datasource analytics assistant (Salesforce + PostHog)",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# System prompts for different data sources
SALESFORCE_SYSTEM_PROMPT = """You are an expert Salesforce integration assistant that helps users query and analyze CRM data through SOQL (Salesforce Object Query Language).

**Your Capabilities:**

You have access to four powerful tools:

1. **discover_objects**: Lists available Salesforce objects (Lead, Account, Opportunity, etc.)
2. **get_object_fields**: Gets the schema for a specific object (field names, types, descriptions)
3. **execute_salesforce_query**: Generates and executes SOQL query scripts to retrieve data
4. **show_last_script**: Shows the Python code from the most recent query execution

**Your Workflow:**

1. **Discover First**: When a user asks about data you're not familiar with, use discover_objects and get_object_fields to understand what's available
2. **Analyze Request**: Understand what the user wants (filtering, sorting, aggregation, etc.)
3. **Generate Query**: Create precise SOQL queries based on discovered schema
4. **Execute & Present**: Run the query and present results with insights
5. **Show Code**: If requested, display the generated Python script

**Important Guidelines:**

- **Always discover before querying**: Never assume field names - use get_object_fields to see actual schema
- **Be precise**: Use exact field names from schema discovery
- **Handle errors gracefully**: If a query fails, explain why and suggest corrections
- **Provide insights**: Don't just return raw data - analyze and summarize findings
- **Show your work**: When asked, use show_last_script to display generated code

**SOQL Best Practices:**

- Use `SELECT field1, field2 FROM Object` syntax
- Filter with `WHERE` clause (e.g., `WHERE Status = 'Open'`)
- Sort with `ORDER BY` clause (e.g., `ORDER BY CreatedDate DESC`)
- Limit results with `LIMIT` (e.g., `LIMIT 100`)
- Date fields use format: `WHERE CreatedDate >= 2024-01-01`

**Communication Style:**

- Be conversational and helpful
- Explain technical details in simple terms
- Ask clarifying questions when requests are ambiguous
- Provide actionable insights from data
- Use markdown formatting for better readability

Remember: You're a helpful assistant that combines technical expertise with clear communication. Always prioritize accuracy and user understanding."""

POSTHOG_SYSTEM_PROMPT = """You are an expert PostHog analytics assistant that helps users query and analyze product analytics data through HogQL (PostHog's SQL-like query language).

**Your Capabilities:**

You have access to four powerful tools:

1. **discover_objects**: Lists available PostHog resources (events, persons, cohorts, insights, etc.)
2. **get_object_fields**: Gets the schema for a specific resource (field names, types, descriptions)
3. **execute_posthog_query**: Generates and executes HogQL query scripts to analyze data
4. **show_last_script**: Shows the Python code from the most recent query execution

**Your Workflow:**

1. **Discover First**: When a user asks about data you're not familiar with, use discover_objects and get_object_fields to understand what's available
2. **Analyze Request**: Understand what the user wants (event analysis, user behavior, trends, etc.)
3. **Generate Query**: Create precise HogQL queries based on discovered schema
4. **Execute & Present**: Run the query and present results with analytics insights
5. **Show Code**: If requested, display the generated Python script

**Important Guidelines:**

- **Always discover before querying**: Never assume field names - use get_object_fields to see actual schema
- **Be precise**: Use exact field names from schema discovery
- **Handle errors gracefully**: If a query fails, explain why and suggest corrections
- **Provide insights**: Don't just return raw data - analyze trends and patterns
- **Show your work**: When asked, use show_last_script to display generated code

**HogQL Best Practices:**

- Use `SELECT field1, field2 FROM events` syntax
- Filter with `WHERE` clause (e.g., `WHERE event = 'pageview'`)
- Aggregate with functions: `count()`, `sum()`, `avg()`, `uniq()`
- Group with `GROUP BY` (e.g., `GROUP BY event`)
- Time intervals: `now() - INTERVAL 7 DAY`, `now() - INTERVAL 30 DAY`
- Date functions: `toStartOfDay(timestamp)`, `toStartOfWeek(timestamp)`

**Communication Style:**

- Be conversational and analytical
- Explain metrics and trends clearly
- Ask clarifying questions when requests are ambiguous
- Provide actionable product insights from data
- Use markdown formatting for better readability

Remember: You're a helpful assistant that combines analytics expertise with clear communication. Always prioritize accuracy and user understanding."""


# Claude tools definitions for Salesforce
SALESFORCE_TOOLS = [
    {
        "name": "discover_objects",
        "description": "Discovers all available Salesforce objects (like Lead, Account, Opportunity, etc.). Use this first when you need to understand what data is available.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_object_fields",
        "description": "Gets the complete schema for a specific Salesforce object, including all field names, types, and metadata. Use this to see what fields are available before writing SOQL queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "The name of the Salesforce object (e.g., 'Lead', 'Account', 'Opportunity')"
                }
            },
            "required": ["object_name"]
        }
    },
    {
        "name": "execute_salesforce_query",
        "description": "Generates and executes a Python script with SOQL query to retrieve Salesforce data. Returns the query results as JSON. Use after discovering schema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A human-readable description of what this query does (e.g., 'Get all open leads from last 30 days')"
                },
                "soql_query": {
                    "type": "string",
                    "description": "The SOQL query to execute (e.g., 'SELECT Id, Name, Email FROM Lead WHERE Status = \"Open\" LIMIT 100')"
                }
            },
            "required": ["description", "soql_query"]
        }
    },
    {
        "name": "show_last_script",
        "description": "Shows the Python code that was generated and executed for the last query. Use when user asks to see the code or script.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


# Claude tools definitions for PostHog
POSTHOG_TOOLS = [
    {
        "name": "discover_objects",
        "description": "Discovers all available PostHog resources (like events, persons, cohorts, insights, etc.). Use this first when you need to understand what data is available.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_object_fields",
        "description": "Gets the complete schema for a specific PostHog resource, including all field names, types, and metadata. Use this to see what fields are available before writing HogQL queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "The name of the PostHog resource (e.g., 'events', 'persons', 'sessions')"
                }
            },
            "required": ["object_name"]
        }
    },
    {
        "name": "execute_posthog_query",
        "description": "Generates and executes a Python script with HogQL query to analyze PostHog data. Returns the query results as JSON. Use after discovering schema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A human-readable description of what this query does (e.g., 'Get top 10 events from last week')"
                },
                "hogql_query": {
                    "type": "string",
                    "description": "The HogQL query to execute (e.g., 'SELECT event, count() as total FROM events WHERE timestamp >= now() - INTERVAL 7 DAY GROUP BY event ORDER BY total DESC LIMIT 10')"
                }
            },
            "required": ["description", "hogql_query"]
        }
    },
    {
        "name": "show_last_script",
        "description": "Shows the Python code that was generated and executed for the last query. Use when user asks to see the code or script.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


class ChatSession:
    """Manages a single chat session with Claude and executor."""

    def __init__(self, session_id: str, data_source: str):
        self.session_id = session_id
        self.data_source = data_source
        self.executor = None
        self.conversation_history = []
        self.last_script = None
        self.claude_client = None
        self.system_prompt = None
        self.tools = None

        # Initialize Claude client if API key is available
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_api_key:
            claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
            enable_caching = os.getenv('ENABLE_PROMPT_CACHING', 'true').lower() == 'true'

            self.claude_client = anthropic.Anthropic(api_key=anthropic_api_key)
            logger.info(f"Claude client initialized with model {claude_model}, caching={enable_caching}")
        else:
            logger.warning("No ANTHROPIC_API_KEY - Claude mode disabled")

        # Set system prompt and tools based on data source
        self._configure_data_source(data_source)

        logger.info(f"Created session {session_id} with data source {data_source}")

    def _configure_data_source(self, data_source: str):
        """Configure system prompt, tools, and executor for the selected data source."""
        if data_source == "salesforce":
            self.system_prompt = SALESFORCE_SYSTEM_PROMPT
            self.tools = SALESFORCE_TOOLS
        elif data_source == "posthog":
            self.system_prompt = POSTHOG_SYSTEM_PROMPT
            self.tools = POSTHOG_TOOLS
        else:
            raise ValueError(f"Unknown data source: {data_source}")

        logger.info(f"Configured for {data_source} data source")

    async def initialize(self):
        """Initialize the executor (creates E2B sandbox)."""
        loop = asyncio.get_event_loop()

        def create_executor_with_sandbox():
            """Create executor and sandbox in thread pool."""
            if self.data_source == "salesforce":
                executor = AgentExecutor()
            elif self.data_source == "posthog":
                executor = PostHogAgentExecutor()
            else:
                raise ValueError(f"Unknown data source: {self.data_source}")

            executor.create_sandbox()
            return executor

        try:
            self.executor = await loop.run_in_executor(None, create_executor_with_sandbox)
            logger.info(f"Session {self.session_id} initialized with sandbox {self.executor.sandbox.sandbox_id}")
        except Exception as e:
            logger.error(f"Session {self.session_id}: Initialization failed: {e}")
            raise

    async def switch_data_source(self, new_data_source: str):
        """Switch to a different data source."""
        if new_data_source == self.data_source:
            return {"message": f"Already using {new_data_source}"}

        logger.info(f"Switching from {self.data_source} to {new_data_source}")

        # Close current executor
        if self.executor:
            await self.close()

        # Reconfigure for new data source
        self.data_source = new_data_source
        self._configure_data_source(new_data_source)

        # Reset conversation history
        self.conversation_history = []
        self.last_script = None

        # Initialize new executor
        await self.initialize()

        return {"message": f"Switched to {new_data_source}", "data_source": new_data_source}

    async def handle_message(self, message: str):
        """Handle user message and stream Claude's response."""
        if not self.claude_client:
            yield {"type": "error", "content": "Claude API not configured"}
            return

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })

        # Call Claude with streaming
        try:
            enable_caching = os.getenv('ENABLE_PROMPT_CACHING', 'true').lower() == 'true'
            claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')

            # Prepare system prompt with caching if enabled
            system_messages = []
            if enable_caching:
                system_messages.append({
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"}
                })
            else:
                system_messages.append({
                    "type": "text",
                    "text": self.system_prompt
                })

            with self.claude_client.messages.stream(
                model=claude_model,
                max_tokens=4096,
                system=system_messages,
                tools=self.tools,
                messages=self.conversation_history,
            ) as stream:
                assistant_message = {"role": "assistant", "content": []}

                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "text":
                            yield {"type": "text_start"}

                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield {"type": "text_delta", "content": event.delta.text}
                            # Add to assistant message
                            if not assistant_message["content"] or assistant_message["content"][-1].get("type") != "text":
                                assistant_message["content"].append({"type": "text", "text": ""})
                            assistant_message["content"][-1]["text"] += event.delta.text

                    elif event.type == "content_block_stop":
                        pass

                    elif event.type == "message_delta":
                        if event.delta.stop_reason == "tool_use":
                            # Claude wants to use a tool
                            pass

                # Get final message
                final_message = stream.get_final_message()

                # Handle tool use
                if final_message.stop_reason == "tool_use":
                    # Add assistant message to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_message.content
                    })

                    # Execute tools
                    tool_results = []
                    for block in final_message.content:
                        if block.type == "tool_use":
                            yield {"type": "tool_use", "tool": block.name, "input": block.input}

                            # Execute tool
                            result = await self._execute_tool(block.name, block.input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": safe_json_dumps(result)
                            })

                            yield {"type": "tool_result", "tool": block.name, "result": result}

                    # Add tool results to history
                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                    # Continue conversation with tool results
                    async for chunk in self.handle_message(""):  # Empty message triggers continuation
                        yield chunk

                elif final_message.stop_reason == "end_turn":
                    # Add final assistant message to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_message.content
                    })

                    yield {"type": "done", "stop_reason": "end_turn"}

        except Exception as e:
            logger.error(f"Error in Claude conversation: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}

    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        try:
            if tool_name == "discover_objects":
                return await self._discover_objects()
            elif tool_name == "get_object_fields":
                return await self._get_object_fields(tool_input["object_name"])
            elif tool_name in ["execute_salesforce_query", "execute_posthog_query"]:
                return await self._execute_query(tool_input)
            elif tool_name == "show_last_script":
                return await self._show_last_script()
            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
            return {"error": str(e)}

    async def _discover_objects(self) -> Dict[str, Any]:
        """Discover available objects."""
        loop = asyncio.get_event_loop()

        if self.data_source == "salesforce":
            result = await loop.run_in_executor(None, self.executor.run_discovery)
        elif self.data_source == "posthog":
            result = await loop.run_in_executor(None, self.executor.run_discovery)

        return result

    async def _get_object_fields(self, object_name: str) -> Dict[str, Any]:
        """Get fields for a specific object."""
        loop = asyncio.get_event_loop()

        def get_fields():
            if self.data_source == "salesforce":
                from salesforce_driver.client import SalesforceClient
                client = SalesforceClient(
                    api_url=os.getenv('SF_API_URL', 'http://localhost:8000'),
                    api_key=os.getenv('SF_API_KEY', 'test_key')
                )
                return client.get_fields(object_name)
            elif self.data_source == "posthog":
                script = f"""
import sys
sys.path.insert(0, '/home/user')
from posthog_driver.client import PostHogDriver
import json

driver = PostHogDriver(
    api_url='{os.getenv("POSTHOG_HOST")}',
    api_key='{os.getenv("POSTHOG_API_KEY")}',
    project_id='{os.getenv("POSTHOG_PROJECT_ID")}'
)

fields = driver.get_fields('{object_name}')
print(json.dumps(fields, indent=2))
"""
                result = self.executor.execute_script(script, f"Get fields for {object_name}")
                if result['success']:
                    return result['data']
                else:
                    return {"error": result.get('error', 'Unknown error')}

        return await loop.run_in_executor(None, get_fields)

    async def _execute_query(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a query."""
        loop = asyncio.get_event_loop()

        description = tool_input.get('description', 'Execute query')

        if self.data_source == "salesforce":
            soql_query = tool_input.get('soql_query', '')

            def execute_sf():
                script = self.executor.templates.generate_query_script(
                    description=description,
                    soql_query=soql_query
                )
                self.last_script = script
                return self.executor.execute_script(script, description)

            return await loop.run_in_executor(None, execute_sf)

        elif self.data_source == "posthog":
            hogql_query = tool_input.get('hogql_query', '')

            def execute_ph():
                script = f"""
import sys
sys.path.insert(0, '/home/user')
from posthog_driver.client import PostHogDriver
import json

driver = PostHogDriver(
    api_url='{os.getenv("POSTHOG_HOST")}',
    api_key='{os.getenv("POSTHOG_API_KEY")}',
    project_id='{os.getenv("POSTHOG_PROJECT_ID")}'
)

results = driver.read('''
{hogql_query}
''')

print(json.dumps({{'count': len(results), 'results': results}}, indent=2))
"""
                self.last_script = script
                result = self.executor.execute_script(script, description)
                return result

            return await loop.run_in_executor(None, execute_ph)

    async def _show_last_script(self) -> Dict[str, Any]:
        """Show the last executed script."""
        if self.last_script:
            return {"script": self.last_script}
        else:
            return {"message": "No script has been executed yet"}

    async def close(self):
        """Clean up session resources."""
        if self.executor:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.executor.close)
        logger.info(f"Session {self.session_id} closed")


# Session management
sessions: Dict[str, ChatSession] = {}


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    static_path = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_path), html=True), name="static")
    logger.info(f"Mounted static files from {static_path}")

    logger.info("=" * 80)
    logger.info("Unified Data Analytics Agent - Web UI")
    logger.info("=" * 80)
    logger.info("Server starting...")
    logger.info("WebSocket endpoint: ws://localhost:8080/chat")
    logger.info("Web interface: http://localhost:8080/static/")
    logger.info("Health check: http://localhost:8080/health")

    # Check environment variables
    e2b_key = os.getenv('E2B_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    posthog_key = os.getenv('POSTHOG_API_KEY')
    sf_key = os.getenv('SF_API_KEY')

    if e2b_key:
        logger.info("✓ E2B_API_KEY found")
    else:
        logger.warning("⚠️  E2B_API_KEY not set!")

    if anthropic_key:
        logger.info("✓ ANTHROPIC_API_KEY found")
    else:
        logger.warning("⚠️  ANTHROPIC_API_KEY not set!")

    if posthog_key:
        logger.info("✓ POSTHOG_API_KEY found")
    else:
        logger.warning("⚠️  POSTHOG_API_KEY not set (PostHog queries will fail)")

    if sf_key:
        logger.info("✓ SF_API_KEY found")
    else:
        logger.warning("⚠️  SF_API_KEY not set (Salesforce queries will use default)")

    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up all sessions on shutdown."""
    logger.info("Server shutting down...")
    for session in sessions.values():
        await session.close()


@app.get("/")
async def root():
    """Redirect to static UI."""
    return HTMLResponse("<script>window.location.href='/static/'</script>")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "sessions": len(sessions),
        "data_sources": ["salesforce", "posthog"]
    }


@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat."""
    await websocket.accept()
    session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    session = None

    try:
        logger.info("WebSocket connection accepted")

        # Wait for initial data source selection
        init_message = await websocket.receive_json()
        data_source = init_message.get("data_source", "salesforce")

        # Create session
        session = ChatSession(session_id, data_source)
        sessions[session_id] = session

        # Send initialization start message
        await websocket.send_json({
            "type": "status",
            "content": f"Initializing {data_source} agent..."
        })

        # Initialize session (creates E2B sandbox)
        await session.initialize()

        # Send ready message
        await websocket.send_json({
            "type": "ready",
            "session_id": session_id,
            "data_source": data_source,
            "message": f"Connected to {data_source}! Ask me anything about your data."
        })

        # Handle messages
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "switch_source":
                # Handle data source switch
                new_source = data.get("data_source")
                await websocket.send_json({
                    "type": "status",
                    "content": f"Switching to {new_source}..."
                })

                result = await session.switch_data_source(new_source)

                await websocket.send_json({
                    "type": "source_switched",
                    "data_source": new_source,
                    "message": result["message"]
                })

            elif data.get("type") == "message":
                # Handle chat message
                message = data.get("content", "")

                # Stream response
                async for chunk in session.handle_message(message):
                    await websocket.send_json(chunk)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Unexpected error: {str(e)}"
            })
        except:
            pass

    finally:
        # Clean up session
        if session:
            logger.info(f"Cleaning up session {session_id}...")
            await session.close()
            sessions.pop(session_id, None)
