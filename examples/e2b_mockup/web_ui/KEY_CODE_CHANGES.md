# Key Code Changes - Detailed Reference

This document shows the exact code changes made to implement the UI restructure.

---

## 1. Backend - app.py

### System Information Update (Lines 275-292)

**OLD CODE:**
```python
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
await self.send_agent_message(welcome_msg)  # ← Goes to CHAT
```

**NEW CODE:**
```python
# Send system information to populate sidebar (not as a chat message)
system_info = (
    f"**E2B Sandbox:** `{sandbox_id}`\n"
    f"**Database:** DuckDB with 180 test records\n"
    f"**Salesforce Driver:** Loaded successfully\n"
    f"**Mock API:** Running on `localhost:8000` (inside sandbox)\n"
    f"**Available Objects:** Account, Lead, Opportunity, Campaign\n\n"
    f"**Model:** {self.claude_model if self.claude_model else 'Pattern Matching (No API Key)'}\n"
    f"**Prompt Caching:** {'Enabled ✓ (Ephemeral, 5 min)' if self.enable_prompt_caching else 'Disabled ✗'}\n\n"
    f"**Environment:**\n"
    f"- `SF_API_URL`: {self.executor.sandbox_sf_api_url}\n"
    f"- `SF_API_KEY`: {'*' * 8} (configured)\n"
    f"- `E2B_API_KEY`: {'*' * 8} (configured)"
)
await self.send_status(system_info)  # ← Goes to SIDEBAR
```

**Key Changes:**
1. Removed Try asking examples from system info
2. Added `**Model:**` line showing `self.claude_model`
3. Added `**Prompt Caching:**` line showing `self.enable_prompt_caching` status
4. Updated Available Objects to include Campaign
5. Changed `send_agent_message()` → `send_status()` (sidebar instead of chat)

---

## 2. Frontend - HTML Structure

### Agent Status Card (Lines 156-166)

**OLD CODE:**
```html
<!-- Agent Status Card -->
<div class="bg-white rounded-lg shadow-md p-4">
    <h3 class="font-semibold text-gray-800 mb-3">Agent Status</h3>
    <div id="agent-working-indicator" class="hidden mb-3 bg-blue-50 border border-blue-300 rounded-lg p-3">
        <div class="flex items-center gap-2">
            <div class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <span class="text-sm text-blue-700 font-medium">Agent is working...</span>
        </div>
    </div>
</div>
```

**NEW CODE:**
```html
<!-- Agent Status Card -->
<div class="bg-white rounded-lg shadow-md p-4">
    <h3 class="font-semibold text-gray-800 mb-3">Agent Status</h3>
    <div id="agent-status-content" class="space-y-2">
        <div class="flex items-center gap-2">
            <div id="agent-status-indicator" class="w-2 h-2 bg-gray-400 rounded-full"></div>
            <span id="agent-status-text" class="text-sm text-gray-600">Idle</span>
        </div>
        <div id="agent-current-activity" class="text-xs text-gray-500 hidden pl-4"></div>
    </div>
</div>
```

**Key Changes:**
1. Removed `agent-working-indicator` (old approach)
2. Added `agent-status-content` container
3. Added `agent-status-indicator` (colored dot)
4. Added `agent-status-text` (dynamic status label)
5. Added `agent-current-activity` (detail line for activities)
6. Default state: Gray dot, "Idle" text

---

## 3. Frontend - JavaScript Functions

### A. New updateAgentStatus() Function (Line 664)

