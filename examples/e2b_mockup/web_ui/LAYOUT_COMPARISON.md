# Web UI Layout Comparison - Before vs After

## Before Restructure

### Chat Area
```
┌─────────────────────────────────────────────────┐
│ [Welcome Message - Blue Box]                    │
│                                                 │
│ Welcome! Ask me to generate Salesforce         │
│ integration scripts...                          │
│                                                 │
│ **System Information:**                         │
│ **E2B Sandbox:** abc123...                      │
│ **Database:** DuckDB with 180 test records     │
│ **Available Objects:** Account, Lead...        │
│ **Environment:**                                │
│ - SF_API_URL: http://localhost:8000            │
│ - SF_API_KEY: ******** (configured)            │
│ - E2B_API_KEY: ******** (configured)           │
│                                                 │
│ Ready to query your Salesforce data!           │
│ Try asking: "Get all leads"...                 │
└─────────────────────────────────────────────────┘
```

### Sidebar
```
┌──────────────────────┐
│ Agent Status         │
├──────────────────────┤
│ [Empty Card]         │
│                      │
│                      │
└──────────────────────┘

┌──────────────────────┐
│ Token Usage          │
├──────────────────────┤
│ Input: 0             │
│ Output: 0            │
│ Cache Created: 0     │
│ Cache Read: 0        │
│ Total: 0             │
└──────────────────────┘

┌──────────────────────┐
│ System Information   │
├──────────────────────┤
│ Initializing...      │
│                      │
│ (Later shows same    │
│  info as in chat)    │
└──────────────────────┘
```

**Issues:**
- System info appears BOTH in chat AND sidebar (redundant)
- Agent Status card is empty/unused
- No model name visible
- No caching status visible
- No real-time agent activity feedback

---

## After Restructure

### Chat Area
```
┌─────────────────────────────────────────────────┐
│ [Welcome Message - Blue Box]                    │
│                                                 │
│ Welcome! Ask me to generate Salesforce         │
│ integration scripts. For example: "Get all     │
│ leads from the last 30 days" or "Find          │
│ campaigns created this month"                   │
│                                                 │
│ (No system information here - clean!)          │
└─────────────────────────────────────────────────┘
```

### Sidebar
```
┌──────────────────────┐
│ Agent Status         │
├──────────────────────┤
│ ● Idle               │ ← Gray dot, default state
│                      │
│ OR:                  │
│ ● Thinking...        │ ← Blue pulsing
│ ● Generating...      │ ← Blue animated
│ ● Using tool         │ ← Yellow pulsing
│   execute_query      │   (detail line)
│ ● Tool completed     │ ← Green (auto-resets)
│ ● Error              │ ← Red
└──────────────────────┘

┌──────────────────────┐
│ Token Usage          │
├──────────────────────┤
│ Input: 1,234         │
│ Output: 567          │
│ Cache Created: 1,890 │
│ Cache Read: 1,890    │
│ Total Tokens: 1,801  │
│                      │
│ This Request: $0.012 │
│ Session Total: $0.045│
└──────────────────────┘

┌──────────────────────┐
│ System Information   │
├──────────────────────┤
│ E2B Sandbox: abc123  │
│ Database: DuckDB...  │
│ Driver: Loaded ✓     │
│ Mock API: Running... │
│ Objects: Account...  │
│                      │
│ Model: claude-sonnet │ ← NEW!
│   -4-5-20250929      │
│ Prompt Caching:      │ ← NEW!
│   Enabled ✓ (5 min)  │
│                      │
│ Environment:         │
│ - SF_API_URL: ...    │
│ - SF_API_KEY: ***    │
│ - E2B_API_KEY: ***   │
└──────────────────────┘
```

**Improvements:**
- System info ONLY in sidebar (no chat clutter)
- Agent Status shows real-time activity
- Model name clearly displayed
- Caching status visible (transparency)
- Visual color coding for agent states
- Auto-reset for transient states
- Additional detail line for activities

---

## State Flow Visualization

### Agent Status During Query

