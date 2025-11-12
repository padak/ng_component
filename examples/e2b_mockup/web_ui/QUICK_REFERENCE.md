# Web UI - Quick Reference Guide

## File Structure
```
web_ui/
├── app.py                              # Backend (1143 lines)
├── static/
│   └── index.html                      # Frontend (568 lines)
├── test_websocket.py                   # Testing utility
├── WEB_UI_ARCHITECTURE.md              # Detailed architecture (this dir)
├── TOKEN_TRACKING_FLOW.md              # Token flow diagrams
├── CLAUDE_INTEGRATION_SUMMARY.md       # Integration details
├── QUICKSTART.md                       # Quick start guide
└── README.md                           # General documentation
```

## Key Concepts

### Frontend (index.html)
- **Framework:** Tailwind CSS + Vanilla JS
- **Layout:** 2-column grid (chat left, sidebar right)
- **Communication:** WebSocket to `ws://localhost:8080/chat`
- **Streaming:** Uses `marked.js` for Markdown rendering

### Backend (app.py)
- **Framework:** FastAPI + asyncio
- **Claude Integration:** AsyncAnthropic client
- **E2B Integration:** AgentExecutor for sandbox execution
- **Tools:** 4 Claude tools (discover, fields, execute, show_script)

## WebSocket Message Types

### From Client → Server
```
{"type": "message", "content": "user text"}
{"type": "ping"}
```

### From Server → Client
```
{"type": "agent_message", "content": "..."}     # Final message
{"type": "agent_delta", "delta": "I'll"}         # Streaming text
{"type": "status", "content": "..."}             # Status update
{"type": "tool", "tool": "name", "status": "running|completed|failed"}
{"type": "result", "success": true, "data": {...}}
{"type": "error", "error": "message"}
{"type": "usage", "usage": {...}}                # Token metrics
{"type": "typing", "is_typing": true|false}
```

## Claude Tools

1. **discover_objects**
   - Lists available Salesforce objects
   - No inputs
   
2. **get_object_fields**
   - Gets schema for specific object
   - Input: `object_name`
   
3. **execute_salesforce_query**
   - Generates and executes Python scripts
   - Inputs: `description`, `python_script`
   
4. **show_last_script**
   - Shows previously executed code
   - No inputs

## Token Tracking Flow

```
Claude API → Extract usage → Accumulate in session → Send via WebSocket → Update UI
```

### Metrics Tracked
- `input_tokens` - User messages + conversation history
- `output_tokens` - Claude's generated response
- `cache_creation_tokens` - System prompt written to cache (first time)
- `cache_read_tokens` - System prompt read from cache (90% cheaper)

### Display
Frontend shows **cumulative totals** in sidebar:
- Input: Total input tokens across all requests
- Output: Total output tokens across all requests
- Cache Created: One-time write cost (~2000 tokens)
- Cache Read: Cumulative reuses (shows cost savings)
- Total: Input + Output (cache metrics not included)

## Prompt Caching

### Configuration
```python
# Default (enabled)
ENABLE_PROMPT_CACHING=true

# Can disable
ENABLE_PROMPT_CACHING=false
```

### How It Works
- System prompt (~2000 tokens) cached for 5 minutes
- First request: Full cost (write to cache)
- Subsequent requests: 90% discount (read from cache)
- Per-session cache (each WebSocket connection)

### Cost Impact
```
10 requests example (claude-sonnet-4-5):
Without cache: $0.30
With cache: $0.057 (81% savings)
```

## Environment Variables

```bash
# Required
E2B_API_KEY=...                    # E2B sandbox API key
ANTHROPIC_API_KEY=...              # Claude API key

# Optional
CLAUDE_MODEL=claude-sonnet-4-5-20250929  # Model selection
ENABLE_PROMPT_CACHING=true               # Cache toggle
SF_API_URL=http://localhost:8000
SF_API_KEY=test_key_12345
```

## Common Issues & Fixes

### Issue: No streaming visible
**Problem:** `agent_delta` messages received but text not displayed
**Current State:** Frontend only shows "Agent is working..." indicator
**Fix Needed:** Accumulate deltas into visible message element