```javascript
// Update agent status in sidebar with visual indicators
function updateAgentStatus(status, activity = '') {
    const statusIndicator = document.getElementById('agent-status-indicator');
    const statusText = document.getElementById('agent-status-text');
    const currentActivity = document.getElementById('agent-current-activity');

    if (!statusIndicator || !statusText || !currentActivity) return;

    // Reset classes
    statusIndicator.className = 'w-2 h-2 rounded-full';

    switch(status) {
        case 'idle':
            statusIndicator.classList.add('bg-gray-400');
            statusText.textContent = 'Idle';
            statusText.className = 'text-sm text-gray-600';
            currentActivity.classList.add('hidden');
            break;

        case 'thinking':
            statusIndicator.classList.add('bg-blue-500', 'pulse-dot');
            statusText.textContent = 'Thinking...';
            statusText.className = 'text-sm text-blue-700 font-medium';
            currentActivity.classList.add('hidden');
            break;

        case 'generating':
            statusIndicator.classList.add('bg-blue-500', 'animate-pulse');
            statusText.textContent = 'Generating response...';
            statusText.className = 'text-sm text-blue-700 font-medium';
            currentActivity.classList.add('hidden');
            break;

        case 'tool_running':
            statusIndicator.classList.add('bg-yellow-500', 'animate-pulse');
            statusText.textContent = 'Using tool';
            statusText.className = 'text-sm text-yellow-700 font-medium';
            currentActivity.textContent = activity;
            currentActivity.classList.remove('hidden');
            break;

        case 'tool_complete':
            statusIndicator.classList.add('bg-green-500');
            statusText.textContent = 'Tool completed';
            statusText.className = 'text-sm text-green-700 font-medium';
            currentActivity.classList.add('hidden');
            setTimeout(() => updateAgentStatus('idle'), 2000);
            break;

        case 'tool_failed':
            statusIndicator.classList.add('bg-red-500');
            statusText.textContent = 'Tool failed';
            statusText.className = 'text-sm text-red-700 font-medium';
            currentActivity.textContent = activity;
            currentActivity.classList.remove('hidden');
            setTimeout(() => updateAgentStatus('idle'), 3000);
            break;

        case 'error':
            statusIndicator.classList.add('bg-red-500');
            statusText.textContent = 'Error';
            statusText.className = 'text-sm text-red-700 font-medium';
            currentActivity.textContent = activity;
            currentActivity.classList.remove('hidden');
            break;

        default:
            statusIndicator.classList.add('bg-gray-400');
            statusText.textContent = 'Unknown';
            statusText.className = 'text-sm text-gray-600';
            currentActivity.classList.add('hidden');
    }
}
```

**Features:**
- Centralized status management
- Dynamic color/text updates
- Auto-reset for transient states (tool_complete, tool_failed)
- Activity detail line for context
- Tailwind CSS class manipulation

---

### B. Updated handleMessage() Integration (Lines 282-337)

**Added calls to updateAgentStatus():**

```javascript
function handleMessage(data) {
    switch(data.type) {
        case 'agent_message':
            finalizeAgentMessage();
            addAgentMessage(data.content);
            hideWorkingIndicator();
            updateAgentStatus('idle');  // ← NEW
            break;

        case 'agent_delta':
            if (data.delta) {
                appendAgentDelta(data.delta);
            }
            showWorkingIndicator();
            updateAgentStatus('generating', 'Generating response...');  // ← NEW
            break;

        case 'tool':
            addToolUseIndicator(data.tool, data.status);
            // ← NEW: Update agent status based on tool status
            if (data.status === 'running') {
                updateAgentStatus('tool_running', `Using tool: ${data.tool}`);
            } else if (data.status === 'completed' || data.status === 'complete') {
                updateAgentStatus('tool_complete', 'Tool completed');
            } else if (data.status === 'failed') {
                updateAgentStatus('tool_failed', `Tool failed: ${data.tool}`);
            }
            break;

        case 'error':
            addErrorMessage(data.error);
            finalizeAgentMessage();
            hideWorkingIndicator();
            updateAgentStatus('error', 'Error occurred');  // ← NEW
            break;

        case 'typing':
            if (data.is_typing) {
                showWorkingIndicator();
                updateAgentStatus('thinking', 'Thinking...');  // ← NEW
            } else {
                hideWorkingIndicator();
                updateAgentStatus('idle');  // ← NEW
            }
            break;

        // ... other cases
    }
}
```

