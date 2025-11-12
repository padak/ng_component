"""
PostHog Web UI Backend with Claude SDK Integration

FastAPI application with WebSocket support for real-time PostHog analytics chat.
Integrates with PostHogAgentExecutor for E2B sandbox execution.

Features:
- WebSocket endpoint for real-time chat
- Claude Sonnet 4.5 integration with HogQL query generation
- Stream agent responses to frontend
- Execute HogQL scripts in E2B sandboxes
- Session management per WebSocket connection
- Static file serving for frontend

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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

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
    title="PostHog Analytics Agent",
    description="AI-powered PostHog analytics assistant with HogQL query generation",
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


# Claude System Prompt for PostHog
CLAUDE_SYSTEM_PROMPT = """You are an expert PostHog analytics assistant that helps users query and analyze product analytics data through HogQL (PostHog's SQL-like query language).

**Your Capabilities:**

You have access to four powerful tools:

1. **discover_objects**: Lists available PostHog resources (events, persons, cohorts, insights, etc.)
2. **get_object_fields**: Gets the schema for a specific resource (field names, types, descriptions)
3. **execute_posthog_query**: Generates and executes HogQL query scripts to analyze data
4. **show_last_script**: Shows the Python code from the most recent query execution

**Discovery-First Approach:**

When a user asks about data you're unfamiliar with, ALWAYS follow this pattern:

1. Use `discover_objects` to see what resources are available
2. Use `get_object_fields` to understand the schema
3. Use `execute_posthog_query` to generate and run the appropriate HogQL query
4. Present results in a clear, conversational manner with insights

**HogQL Query Guidelines:**

HogQL is PostHog's SQL-like query language. Key features:
- Standard SQL syntax: SELECT, FROM, WHERE, GROUP BY, ORDER BY, LIMIT
- Built-in functions: count(), uniq(), avg(), sum(), min(), max()
- Time functions: now(), toStartOfDay(), INTERVAL
- Event properties: access with properties.property_name
- Person properties: access with person.properties.property_name

**Script Template Structure:**

Every script you generate should follow this pattern:

```python
import sys
sys.path.insert(0, '/home/user')
from posthog_driver.client import PostHogDriver
import json
import os

# Initialize driver (credentials from environment)
driver = PostHogDriver(
    api_url=os.getenv('POSTHOG_HOST'),
    api_key=os.getenv('POSTHOG_API_KEY'),
    project_id=os.getenv('POSTHOG_PROJECT_ID')
)

try:
    # Your HogQL query here
    results = driver.read('''
        SELECT event, count() as total
        FROM events
        WHERE timestamp >= now() - INTERVAL 7 DAY
        GROUP BY event
        ORDER BY total DESC
        LIMIT 10
    ''')

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

**Common HogQL Patterns:**

1. **Event aggregation:**
```sql
SELECT event, count() as event_count
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY event
ORDER BY event_count DESC
```

2. **User activity:**
```sql
SELECT distinct_id, count() as actions
FROM events
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY distinct_id
ORDER BY actions DESC
LIMIT 100
```

3. **Time-based analysis:**
```sql
SELECT toStartOfDay(timestamp) as day, count() as daily_events
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY day
ORDER BY day
```

4. **Property filtering:**
```sql
SELECT event, count() as total
FROM events
WHERE properties.browser = 'Chrome'
  AND timestamp >= now() - INTERVAL 7 DAY
GROUP BY event
```

**Response Style:**

- Be conversational and helpful
- Explain what you're doing when executing tools
- Provide summaries and insights, not just raw data
- Suggest follow-up queries that might be useful
- Highlight trends, anomalies, and key metrics
- **After executing a query successfully, ALWAYS offer to show the Python code**

**Code Transparency:**

After using the `execute_posthog_query` tool successfully:
1. Present the query results with insights
2. Mention that you can show the generated code
3. Say: "Would you like to see the Python script I generated? Just ask 'show me the code'"

**Examples:**

User: "Show me the most popular events in the last week"
You: "I'll query the top events from the past 7 days..."
[Use execute_posthog_query with HogQL]
"I found the top 10 events from the last week. The most popular is 'pageview' with 15,234 occurrences...
Would you like to see the Python script? Just ask 'show me the code'."

User: "What data can I analyze?"
You: "Let me discover what PostHog resources are available..."
[Use discover_objects]
"I have access to: events (user actions), persons (user profiles), cohorts (user groups), and more. Would you like to explore any of these?"

User: "Show the code"
You: "Here's the Python script I executed..."
[Use show_last_script]
"""


# Claude Tools Configuration
CLAUDE_TOOLS = [
    {
        "name": "discover_objects",
        "description": "Discovers all available PostHog resources (events, persons, cohorts, insights, etc.). Use this when you need to understand what data is available in the PostHog project. Returns a list of resource names and their schemas.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_object_fields",
        "description": "Gets the complete field schema for a specific PostHog resource. Use this to understand what fields are available before constructing HogQL queries. Returns detailed field information including types and descriptions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "The name of the PostHog resource (e.g., 'events', 'persons', 'cohorts')"
                }
            },
            "required": ["object_name"]
        }
    },
    {
        "name": "execute_posthog_query",
        "description": "Generates and executes a Python script with HogQL query to analyze PostHog data. You should generate the complete Python code that uses the PostHogDriver to perform the desired analysis. The script will be executed in an E2B sandbox with access to the PostHog driver.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what this query does (e.g., 'Get top events from last 7 days')"
                },
                "python_script": {
                    "type": "string",
                    "description": "Complete Python script to execute. Must import PostHogDriver, initialize it with credentials from environment variables, execute HogQL queries, and print results as JSON."
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
    """Manages an agent session for a WebSocket connection."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.executor: Optional[PostHogAgentExecutor] = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # Claude SDK integration
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_api_key:
            self.claude_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
            self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')

            # Map short names to full IDs
            model_mapping = {
                'claude-sonnet-4-5': 'claude-sonnet-4-5-20250929',
                'claude-sonnet-4': 'claude-sonnet-4-20250514',
                'claude-haiku-4-5': 'claude-haiku-4-5-20251001',
            }
            self.claude_model = model_mapping.get(self.claude_model, self.claude_model)

            # Prompt caching configuration
            caching_env = os.getenv('ENABLE_PROMPT_CACHING', 'true').lower()
            self.enable_prompt_caching = caching_env in ('true', '1', 'yes', 'on')

            logger.info(f"Claude client initialized with model {self.claude_model}, caching={self.enable_prompt_caching}")
        else:
            self.claude_client = None
            logger.warning("No ANTHROPIC_API_KEY - Claude mode disabled")

        # Conversation state
        self.conversation_history: List[Dict[str, Any]] = []
        self.last_executed_script: Optional[str] = None

        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_creation_tokens = 0
        self.total_cache_read_tokens = 0
        self.total_cost = 0.0

        logger.info(f"Created session {self.session_id}")

    async def initialize(self):
        """Initialize the PostHogAgentExecutor (creates E2B sandbox)."""
        try:
            await self.send_status("Initializing PostHog analytics environment...")

            # Create executor in thread pool
            loop = asyncio.get_event_loop()

            def create_executor_with_sandbox():
                executor = PostHogAgentExecutor()
                executor.create_sandbox()
                return executor

            self.executor = await loop.run_in_executor(None, create_executor_with_sandbox)

            # Send success message
            sandbox_id = self.executor.sandbox.sandbox_id
            posthog_host = self.executor.posthog_host
            project_id = self.executor.posthog_project_id

            system_info = (
                f"**E2B Sandbox:** `{sandbox_id}`\n"
                f"**PostHog Project:** {project_id}\n"
                f"**PostHog Host:** {posthog_host}\n"
                f"**PostHog Driver:** Loaded successfully\n"
                f"**Query Language:** HogQL (SQL-like)\n\n"
                f"**Model:** {self.claude_model if self.claude_model else 'Pattern Matching'}\n"
                f"**Prompt Caching:** {'Enabled ✓' if self.enable_prompt_caching else 'Disabled ✗'}\n\n"
                f"**Available Resources:**\n"
                f"- events: User actions and interactions\n"
                f"- persons: User profiles and properties\n"
                f"- cohorts: User segments\n"
                f"- insights: Saved analytics queries"
            )
            await self.send_status(system_info)

            logger.info(f"Session {self.session_id} initialized with sandbox {sandbox_id}")
            return True

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Session {self.session_id}: Initialization failed: {error_msg}", exc_info=True)
            await self.send_error(f"❌ **Failed to initialize agent**: {error_msg}")
            return False

    async def execute_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call from Claude and return the result."""
        try:
            await self.send_tool_status(tool_name, "running")
            loop = asyncio.get_event_loop()

            if tool_name == "discover_objects":
                result = await loop.run_in_executor(None, self.executor.run_discovery)

                objects_summary = []
                for obj_name in result.get('objects', []):
                    schema = result.get('schemas', {}).get(obj_name, {})
                    objects_summary.append({'name': obj_name, 'fields': schema})

                tool_result = {
                    'success': True,
                    'objects': objects_summary,
                    'total_count': len(result.get('objects', []))
                }

            elif tool_name == "get_object_fields":
                object_name = tool_input['object_name']

                script = f"""
import sys
sys.path.insert(0, '/home/user')
from posthog_driver.client import PostHogDriver
import json
import os

driver = PostHogDriver(
    api_url=os.getenv('POSTHOG_HOST'),
    api_key=os.getenv('POSTHOG_API_KEY'),
    project_id=os.getenv('POSTHOG_PROJECT_ID')
)

schema = driver.get_fields('{object_name}')
print(json.dumps(schema, indent=2))
"""

                exec_result = await loop.run_in_executor(
                    None,
                    lambda: self.executor.execute_script(script, f"Get {object_name} schema")
                )

                if exec_result['success']:
                    tool_result = {
                        'success': True,
                        'object_name': object_name,
                        'schema': exec_result.get('data')
                    }
                else:
                    tool_result = {
                        'success': False,
                        'error': exec_result.get('error', 'Unknown error')
                    }

            elif tool_name == "execute_posthog_query":
                description = tool_input['description']
                python_script = tool_input['python_script']

                # Store for show_last_script
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

                # Send result to frontend
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
        """Process user message using Claude API with streaming and tool support."""
        try:
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })

            await self.send_typing(True)

            max_iterations = 15
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                response_text = ""

                # Prepare system prompt
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
                        if event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                text_delta = event.delta.text
                                response_text += text_delta

                                await self._safe_send({
                                    "type": "agent_delta",
                                    "delta": text_delta,
                                    "timestamp": datetime.now().isoformat()
                                })

                    final_message = await stream.get_final_message()

                # Track token usage
                if hasattr(final_message, 'usage') and final_message.usage:
                    usage = final_message.usage
                    self.total_input_tokens += usage.input_tokens
                    self.total_output_tokens += usage.output_tokens

                    # Track cache metrics
                    cache_creation = 0
                    cache_read = 0

                    if hasattr(usage, 'cache_creation') and usage.cache_creation:
                        cache_obj = usage.cache_creation
                        ephemeral_5m = getattr(cache_obj, 'ephemeral_5m_input_tokens', 0) or 0
                        ephemeral_1h = getattr(cache_obj, 'ephemeral_1h_input_tokens', 0) or 0
                        cache_creation = ephemeral_5m + ephemeral_1h

                    if cache_creation == 0:
                        cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0

                    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0

                    self.total_cache_creation_tokens += cache_creation
                    self.total_cache_read_tokens += cache_read

                    # Send usage update
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

                # Check for tool use
                if final_message.stop_reason == "tool_use":
                    tool_results = []

                    for block in final_message.content:
                        if block.type == "tool_use":
                            tool_result = await self.execute_tool_call(block.name, block.input)

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": safe_json_dumps(tool_result)
                            })

                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_message.content
                    })

                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                    continue

                else:
                    # Final response
                    if response_text:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response_text
                        })

                    break

            if iteration >= max_iterations:
                await self.send_agent_message(
                    "⚠️ I reached the maximum number of conversation turns. Please try asking your question again."
                )

            await self.send_typing(False)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Session {self.session_id}: Claude processing failed: {error_msg}", exc_info=True)
            await self.send_error(f"❌ **Unexpected error**: {error_msg}")
            await self.send_typing(False)

    async def process_message(self, user_message: str):
        """Process a user message - routes to Claude."""
        if self.claude_client:
            await self.process_message_with_claude(user_message)
        else:
            await self.send_error("Claude integration not available. Please set ANTHROPIC_API_KEY.")

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
        except Exception as e:
            logger.debug(f"Session {self.session_id}: Failed to send message: {e}")
            return False

    async def send_status(self, status: str):
        """Send a status update."""
        await self._safe_send({
            "type": "status",
            "content": status,
            "timestamp": datetime.now().isoformat()
        })

    async def send_error(self, error: str):
        """Send an error message."""
        await self._safe_send({
            "type": "error",
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    async def send_tool_status(self, tool: str, status: str):
        """Send tool execution status."""
        await self._safe_send({
            "type": "tool",
            "tool": tool,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })

    async def send_result(self, result: Dict[str, Any]):
        """Send query results."""
        await self._safe_send({
            "type": "result",
            "success": result['success'],
            "data": result.get('data'),
            "description": result.get('description'),
            "timestamp": datetime.now().isoformat()
        })

    async def send_typing(self, is_typing: bool):
        """Send typing indicator."""
        await self._safe_send({
            "type": "typing",
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat()
        })

    async def cleanup(self):
        """Clean up session resources."""
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
    """WebSocket endpoint for real-time chat with the PostHog agent."""
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    session = AgentSession(websocket)

    try:
        # Initialize session
        initialized = await session.initialize()

        if not initialized:
            logger.error("Session initialization failed")
            await websocket.close(code=1011, reason="Failed to initialize agent")
            return

        # Send welcome message
        await session.send_agent_message(
            "Hello! I'm your PostHog analytics assistant. "
            "I can help you query and analyze your product analytics data using HogQL. "
            "What would you like to explore?"
        )

        # Main message loop
        while True:
            data = await websocket.receive_json()
            message_type = data.get('type')

            if message_type == 'message':
                content = data.get('content', '').strip()
                if content:
                    logger.info(f"Received message: {content[:100]}...")
                    await session.process_message(content)

            elif message_type == 'ping':
                try:
                    await websocket.send_json({"type": "pong"})
                except Exception:
                    pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session.session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        try:
            await session.send_error(f"Connection error: {str(e)}")
        except:
            pass

    finally:
        await session.cleanup()
        logger.info(f"Session {session.session_id} closed")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "posthog-analytics-agent",
        "timestamp": datetime.now().isoformat()
    }


# API info
@app.get("/api/info")
async def api_info():
    """Get API information."""
    return {
        "name": "PostHog Analytics Agent",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/chat",
            "health": "/health",
            "info": "/api/info"
        },
        "features": [
            "Real-time WebSocket chat",
            "HogQL query execution",
            "E2B sandbox execution",
            "PostHog data discovery",
            "Claude Sonnet 4.5 integration"
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
        <title>PostHog Analytics Agent</title>
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
        <h1>PostHog Analytics Agent</h1>
        <p class="status">✓ Server is running</p>

        <h2>WebSocket Endpoint</h2>
        <div class="endpoint">ws://localhost:8080/chat</div>

        <h2>Features</h2>
        <ul>
            <li>AI-powered PostHog analytics with Claude Sonnet 4.5</li>
            <li>HogQL query generation and execution</li>
            <li>E2B sandbox for secure script execution</li>
            <li>Real-time streaming responses</li>
            <li>Discovery-first approach (no hardcoded schemas)</li>
        </ul>

        <h2>Getting Started</h2>
        <p>Visit <a href="/static/">/static/</a> for the web interface</p>

        <hr>
        <p><small>PostHog Analytics Agent v1.0.0</small></p>
    </body>
    </html>
    """)


# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info(f"Mounted static files from {static_dir}")
else:
    logger.warning(f"Static directory not found: {static_dir}")


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("="*80)
    logger.info("PostHog Analytics Agent - Web UI")
    logger.info("="*80)
    logger.info("Server starting...")
    logger.info(f"WebSocket endpoint: ws://localhost:8080/chat")
    logger.info(f"Web interface: http://localhost:8080/static/")
    logger.info(f"Health check: http://localhost:8080/health")

    # Check environment
    if not os.getenv('E2B_API_KEY'):
        logger.warning("⚠️  E2B_API_KEY not set!")
    else:
        logger.info("✓ E2B_API_KEY found")

    if not os.getenv('ANTHROPIC_API_KEY'):
        logger.warning("⚠️  ANTHROPIC_API_KEY not set!")
    else:
        logger.info("✓ ANTHROPIC_API_KEY found")

    if not os.getenv('POSTHOG_API_KEY'):
        logger.warning("⚠️  POSTHOG_API_KEY not set!")
    else:
        logger.info("✓ POSTHOG_API_KEY found")

    logger.info("="*80)


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Server shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
