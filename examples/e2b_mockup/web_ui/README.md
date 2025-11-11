# Web UI Backend

FastAPI-based WebSocket server for real-time agent chat interface.

## Overview

This backend provides a WebSocket API for interacting with the Agent-Based Integration System through a web interface. It integrates with AgentExecutor for E2B sandbox execution and provides real-time streaming of agent responses.

## Architecture

```
Browser (WebSocket Client)
    ↓
FastAPI WebSocket Server (app.py)
    ↓
AgentSession (manages state per connection)
    ↓
AgentExecutor (E2B sandbox orchestration)
    ↓
[E2B Sandbox with Mock API, Driver, Database]
```

## Features

- **WebSocket Chat**: Real-time bidirectional communication
- **Session Management**: Isolated E2B sandbox per WebSocket connection
- **Agent Logic**: Pattern-based intent recognition (production would use Claude API)
- **Streaming Responses**: Progressive updates as agent executes tasks
- **Tool Status**: Real-time feedback on discovery, queries, and execution
- **Error Handling**: Graceful error handling and user feedback

## Installation

Dependencies are already in the main `requirements.txt`:

```bash
# From examples/e2b_mockup/
pip install -r requirements.txt
```

Required packages:
- `fastapi>=0.104.0`
- `uvicorn>=0.24.0`
- `websockets>=12.0`
- `e2b-code-interpreter>=0.0.8`

## Configuration

Set up your `.env` file in `examples/e2b_mockup/`:

```bash
# Required for E2B sandboxes
E2B_API_KEY=your_e2b_api_key_here

# Used inside sandbox (always localhost:8000)
SF_API_URL=http://localhost:8000
SF_API_KEY=test_key_12345
```

## Running the Server

From the `examples/e2b_mockup/` directory:

```bash
# Development mode (auto-reload)
uvicorn web_ui.app:app --reload --port 8080

# Or run directly
python -m web_ui.app
```

Server will start on: `http://localhost:8080`

## API Endpoints

### WebSocket

**Endpoint**: `ws://localhost:8080/chat`

**Client → Server Messages**:

```json
{
  "type": "message",
  "content": "Get leads from last 30 days"
}
```

```json
{
  "type": "ping"
}
```

**Server → Client Messages**:

1. **Agent Message** (conversational text):
```json
{
  "type": "agent_message",
  "content": "I'll query that data for you...",
  "timestamp": "2024-01-01T12:00:00"
}
```

2. **Status Update** (progress info):
```json
{
  "type": "status",
  "content": "Initializing agent environment...",
  "timestamp": "2024-01-01T12:00:00"
}
```

3. **Tool Execution** (tool running/completed):
```json
{
  "type": "tool",
  "tool": "execute_query",
  "status": "running",
  "timestamp": "2024-01-01T12:00:00"
}
```

4. **Query Results** (data returned):
```json
{
  "type": "result",
  "success": true,
  "data": {
    "count": 42,
    "leads": [...],
    "status_breakdown": {...}
  },
  "description": "Get leads from last 30 days",
  "timestamp": "2024-01-01T12:00:00"
}
```

5. **Error** (when something fails):
```json
{
  "type": "error",
  "error": "Query failed: Invalid SOQL",
  "timestamp": "2024-01-01T12:00:00"
}
```

6. **Typing Indicator**:
```json
{
  "type": "typing",
  "is_typing": true,
  "timestamp": "2024-01-01T12:00:00"
}
```

### HTTP Endpoints

**Health Check**: `GET /health`

```json
{
  "status": "healthy",
  "service": "agent-integration-web-ui",
  "timestamp": "2024-01-01T12:00:00"
}
```

**API Info**: `GET /api/info`

```json
{
  "name": "Agent-Based Integration System",
  "version": "1.0.0",
  "endpoints": {...},
  "features": [...]
}
```

**Root**: `GET /`

Returns a simple HTML page with server info.

## Agent Capabilities

The agent can handle:

### 1. Discovery Requests

```
"What objects are available?"
"List all Salesforce objects"
"What data do you have access to?"
```

Response: Lists available objects (Lead, Campaign, CampaignMember) with field counts.

### 2. Field Discovery

```
"What fields does Lead have?"
"Show me Campaign fields"
"Describe the Lead object"
```

Response: Lists all fields with types and labels.

### 3. Query Requests

```
"Get leads from last 30 days"
"Show me all New leads"
"Get leads for Summer Campaign"
"List all leads"
```

