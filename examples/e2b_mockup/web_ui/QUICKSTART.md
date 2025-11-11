# Web UI Quick Start Guide

Get the Agent-Based Integration System Web UI running in 5 minutes.

## Prerequisites

1. **E2B API Key**: Get one at [e2b.dev](https://e2b.dev)
2. **Python 3.8+**
3. **Dependencies installed** (from `examples/e2b_mockup/requirements.txt`)

## Step 1: Set Up Environment

Create a `.env` file in `examples/e2b_mockup/`:

```bash
# Required for E2B sandboxes
E2B_API_KEY=your_e2b_api_key_here

# Used inside sandbox (always localhost:8000)
SF_API_URL=http://localhost:8000
SF_API_KEY=test_key_12345
```

## Step 2: Install Dependencies

```bash
cd examples/e2b_mockup
pip install -r requirements.txt
```

## Step 3: Start the Server

```bash
# From examples/e2b_mockup/
uvicorn web_ui.app:app --reload --port 8080
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using StatReload
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
================================================================================
Agent-Based Integration System - Web UI Backend
================================================================================
Server starting...
WebSocket endpoint: ws://localhost:8080/chat
Health check: http://localhost:8080/health
API info: http://localhost:8080/api/info
✓ E2B_API_KEY found
================================================================================
INFO:     Application startup complete.
```

## Step 4: Open the Web UI

Open your browser to:

```
http://localhost:8080/static/
```

You should see the **Salesforce Integration Designer** interface.

## Step 5: Start Chatting!

The agent will initialize (takes ~10 seconds to create E2B sandbox). Once you see "Agent ready!", try these queries:

### Example Queries

1. **Discovery**:
   ```
   What objects are available?
   ```

2. **Field Discovery**:
   ```
   What fields does Lead have?
   ```

3. **Get Recent Leads**:
   ```
   Get leads from last 30 days
   ```

4. **Filter by Status**:
   ```
   Show me all New leads
   ```

5. **Campaign Data**:
   ```
   Get leads for Summer Campaign
   ```

6. **Help**:
   ```
   What can you do?
   ```

## Troubleshooting

### Server won't start

**Error**: `E2B_API_KEY not set`
- **Solution**: Add `E2B_API_KEY=your_key` to `.env` file

**Error**: `ModuleNotFoundError: No module named 'fastapi'`
- **Solution**: Run `pip install -r requirements.txt`

### WebSocket connection fails

**Status**: "Disconnected" in UI
- **Check**: Server is running on port 8080
- **Check**: Browser console for errors (F12 → Console)
- **Check**: Firewall allows port 8080

### Agent initialization takes too long

**Status**: "Initializing agent environment..." for > 30 seconds
- **Check**: E2B API key is valid
- **Check**: Internet connection is working
- **Check**: E2B service status at [status.e2b.dev](https://status.e2b.dev)

### Queries fail

**Error**: "Query failed: ..."
- **Check**: Server logs for detailed error
- **Check**: SOQL syntax (dates need quotes: `'2024-01-01'`)
- **Try**: Simpler query first: "Get all leads"

## Testing the Backend

Test the WebSocket backend without the UI:

```bash
# From examples/e2b_mockup/
python web_ui/test_websocket.py
```

This will:
1. Connect to the WebSocket
2. Wait for initialization
3. Send a test query
4. Display all messages
5. Verify complete flow

## Development Mode

### Auto-reload on changes

The `--reload` flag enables automatic reload when you modify code:

```bash
uvicorn web_ui.app:app --reload --port 8080
```

### View logs

Server logs show all activity:

```
INFO:     WebSocket connection accepted
INFO:     Created session 20241110_120000_123456
INFO:     Session 20241110_120000_123456 initialized with sandbox sbx_abc123
INFO:     Received message: Get leads from last 30 days...
```

### Check health

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "service": "agent-integration-web-ui",
  "timestamp": "2024-11-10T12:00:00"
}
```

## Architecture Overview

```
Browser
    ↓ WebSocket (ws://localhost:8080/chat)
FastAPI Server (app.py)
    ↓
AgentSession (per connection)
    ↓
AgentExecutor
    ↓
E2B Sandbox (isolated VM)
    ├── Mock API (localhost:8000)
    ├── DuckDB (salesforce.duckdb)
    └── Salesforce Driver
```

## What Happens When You Send a Message

1. **Browser** sends WebSocket message:
   ```json
   {"type": "message", "content": "Get leads from last 30 days"}
   ```

2. **Server** receives and parses intent (pattern matching)

3. **AgentSession** determines action needed (discovery, query, etc.)

4. **AgentExecutor** generates Python script from template

5. **E2B Sandbox** executes script:
   - Script imports Salesforce driver
   - Connects to Mock API at localhost:8000
   - Queries DuckDB database
   - Returns results as JSON

6. **Server** sends results back to browser:
   ```json
   {"type": "result", "success": true, "data": {...}}
   ```

7. **Browser** displays formatted results

## Tips

- **Session isolation**: Each browser tab gets its own E2B sandbox
- **Conversation history**: Not persisted (resets on disconnect)
- **Sandbox lifecycle**: Created on connect, destroyed on disconnect
- **Keep-alive**: Ping/pong messages keep connection alive
- **Timeout**: Sandbox auto-closes after disconnect

## Next Steps

- Explore different query patterns
- Try filtering by status, date ranges, campaigns
- Discover available objects and fields
- Check server logs to see E2B execution details

## Support

For issues:
1. Check server logs for errors
2. Check browser console (F12) for WebSocket errors
3. Test with `test_websocket.py` to isolate issues
4. Verify E2B API key is valid

Enjoy exploring the Agent-Based Integration System! 🚀
