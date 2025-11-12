# Web UI Architecture - Detailed Analysis
**Date:** November 11, 2025
**Thoroughness:** Medium - Comprehensive overview of structure, flow, and implementation

---

## 1. FRONTEND ARCHITECTURE (index.html)

### Overall Structure
- **Framework:** Tailwind CSS + Vanilla JavaScript (no frameworks)
- **Layout:** CSS Grid with 2 columns
  - Left column (flex: 1): Chat area
  - Right column (fixed 320px): Sidebar with metrics

### Visual Components

#### Header Section (Lines 96-111)
- Orange gradient banner with app title
- Connection status indicator (top-right)
  - Shows: Connected/Disconnected/Connecting status
  - Color-coded: Green (connected), Red (disconnected), Gray (connecting)

#### Main Chat Area (Lines 117-131)
- `#chat-container` - Message display area
  - Auto-scrolls to bottom on new messages
  - Smooth scrolling enabled
  - Custom scrollbar styling
  - White background with shadow

#### Input Area (Lines 134-151)
- Text input field (`#message-input`)
  - Placeholder: "Type your integration request..."
  - Tab autocomplete disabled
- Send button (`#send-btn`)
  - Disabled when WebSocket not connected
  - Blue background with hover effect

#### Right Sidebar (Lines 154-202)
**Three Cards:**

1. **Agent Status Card** (Lines 157-165)
   - Shows "Agent is working..." indicator when active
   - Hidden by default, shown when agent_delta received

2. **Token Usage Card** (Lines 168-192)
   - **Four token metrics tracked:**
     - `total-input-tokens`: Gray text
     - `total-output-tokens`: Gray text
     - `total-cache-creation-tokens`: Orange text (indicates cache writes)
     - `total-cache-read-tokens`: Green text (indicates cache hits)
     - `total-all-tokens`: Total of input + output
   - Updates dynamically when 'usage' message received
   - Uses `toLocaleString()` for thousand separators

3. **System Information Card** (Lines 195-200)
   - Displays initialization details
   - Shows E2B sandbox ID, database info, API status
   - Updated by status messages

### JavaScript Components

#### Message Types Handled (Lines 266-303)
```
'agent_message'   → addAgentMessage()
'agent_delta'     → showWorkingIndicator()  [BUG: Not accumulating text!]
'status'          → updateSystemInfo()
'tool'            → addToolUseIndicator()
'result'          → addExecutionResult()
'error'           → addErrorMessage()
'usage'           → updateTokenUsage()
'typing'          → showWorkingIndicator() or hideWorkingIndicator()
'pong'            → [Keep-alive response]
```

#### Message Rendering Functions

1. **addUserMessage()** (Lines 307-317)
   - Right-aligned blue bubble
   - Escapes HTML for security
   - Preserves whitespace

2. **addAgentMessage()** (Lines 320-337)
   - **Uses marked.js library for Markdown parsing**
   - Left-aligned gray bubble
   - Applies custom prose styling
   - Removes thinking indicator if present

3. **addThinkingIndicator()** (Lines 382-395)
   - Pulsing "Agent is thinking..." animation
   - Adds before response starts
   - Removed when agent_message arrives

4. **addToolUseIndicator()** (Lines 352-379)
   - Shows tool execution status with emoji
   - States: running (⚙️), completed (✅), failed (❌)
   - Pulsing dots animation when running
   - Styled with colored borders

5. **addExecutionResult()** (Lines 406-430)
   - Green border for success, red for failure
   - JSON syntax-highlighted if object
   - Displays execution results/errors
   - Full-width with max-width constraint

#### Token Usage Tracking (Lines 462-472)
```javascript
function updateTokenUsage(usage) {
    // Takes usage object from backend with:
    // - total_input_tokens
    // - total_output_tokens
    // - total_cache_creation_tokens
    // - total_cache_read_tokens
    
    // Updates DOM elements with formatted numbers
    // Total = input + output (excludes cache metrics)
}
```