### Issue: Thinking indicator persists
**Problem:** Agent thinking indicator not removed properly
**Current State:** Only removed in `addAgentMessage()`
**Fix Needed:** Add timeout or better state tracking

### Issue: Can't see per-request token cost
**Problem:** Only cumulative totals displayed
**Current State:** Per-request metrics available but not shown
**Fix Needed:** Add expandable details section in UI

### Issue: Cache hits not visible
**Problem:** No indication when cache is being used
**Current State:** Green `cache_read_tokens` shown but no badge
**Fix Needed:** Add "Cache hit!" indicator when `cache_read_tokens > 0`

## Running the Web UI

```bash
# 1. Set up environment
cd examples/e2b_mockup
cp .env.example .env
# Edit .env with your API keys

# 2. Start backend
cd web_ui
uvicorn app:app --reload --port 8080

# 3. Open frontend
# Browser: http://localhost:8080/static/

# 4. Start testing
# Try: "What objects are available?"
```

## Testing Checklist

- [ ] Can connect to WebSocket
- [ ] Can see connection status indicator
- [ ] Can send messages
- [ ] Agent responds with Markdown formatting
- [ ] Tool execution shows status indicators
- [ ] Token usage updates in sidebar
- [ ] Multiple conversations accumulate tokens
- [ ] Cache metrics show when available
- [ ] Fallback to pattern matching if no API key

## Message Handler Flow

```
handleMessage(data)
  ├─ agent_message → addAgentMessage()
  ├─ agent_delta → showWorkingIndicator() [BUG: not accumulating]
  ├─ status → updateSystemInfo()
  ├─ tool → addToolUseIndicator()
  ├─ result → addExecutionResult()
  ├─ error → addErrorMessage()
  ├─ usage → updateTokenUsage()
  ├─ typing → show/hideWorkingIndicator()
  └─ pong → [keep-alive]
```

## Backend Processing Flow

```
receive_json()
  ↓
process_message()
  ├─ (Claude available) → process_message_with_claude()
  │   ├─ Stream from Claude
  │   ├─ Send agent_delta for each text chunk
  │   ├─ Execute tools if needed
  │   ├─ Track token usage
  │   ├─ Send usage message
  │   └─ Send final agent_message
  │
  └─ (Claude unavailable) → process_message_with_patterns()
      └─ Original pattern-matching logic
```

## Key Code Locations

| What | Where |
|------|-------|
| System Prompt | app.py:69-154 |
| Tool Definitions | app.py:157-208 |
| Token Tracking Init | app.py:249-253 |
| Prompt Caching Config | app.py:475-487 |
| Token Tracking Logic | app.py:515-541 |
| Tool Execution | app.py:309-447 |
| WebSocket Handler | app.py:918-998 |
| Token Display (UI) | index.html:168-192 |
| Usage Update (UI) | index.html:462-472 |
| Tool Indicator (UI) | index.html:352-379 |
| Message Handling (UI) | index.html:265-304 |

## Architecture Principles

1. **Discovery-First:** Agent discovers schema before generating queries
2. **Streaming:** Real-time token-by-token responses (implemented on backend, not fully used on frontend)
3. **Tool-Based:** All system interactions go through Claude tools
4. **Cached Efficiency:** System prompt cached for 5-minute sessions
5. **Graceful Fallback:** Pattern matching available if Claude unavailable
6. **Session Isolation:** Each WebSocket connection is independent
7. **Async/Await:** Non-blocking execution with thread pools for I/O

## Performance Notes

- First Claude request: 2-3 seconds (includes cache write)
- Subsequent requests: 1-2 seconds (uses cache)
- Tool execution: 2-5 seconds (depends on E2B sandbox)
- Total response time: 5-15 seconds for complex queries
- Cache benefit: 90% cost reduction on system prompt (~2000 tokens)

## Next Steps for Enhancement

### High Priority
1. Implement agent_delta accumulation for true streaming UX
2. Add cache hit indicators
3. Display per-request token breakdown

### Medium Priority
4. Add tool execution timing
5. Improve error message formatting
6. Better thinking indicator management

### Low Priority
7. Add conversation export
8. Add token cost calculator
9. Add request history UI

