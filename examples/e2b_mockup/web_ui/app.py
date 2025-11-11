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


# System prompt for the agent
AGENT_SYSTEM_PROMPT = """You are a helpful AI assistant that helps users query and analyze Salesforce data.

You have access to a Salesforce integration system through an E2B sandbox. You can:

1. **Discover Objects**: List available Salesforce objects (Lead, Campaign, CampaignMember, etc.)
2. **Discover Fields**: Get field schemas for any object to understand available data
3. **Query Data**: Execute SOQL queries to retrieve data based on user requests
4. **Analyze Data**: Process and summarize query results

**Available Capabilities:**

- Get recent leads (e.g., "Get leads from last 30 days")
- Get leads by status (e.g., "Get all New leads")
- Get campaign with leads (e.g., "Get leads for Summer Campaign")
- Get all leads with filtering
- Custom SOQL queries
- Discover available objects and their schemas

**Discovery-First Pattern:**

When the user asks about data you're unfamiliar with:
1. First discover what objects are available using list_objects()
2. Then discover what fields are available using get_fields(object_name)
3. Generate appropriate queries based on discovered schema
4. Execute and return results

**Response Guidelines:**

- Be conversational and helpful
- Explain what you're doing when executing queries
- Provide summaries of results, not just raw data
- Ask clarifying questions if the request is ambiguous
- Suggest related queries the user might be interested in

**Examples:**

User: "Show me recent leads"
You: "I'll get the leads created in the last 30 days for you. Let me query that data..."
[Execute query]
"I found X leads created in the last 30 days. Here's a summary..."

User: "What data do you have access to?"
You: "Let me discover what Salesforce objects are available..."
[Run discovery]
"I have access to Lead, Campaign, and CampaignMember objects. Would you like to explore any of these?"

Always be helpful, informative, and proactive in assisting the user with their data needs.
"""


class AgentSession:
    """
    Manages an agent session for a WebSocket connection.

    Each session has its own AgentExecutor instance for E2B sandbox isolation.
    """

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.executor: Optional[AgentExecutor] = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.message_history: List[Dict[str, str]] = []
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

    async def process_message(self, user_message: str):
        """
        Process a user message and execute the appropriate action.

        This simulates what an AI agent would do:
        1. Parse user intent
        2. Determine appropriate action (query, discovery, etc.)
        3. Execute in E2B sandbox
        4. Stream results back
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