#### Connection Management (Lines 219-263)
- Attempts to reconnect up to 5 times
- 2-second delay between reconnection attempts
- Updates status indicator based on connection state
- Shows reconnection attempt counter

#### Utilities
- **escapeHtml()** - XSS prevention via textContent
- **syntaxHighlightJSON()** - Color-codes JSON output
  - Keys: Blue (#93c5fd)
  - Strings: Green (#86efac)
  - Numbers: Amber (#fbbf24)
  - Booleans: Purple (#c084fc)
  - Null: Red (#f87171)

---

## 2. BACKEND ARCHITECTURE (app.py)

### Application Setup (Lines 52-65)
- FastAPI with CORS enabled (allows all origins for dev)
- Static files mounted at `/static`
- Logging configured with timestamps and levels

### Claude SDK Configuration (Lines 68-208)

#### System Prompt (Lines 69-154)
- **~80 lines** of detailed instructions
- Teaches Claude:
  - 4 available tools and when to use them
  - Discovery-first approach
  - Script template structure
  - Response style guidelines
  - Examples of interactions

#### Claude Tools Definition (Lines 157-208)
```
1. discover_objects
   - Lists all available Salesforce objects
   - No input parameters
   
2. get_object_fields
   - Get schema for specific object
   - Input: object_name (string)
   
3. execute_salesforce_query
   - Generate and execute Python scripts
   - Inputs: description, python_script
   
4. show_last_script
   - Display previously executed code
   - No input parameters
```

### AgentSession Class (Lines 211-915)

#### Initialization (Lines 218-255)
- **Session ID:** Timestamp-based (YYYYMMdd_HHMMSS_microseconds)
- **Claude Client:** AsyncAnthropic instance if ANTHROPIC_API_KEY set
- **Model Selection:** CLAUDE_MODEL env var (default: sonnet-4-5-20250929)
- **Prompt Caching:** ENABLE_PROMPT_CACHING env var (default: true)
- **Token Tracking:**
  ```python
  self.total_input_tokens = 0
  self.total_output_tokens = 0
  self.total_cache_creation_tokens = 0
  self.total_cache_read_tokens = 0
  ```
- **Conversation History:** List of role/content messages
- **Last Script:** Stores most recent executed Python code

#### Initialize Method (Lines 257-307)
- Creates E2B sandbox asynchronously (uses thread pool)
- Sends initialization status updates
- Sends detailed system info in welcome message:
  - Sandbox ID
  - Database info
  - Available objects
  - Environment variables
- Graceful error handling with user-friendly messages

#### Execute Tool Call (Lines 309-447)
**Handles 4 tools:**

1. **discover_objects**
   - Calls `executor.run_discovery()`
   - Returns: List of objects with field counts
   
2. **get_object_fields**
   - Generates schema discovery script
   - Uses `ScriptTemplates.discover_schema()`
   - Executes via `executor.execute_script()`
   - Returns: Field schema with types
   
3. **execute_salesforce_query**
   - Takes Python script from Claude
   - Replaces `<api_key_here>` placeholder
   - Stores script in `self.last_executed_script`
   - Executes via `executor.execute_script()`
   - Sends results to frontend
   
4. **show_last_script**
   - Returns stored script or "No script executed" message

**Tool Status Flow:**
```
Tool call starts:
  await send_tool_status(tool_name, "running")
  
Tool executes:
  [execution in thread pool]
  
Tool completes:
  await send_tool_status(tool_name, "completed" or "failed")
```

#### Process Message with Claude (Lines 449-623)

**Overall Flow:**
```
User message arrives
  ↓
Add to conversation_history
  ↓
Send typing indicator
  ↓
Enter max 5-iteration loop:
  ├─ Prepare system prompt
  │   ├─ If caching enabled: Wrap with cache_control {"type": "ephemeral"}
  │   └─ Else: Plain system string
  │
  ├─ Call Claude API with streaming
  │   └─ Accumulate response_text from text_delta events
  │
  ├─ Send agent_delta messages to WebSocket
  │   └─ Each delta sent immediately for streaming UX
  │
  ├─ Track token usage from final_message.usage:
  │   ├─ input_tokens
  │   ├─ output_tokens
  │   ├─ cache_creation_input_tokens (if available)
  │   └─ cache_read_input_tokens (if available)
  │
  ├─ Send usage message to frontend:
  │   └─ Includes per-request AND total tokens
  │
  ├─ Check stop_reason:
  │   ├─ "tool_use" → Execute tools
  │   │   ├─ Extract each tool_use block
  │   │   ├─ Call execute_tool_call()
  │   │   ├─ Collect results in tool_results list
  │   │   ├─ Add assistant message to history
  │   │   ├─ Add tool_results to history
  │   │   └─ Loop back (continue iteration)
  │   │
  │   └─ Else → Final response
  │       ├─ Add to history
  │       ├─ Send complete agent_message
  │       └─ Break loop
  │
  └─ Handle errors:
      ├─ API overload → "Please wait 30-60 seconds"
      ├─ Rate limit (429) → "Rate limit reached"
      ├─ Auth error (401) → "Check ANTHROPIC_API_KEY"
      └─ Other → Show status code and message
```

**Token Usage Tracking (Lines 515-541):**
```python
if hasattr(final_message, 'usage') and final_message.usage:
    usage = final_message.usage
    
    # Add to running totals
    self.total_input_tokens += usage.input_tokens
    self.total_output_tokens += usage.output_tokens
    
    # Handle cache metrics (may not exist in usage)
    cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
    self.total_cache_creation_tokens += cache_creation
    self.total_cache_read_tokens += cache_read
    
    # Send to frontend
    await self._safe_send({
        "type": "usage",
        "usage": {
            "input_tokens": usage.input_tokens,          # Per-request
            "output_tokens": usage.output_tokens,        # Per-request
            "cache_creation_tokens": cache_creation,     # Per-request
            "cache_read_tokens": cache_read,             # Per-request
            "total_input_tokens": self.total_input_tokens,        # Cumulative
            "total_output_tokens": self.total_output_tokens,      # Cumulative
            "total_cache_creation_tokens": self.total_cache_creation_tokens,  # Cumulative
            "total_cache_read_tokens": self.total_cache_read_tokens           # Cumulative
        }
    })
```

**Prompt Caching Configuration (Lines 475-487):**
```python
if self.enable_prompt_caching:
    # Enable 5-minute ephemeral cache
    system_param = [
        {
            "type": "text",
            "text": CLAUDE_SYSTEM_PROMPT,  # ~2000 tokens
            "cache_control": {"type": "ephemeral"}
        }
    ]
else:
    # No caching
    system_param = CLAUDE_SYSTEM_PROMPT
```

#### WebSocket Message Senders
- **send_agent_message()** - Full agent response
- **send_typing()** - Typing indicator
- **send_status()** - Status updates
- **send_error()** - Error messages
- **send_tool_status()** - Tool execution state
- **send_result()** - Query execution results
- **_safe_send()** - Core function with connection checking

#### Fallback to Pattern Matching (Lines 644-703)
- Original implementation preserved
- Activated when:
  - No ANTHROPIC_API_KEY set
  - Claude API fails
  - Claude disabled
- Handles: discovery, field queries, general queries

### WebSocket Endpoint (Lines 918-998)

**Connection Flow:**
1. Accept WebSocket connection
2. Create AgentSession
3. Initialize sandbox and agent
4. Send welcome messages
5. Enter message loop:
   - Receive JSON from client
   - Route by message type
   - Process message asynchronously
   - Send responses back
6. On disconnect:
   - Clean up sandbox
   - Log session closure

**Message Types Accepted:**
- `{"type": "message", "content": "user text"}` - Process message
- `{"type": "ping"}` - Keep-alive

---

## 3. TOKEN USAGE TRACKING MECHANISM

### Architecture
```
Claude API Response
    ↓
Extract usage metrics:
  - input_tokens
  - output_tokens
  - cache_creation_input_tokens
  - cache_read_input_tokens
    ↓
Accumulate in session:
  - self.total_input_tokens
  - self.total_output_tokens
  - self.total_cache_creation_tokens
  - self.total_cache_read_tokens
    ↓
Send via WebSocket:
  type: "usage"
  usage: {
    input_tokens,
    output_tokens,
    cache_creation_tokens,
    cache_read_tokens,
    total_input_tokens,
    total_output_tokens,
    total_cache_creation_tokens,
    total_cache_read_tokens
  }
    ↓
Frontend JavaScript:
  updateTokenUsage(usage)
    ↓
Update DOM elements:
  #total-input-tokens
  #total-output-tokens
  #total-cache-creation-tokens
  #total-cache-read-tokens
  #total-all-tokens (calculated)
```

### When Tokens Are Tracked
- **Every message** from Claude (regardless of tool use)
- **Per-request** - Gets usage for current API call
- **Cumulative** - Session totals are maintained
- **Cache metrics** - Only when cache_creation/read_input_tokens present

### Frontend Calculation
```javascript
const total = usage.total_input_tokens + usage.total_output_tokens
// Note: Cache metrics are NOT added to total
// Cache tokens are already counted in input_tokens
```

---

## 4. PROMPT CACHING CONFIGURATION

### How It Works

**Enabled by Default:**
```python
# In AgentSession.__init__:
caching_env = os.getenv('ENABLE_PROMPT_CACHING', 'true').lower()
self.enable_prompt_caching = caching_env in ('true', '1', 'yes', 'on')
```

**System Prompt with Cache Control:**
```python
if self.enable_prompt_caching:
    system_param = [
        {
            "type": "text",
            "text": CLAUDE_SYSTEM_PROMPT,  # ~2000 tokens
            "cache_control": {"type": "ephemeral"}
        }
    ]
```

### Cache Behavior
- **Type:** Ephemeral (5-minute TTL)
- **Scope:** Per-connection (each session)
- **Content:** System prompt (~2000 tokens)
- **Impact:**
  - First request: 2000 tokens written to cache (cache_creation_input_tokens)
  - Subsequent requests: 2000 tokens read from cache (cache_read_input_tokens)
  - **Cost reduction:** 90% on cached tokens (write = full cost, read = 10% cost)

### Configuration Options
```
ENABLE_PROMPT_CACHING=true    # Enable (default)
ENABLE_PROMPT_CACHING=false   # Disable
```

---

## 5. TOOL EXECUTION UI RENDERING

### Tool Lifecycle in UI

#### 1. Tool Running (Lines 352-379)
- Backend sends: `{"type": "tool", "tool": "discover_objects", "status": "running"}`
- Frontend renders:
  ```
  ⚙️ Using tool: discover_objects ...
  ```
  - Yellow background (#FEF3C7)
  - Pulsing dots animation
  - Tool name escaped for XSS prevention

#### 2. Tool Completed
- Backend sends: `{"type": "tool", "tool": "discover_objects", "status": "completed"}`
- Frontend renders:
  ```
  ✅ Using tool: discover_objects
  ```
  - Green background (#DCFCE7)
  - No animation

#### 3. Tool Failed
- Backend sends: `{"type": "tool", "tool": "discover_objects", "status": "failed"}`
- Frontend renders:
  ```
  ❌ Using tool: discover_objects
  ```
  - Red background (#FEE2E2)

### Multiple Tool Execution
- Each tool gets its own indicator element
- Added in order: discover → fields → execute
- All visible in chat history
- No accumulation/merging of indicators

### Tool Execution Flow in Chat
```
Agent starts thinking
  ↓
addThinkingIndicator()          [Pulsing indicator]
  ↓
First tool starts
  ↓
addToolUseIndicator("...", "running")  [Yellow ⚙️]
  ↓
Tool executes (2-5 seconds)
  ↓
addToolUseIndicator("...", "completed") [Green ✅]
  ↓
Result sent to frontend
  ↓
addExecutionResult(result, true)  [Green-bordered result box]
  ↓
Next tool (if needed) or final response
  ↓
addAgentMessage(final_response)    [Gray bubble with Markdown]
  ↓
removeThinkingIndicator()           [Clean up]
```

---

## 6. CURRENT IMPLEMENTATION STATUS

### What's Working ✅

1. **WebSocket Connection**
   - Real-time bidirectional communication
   - Auto-reconnect with exponential backoff
   - Connection status indicator

2. **Claude Integration**
   - Full streaming responses
   - Tool use execution
   - Multi-turn conversations (max 5 iterations)
   - Fallback to pattern matching

3. **Token Usage Tracking**
   - Per-request metrics collected
   - Cumulative totals maintained
   - Cache metrics tracked when available
   - Frontend display with formatting

4. **Prompt Caching**
   - System prompt cached for 5 minutes
   - Cache control properly configured
   - Per-connection ephemeral cache

5. **Tool Execution Display**
   - Tool status indicators (running/completed/failed)
   - Visual feedback with emojis
   - Pulsing animations

6. **Message Rendering**
   - Markdown support via marked.js
   - JSON syntax highlighting
   - XSS protection with HTML escaping
   - User/agent message styling

### What Needs Fixing ⚠️

1. **agent_delta Handling (CRITICAL)**
   - Currently only shows working indicator
   - Should accumulate streaming text into visible response
   - Frontend ignores the actual text deltas
   - Impact: No streaming text visible to user, only complete messages

2. **Thinking Indicator**
   - Added but not automatically removed in some cases
   - Could accumulate if multiple responses sent

3. **Cache Read Display**
   - Green color used for cache_read_tokens
   - No visual indicator when cache hit occurs
   - Users don't see cache benefits

4. **Token Usage Per-Request**
   - Frontend currently doesn't display per-request breakdown
   - Only shows cumulative totals
   - Users can't see per-message token cost

5. **Error Message Formatting**
   - Some error messages may contain raw JSON
   - Could be formatted more user-friendly

---

## 7. DETAILED MESSAGE FLOW

### Complete User Query Flow

```
User types "Get all leads" and hits Enter
    ↓
Frontend sends:
  {"type": "message", "content": "Get all leads"}
    ↓
Backend WebSocket endpoint receives
    ↓
Backend calls session.process_message("Get all leads")
    ↓
(Claude mode) process_message_with_claude() starts:
    ├─ Adds to conversation_history
    ├─ Sends typing indicator to frontend
    ├─ Calls Claude API (streaming)
    │
    ├─ During streaming:
    │   └─ For each text_delta:
    │       └─ Sends: {"type": "agent_delta", "delta": "I'll..."}
    │
    ├─ After streaming, gets usage:
    │   └─ Sends: {"type": "usage", "usage": {...}}
    │
    └─ Claude wants to use tools (stop_reason="tool_use")
        ├─ For each tool_use block:
        │   ├─ Sends: {"type": "tool", "tool": "get_object_fields", "status": "running"}
        │   ├─ Calls execute_tool_call("get_object_fields", {"object_name": "Lead"})
        │   │   └─ Executes in thread pool (non-blocking)
        │   │   └─ Returns field schema
        │   ├─ Sends: {"type": "tool", "tool": "get_object_fields", "status": "completed"}
        │   └─ Result added to conversation_history as tool_result
        │
        ├─ Calls Claude again with tool results
        ├─ Claude generates query script
        │
        ├─ Claude wants another tool (execute_salesforce_query)
        │   ├─ Sends: {"type": "tool", "tool": "execute_salesforce_query", "status": "running"}
        │   ├─ Stores script in self.last_executed_script
        │   ├─ Executes in thread pool (5-10 seconds)
        │   ├─ Sends: {"type": "result", "success": true, "data": [leads...]}
        │   ├─ Sends: {"type": "tool", "tool": "execute_salesforce_query", "status": "completed"}
        │   └─ Result added to history
        │
        ├─ Calls Claude again with results
        └─ Claude generates final response (no more tools)
            ├─ Sends streaming deltas (agent_delta)
            ├─ Sends: {"type": "usage", ...}
            ├─ Sends: {"type": "agent_message", "content": "I found 45 leads..."}
            └─ Sends: {"type": "typing", "is_typing": false}
    ↓
Frontend receives all messages
    ↓
For each message:
    ├─ agent_delta: Shows working indicator (doesn't accumulate text!)
    ├─ usage: Updates token counters
    ├─ tool: Shows status indicator
    ├─ result: Shows execution result box
    └─ agent_message: Renders Markdown response
```

---

## 8. ISSUES IDENTIFIED

### Critical (Breaks Streaming Feature)
1. **Agent Delta Not Accumulated**
   - Location: index.html lines 272-274
   - Current behavior: Shows working indicator only
   - Expected behavior: Accumulate text deltas into visible message
   - Fix: Need to buffer deltas and create/update message element

### High Priority (Impacts UX)
2. **Thinking Indicator Management**
   - Only removed in addAgentMessage()
   - Could persist if error occurs before final message
   
3. **Per-Request Token Display**
   - Not visible to user
   - Only cumulative totals shown
   
4. **Cache Hit Indication**
   - No visual feedback when cache is used
   - Users don't see cost benefits

### Medium Priority (Nice to Have)
5. **Tool Execution Timing**
   - No indication of how long tools took
   - User doesn't know if waiting normally
   
6. **Error Messages**
   - Sometimes show raw JSON
   - Could be formatted more gracefully

---

## 9. KEY FILES SUMMARY

| File | Size | Purpose |
|------|------|---------|
| app.py | 1143 lines | Backend with Claude SDK integration |
| index.html | 568 lines | Frontend UI with WebSocket handling |
| CLAUDE_INTEGRATION_SUMMARY.md | 454 lines | Integration documentation |
| QUICKSTART.md | 150 lines | Quick start guide |
| README.md | 280 lines | General documentation |
| test_websocket.py | 150+ lines | WebSocket test client |

---

## 10. RECOMMENDATIONS

### Immediate (Fix Streaming)
1. Implement agent_delta accumulation in frontend
   - Buffer text pieces as they arrive
   - Create message element on first delta
   - Update element with accumulated text
   - Finalize when agent_message arrives

2. Add loading animation while agent_delta streaming
   - Show cursor blinking or typing dots
   - Replace with formatted Markdown when complete

### Short Term (Improve UX)
3. Display per-request token metrics
   - Add expandable "Details" section in result cards
   - Show: input, output, cache_creation, cache_read per request

4. Add cache hit indicator
   - Show "Cache hit!" badge when cache_read_tokens > 0
   - Highlight in usage card with animation

5. Add tool execution timing
   - Display "Running for X seconds..." during execution
   - Show total time on completion

### Medium Term (Polish)
6. Improve error message formatting
   - Parse and pretty-print JSON errors
   - Highlight key error fields

7. Better thinking indicator management
   - Add timeout to auto-remove old indicators
   - Track thinking state more carefully

---

## Conclusion

The Web UI is **architecturally sound** with good separation of concerns:
- Frontend handles presentation and user input
- Backend orchestrates Claude, tools, and E2B
- WebSocket provides real-time communication
- Token tracking is comprehensive

**Main issue:** The streaming feature (agent_delta) isn't utilized - frontend receives deltas but doesn't display them. This defeats the purpose of streaming since users only see complete messages. This should be the priority fix to provide the responsive, real-time UX that streaming enables.