Response: Executes query and returns data with summary.

### 4. Help

```
"Help"
"What can you do?"
"Hello"
```

Response: Shows available capabilities.

## Session Management

Each WebSocket connection creates an isolated session:

- **AgentSession**: Manages state for one connection
- **AgentExecutor**: Creates dedicated E2B sandbox per session
- **Message History**: Tracks conversation (not persisted)
- **Cleanup**: Automatically closes sandbox on disconnect

## Example Usage

### Using JavaScript/WebSocket API

```javascript
const ws = new WebSocket('ws://localhost:8080/chat');

// Connection opened
ws.onopen = () => {
  console.log('Connected to agent');
};

// Receive messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'agent_message':
      console.log('Agent:', message.content);
      break;

    case 'status':
      console.log('Status:', message.content);
      break;

    case 'tool':
      console.log(`Tool ${message.tool}: ${message.status}`);
      break;

    case 'result':
      console.log('Results:', message.data);
      break;

    case 'error':
      console.error('Error:', message.error);
      break;

    case 'typing':
      console.log('Agent typing:', message.is_typing);
      break;
  }
};

// Send message
ws.send(JSON.stringify({
  type: 'message',
  content: 'Get leads from last 30 days'
}));

// Keep alive
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

### Using Python websocket-client

```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f"{data['type']}: {data.get('content', data)}")

def on_open(ws):
    print("Connected!")
    ws.send(json.dumps({
        "type": "message",
        "content": "Get leads from last 30 days"
    }))

ws = websocket.WebSocketApp(
    "ws://localhost:8080/chat",
    on_message=on_message,
    on_open=on_open
)

ws.run_forever()
```

## Agent System Prompt

The agent uses a predefined system prompt (see `AGENT_SYSTEM_PROMPT` in `app.py`) that defines:

- Available capabilities
- Discovery-first pattern
- Response guidelines
- Example interactions

In production, this would be used with Claude API for natural language understanding.

## Intent Recognition

Currently uses simple pattern matching:

- **Discovery**: Keywords like "what objects", "list objects", "available objects"
- **Fields**: Keywords like "fields" + object name
- **Queries**: Keywords like "get", "show", "find", "list"
- **Help**: Keywords like "help", "hello", "what can you do"

Production version would use Claude API for robust intent understanding.

## Error Handling

The backend handles errors gracefully:

- Sandbox creation failures
- Query execution errors
- WebSocket disconnections
- Invalid requests

All errors are sent to the client with descriptive messages.

## Development

### Running Tests

```bash
# From examples/e2b_mockup/
pytest test_executor.py -v
```

### Hot Reload

The `--reload` flag enables auto-reload on code changes:

```bash
uvicorn web_ui.app:app --reload --port 8080
```

### Logging

Logs are written to stdout with timestamps:

```
2024-01-01 12:00:00 - web_ui.app - INFO - WebSocket connection accepted
2024-01-01 12:00:01 - web_ui.app - INFO - Session 20240101_120001_123456 initialized
```

## Production Considerations

For production deployment:

1. **Add Claude API Integration**: Replace pattern matching with Claude API for intent recognition
2. **Authentication**: Add user authentication and session persistence
3. **CORS**: Configure specific allowed origins instead of `*`
4. **Rate Limiting**: Add rate limiting per user/session
5. **Monitoring**: Add application monitoring (Sentry, DataDog, etc.)
6. **Database**: Persist conversation history and user data
7. **Scaling**: Use Redis for session management across multiple instances
8. **SSL/TLS**: Enable HTTPS/WSS for secure connections
9. **Resource Limits**: Set timeouts and limits for E2B sandboxes
10. **Caching**: Cache discovery results to reduce E2B calls

## Next Steps

1. Create frontend (`web_ui/static/index.html`)
2. Add Claude API integration for natural language understanding
3. Implement conversation history persistence
4. Add user authentication
5. Deploy to production environment

## Troubleshooting

### WebSocket fails to connect

- Check that E2B_API_KEY is set in `.env`
- Verify server is running on port 8080
- Check firewall settings

### Agent initialization takes long

- E2B sandbox creation takes 5-10 seconds
- Wait for "Agent ready!" message
- Check E2B API status if it times out

### Queries fail

- Check E2B sandbox logs in server output
- Verify Mock API started successfully inside sandbox
- Check SOQL syntax (must use quotes for dates)

## License

Part of the Agent-Based Integration System proof-of-concept.