---

### C. Legacy Functions (Lines 746-753)

**Converted to no-ops for backward compatibility:**

```javascript
// Legacy placeholder functions (kept for compatibility)
function showWorkingIndicator() {
    // Now handled by updateAgentStatus
}

function hideWorkingIndicator() {
    // Now handled by updateAgentStatus
}
```

**Why:**
- Existing code may still call these functions
- Prevents runtime errors
- All functionality moved to `updateAgentStatus()`

---

## 4. CSS Animations (Already Existing)

The status indicators use existing Tailwind and custom CSS:

```css
/* Custom pulse-dot animation (lines 11-17) */
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
.pulse-dot {
    animation: pulse-dot 1.5s ease-in-out infinite;
}
```

**Tailwind classes used:**
- `bg-gray-400` - Gray indicator (idle)
- `bg-blue-500` - Blue indicator (thinking/generating)
- `bg-yellow-500` - Yellow indicator (tool running)
- `bg-green-500` - Green indicator (tool complete)
- `bg-red-500` - Red indicator (error/failed)
- `animate-pulse` - Tailwind built-in pulse animation
- `pulse-dot` - Custom dot pulse animation

---

## 5. Integration Summary

### Data Flow

```
Backend                  WebSocket               Frontend
───────                  ─────────               ────────

send_status()    →   type: "status"      →   updateSystemInfo()
                    content: "..."                  ↓
                                           System Information card

send_tool_status() → type: "tool"        →   handleMessage()
                    tool: "name"                    ↓
                    status: "running"        updateAgentStatus()
                                                    ↓
                                           Agent Status card
```

### State Transitions

```
Initial state:
    updateAgentStatus('idle')
        ↓
User sends message:
    updateAgentStatus('thinking', 'Thinking...')
        ↓
Tool starts:
    updateAgentStatus('tool_running', 'Using tool: discover_objects')
        ↓
Tool completes:
    updateAgentStatus('tool_complete', 'Tool completed')
        ↓ (2 second auto-reset)
    updateAgentStatus('idle')
```

---

## 6. Testing Examples

### Test Case 1: Check Model Display

```javascript
// In browser console after page loads:
document.getElementById('system-info-content').innerText
// Should include: "Model: claude-sonnet-4-5-20250929"
```

### Test Case 2: Check Status Updates

```javascript
// Send a message and watch:
const indicator = document.getElementById('agent-status-indicator');
const text = document.getElementById('agent-status-text');

// Initial: gray, "Idle"
console.log(indicator.className, text.textContent);
// → "w-2 h-2 rounded-full bg-gray-400" "Idle"

// After sending message: blue, "Thinking..."
// (observed via visual inspection or MutationObserver)
```

### Test Case 3: Verify Auto-Reset

```javascript
// Manually trigger tool_complete:
updateAgentStatus('tool_complete', 'Test');

// Wait 2 seconds, then check:
setTimeout(() => {
    const text = document.getElementById('agent-status-text');
    console.log(text.textContent);  // Should be "Idle"
}, 2500);
```

---

## 7. Environment Variable Configuration

In `.env` file:

```bash
# Model selection (defaults to Sonnet 4.5 if not set)
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Caching (defaults to enabled if not set)
ENABLE_PROMPT_CACHING=true

# Required keys
ANTHROPIC_API_KEY=sk-ant-...
E2B_API_KEY=e2b_...
```

**Read in backend:**
```python
self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
caching_env = os.getenv('ENABLE_PROMPT_CACHING', 'true').lower()
self.enable_prompt_caching = caching_env in ('true', '1', 'yes', 'on')
```

---

## Conclusion

These changes implement a cleaner, more informative UI with:
- Consolidated system information (sidebar only)
- Real-time agent status feedback
- Model and caching transparency
- Color-coded visual indicators
- Smooth auto-reset transitions
- Full backward compatibility