```
User: "Get all leads"
↓
┌──────────────────────┐     ┌──────────────────────┐
│ Agent Status         │     │ Agent Status         │
├──────────────────────┤     ├──────────────────────┤
│ ● Thinking...        │ --> │ ● Using tool         │
│                      │     │   get_object_fields  │
└──────────────────────┘     └──────────────────────┘
    (Blue pulsing)              (Yellow pulsing)
                                      ↓
┌──────────────────────┐     ┌──────────────────────┐
│ Agent Status         │     │ Agent Status         │
├──────────────────────┤     ├──────────────────────┤
│ ● Tool completed     │ --> │ ● Using tool         │
│                      │     │   execute_query      │
└──────────────────────┘     └──────────────────────┘
    (Green, 2s)                 (Yellow pulsing)
                                      ↓
┌──────────────────────┐     ┌──────────────────────┐
│ Agent Status         │     │ Agent Status         │
├──────────────────────┤     ├──────────────────────┤
│ ● Tool completed     │ --> │ ● Generating...      │
│                      │     │                      │
└──────────────────────┘     └──────────────────────┘
    (Green, 2s)                 (Blue animated)
                                      ↓
                              ┌──────────────────────┐
                              │ Agent Status         │
                              ├──────────────────────┤
                              │ ● Idle               │
                              │                      │
                              └──────────────────────┘
                                  (Gray, resting)
```

---

## Color Coding Reference

| State         | Indicator Color | Animation      | Auto-Reset |
|---------------|----------------|----------------|------------|
| Idle          | Gray           | None           | N/A        |
| Thinking      | Blue           | Pulse (dot)    | No         |
| Generating    | Blue           | Pulse (full)   | No         |
| Tool Running  | Yellow         | Pulse (full)   | No         |
| Tool Complete | Green          | None           | 2 seconds  |
| Tool Failed   | Red            | None           | 3 seconds  |
| Error         | Red            | None           | No         |

---

## Key Benefits Summary

### 1. Information Architecture
**Before:** System info duplicated in chat and sidebar  
**After:** System info only in sidebar (single source of truth)

### 2. Chat Cleanliness
**Before:** Welcome message + long system details = clutter  
**After:** Simple welcome message only = clean conversation

### 3. Model Transparency
**Before:** No indication of which model is responding  
**After:** Model name clearly shown in System Information

### 4. Cost Transparency
**Before:** No indication if caching is saving money  
**After:** Caching status shown (users see 90% cost reduction)

### 5. Real-Time Feedback
**Before:** Agent Status empty, no activity indication  
**After:** Live updates with color-coded states and animations

### 6. User Experience
**Before:** Static, minimal feedback during operations  
**After:** Dynamic, informative, reassuring visual feedback

---

## Migration Notes

### No Breaking Changes
- All existing WebSocket message types supported
- Legacy `showWorkingIndicator()` / `hideWorkingIndicator()` preserved as no-ops
- Existing code continues to work without modification

### Backward Compatibility
- If `ANTHROPIC_API_KEY` not set → Shows "Pattern Matching (No API Key)"
- If `CLAUDE_MODEL` not set → Defaults to sonnet-4-5-20250929
- If `ENABLE_PROMPT_CACHING` not set → Defaults to enabled (true)

---

## Testing Checklist

- [ ] System Information shows in sidebar only (not in chat)
- [ ] Model name displays correctly
- [ ] Caching status displays correctly
- [ ] Agent Status starts as "Idle" (gray)
- [ ] Agent Status updates to "Thinking" when user sends message
- [ ] Agent Status shows "Using tool: {name}" during tool execution
- [ ] Agent Status shows "Tool completed" (green) after tool finishes
- [ ] Tool completed status auto-resets to "Idle" after 2 seconds
- [ ] Agent Status shows "Generating response..." during text streaming
- [ ] Agent Status returns to "Idle" after response complete
- [ ] Error status (red) displays on errors
- [ ] Activity detail line shows/hides appropriately
- [ ] All animations work (pulsing, etc.)
