# Web UI Documentation Index

**Last Updated:** November 11, 2025
**Exploration Thoroughness:** Medium - Comprehensive analysis of structure and implementation

## Quick Navigation

### For Quick Understanding
- **Start Here:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Developer cheat sheet with key concepts
- **Running:** See "Running the Web UI" section in QUICK_REFERENCE.md
- **Issues:** See "Common Issues & Fixes" section in QUICK_REFERENCE.md

### For Detailed Understanding
- **Architecture:** [WEB_UI_ARCHITECTURE.md](WEB_UI_ARCHITECTURE.md) - Comprehensive breakdown of all components
- **Token Flow:** [TOKEN_TRACKING_FLOW.md](TOKEN_TRACKING_FLOW.md) - Visual diagrams and examples
- **Integration:** [CLAUDE_INTEGRATION_SUMMARY.md](CLAUDE_INTEGRATION_SUMMARY.md) - Claude SDK integration details

### For Setup & Getting Started
- **Quick Start:** [QUICKSTART.md](QUICKSTART.md) - First-time setup guide
- **Main README:** [README.md](README.md) - General project information

---

## Documentation Files Overview

### 1. WEB_UI_ARCHITECTURE.md (755 lines)
**Purpose:** Complete technical reference for the Web UI codebase

**Covers:**
- Frontend architecture (HTML structure, components, layout)
- Backend architecture (FastAPI, Claude SDK, async handling)
- AgentSession class (core session management)
- WebSocket endpoint and message handling
- Token usage tracking mechanism
- Prompt caching configuration
- Tool execution UI rendering
- Complete message flow diagrams
- Identified issues (critical, high, medium priority)
- Code location references with line numbers
- Recommendations for improvements

**Best For:** Deep dive understanding, debugging, planning improvements

**Key Sections:**
1. Frontend Architecture
2. Backend Architecture
3. Token Usage Tracking Mechanism
4. Prompt Caching Configuration
5. Tool Execution UI Rendering
6. Current Implementation Status (What Works/Needs Fixing)
7. Detailed Message Flow
8. Issues Identified
9. Key Files Summary
10. Recommendations

---

### 2. TOKEN_TRACKING_FLOW.md (324 lines)
**Purpose:** Visual explanation of how tokens flow through the system

**Covers:**
- Token flow architecture with ASCII diagrams
- Multi-turn conversation token accumulation examples
- Token breakdown in UI (input, output, cache created, cache read)
- Complete token usage timeline showing state changes
- Cache control configuration details
- Per-request vs cumulative token tracking
- Cost analysis and savings calculations
- Important notes on cache behavior and cost savings

**Best For:** Understanding token costs, explaining caching benefits, cost analysis

**Key Diagrams:**
1. Token Flow Architecture
2. Multi-Turn Conversation Example
3. Token Breakdown in UI
4. Timeline of Token Accumulation
5. Cache Control Configuration
6. Per-Request vs Cumulative Tracking

**Example:** With caching enabled:
- 10 requests without cache: $0.30
- 10 requests with cache: $0.057 (81% savings!)

---

### 3. QUICK_REFERENCE.md (263 lines)
**Purpose:** Developer quick lookup guide

**Covers:**
- File structure overview
- Key concepts for frontend and backend
- WebSocket message types (client → server, server → client)
- Claude tools reference (4 tools with descriptions)
- Token tracking flow summary
- Prompt caching quick reference
- Environment variables
- Common issues and fixes with solutions
- Running instructions
- Testing checklist
- Key code locations with line numbers
- Architecture principles summary
- Performance notes
- Enhancement roadmap

**Best For:** Quick lookup, on-the-fly reference, onboarding

**Quick Sections:**
- Message Type Reference
- Claude Tools (4 tools)
- Token Tracking Summary
- Environment Variables
- Common Issues & Fixes
- Testing Checklist
- Key Code Locations

---

### 4. CLAUDE_INTEGRATION_SUMMARY.md (453 lines)
**Purpose:** Details on Claude SDK integration implementation

**Covers:**
- Overview of Claude SDK integration
- What was changed (imports, constants, classes)
- System prompt explanation
- Tool definitions
- New methods added
- Refactored original logic
- Environment configuration
- Architecture and message flow
- Tool integration details
- Discovery-first pattern
- WebSocket message types
- Backward compatibility
- Configuration options
- Testing checklist
- Implementation statistics
- Performance considerations
- Known limitations
- Security notes
- Success criteria
- Recent updates (prompt caching, model selection)

**Best For:** Understanding the Claude integration, testing Claude features

---

### 5. QUICKSTART.md (259 lines)
**Purpose:** First-time setup and running guide

**Covers:**
- Prerequisites
- Installation steps
- Environment configuration
- Starting the Web UI
- Testing the connection
- Making test queries
- Understanding response flow
- Troubleshooting

**Best For:** Getting started quickly, new developer setup

---

### 6. README.md (424 lines)
**Purpose:** General project information

**Covers:**
- Project overview
- Features
- Architecture
- Running the application
- API documentation
- WebSocket protocol
- Configuration
- Deployment notes

**Best For:** Project overview, understanding the big picture

---

## Critical Issue: agent_delta Not Accumulated

**Severity:** CRITICAL - Breaks streaming feature

**Location:** index.html lines 272-274

**Problem:**
```javascript
case 'agent_delta':
    showWorkingIndicator();
    break;
```
The frontend receives streaming text deltas from the backend but only shows a "working" indicator. The actual text deltas are ignored.

**Expected Behavior:**
Text deltas should accumulate into a visible message element that appears token-by-token as they arrive from the backend.

**Impact:**
- Users see "Agent is thinking..." but no actual text appearing
- Defeats the purpose of streaming (real-time UX)
- Users only see complete messages at the end

**Solution:**
```javascript
// Buffer to accumulate deltas
let currentResponseBuffer = '';
let currentResponseElement = null;

case 'agent_delta':
    showWorkingIndicator();
    
    // Get the text delta
    const delta = data.delta;
    
    // Add to buffer
    currentResponseBuffer += delta;
    
    // Create or update message element
    if (!currentResponseElement) {
        // Create new message on first delta
        currentResponseElement = createStreamingMessage();
        chatContainer.appendChild(currentResponseElement);
    }
    
    // Update displayed content
    updateStreamingMessage(currentResponseElement, currentResponseBuffer);
    
    scrollToBottom();
    break;
```

---

## How to Use This Documentation

### Scenario 1: New Developer Onboarding
1. Read QUICK_REFERENCE.md (get oriented - 10 min)
2. Read WEB_UI_ARCHITECTURE.md sections 1-2 (understand components - 20 min)
3. Read QUICKSTART.md (learn how to run it - 10 min)
4. Try running it and test the UI

### Scenario 2: Debugging a Bug
1. Check QUICK_REFERENCE.md "Common Issues & Fixes"
2. Look up the component in WEB_UI_ARCHITECTURE.md with line numbers
3. Reference TOKEN_TRACKING_FLOW.md if it's token-related
4. Check CLAUDE_INTEGRATION_SUMMARY.md if it's Claude-related

### Scenario 3: Understanding Token Usage
1. Start with TOKEN_TRACKING_FLOW.md (visual understanding)
2. Read WEB_UI_ARCHITECTURE.md section 3 (implementation details)
3. Check QUICK_REFERENCE.md "Token Tracking Summary"

### Scenario 4: Planning Improvements
1. Review WEB_UI_ARCHITECTURE.md section 6 "Current Implementation Status"
2. Read WEB_UI_ARCHITECTURE.md section 8 "Issues Identified"
3. Review WEB_UI_ARCHITECTURE.md section 10 "Recommendations"

---

## Key Technical Details by Topic

### WebSocket Communication
**Files:** WEB_UI_ARCHITECTURE.md (sections 2, 7), QUICK_REFERENCE.md

Message types: agent_message, agent_delta, status, tool, result, error, usage, typing

### Token Tracking
**Files:** TOKEN_TRACKING_FLOW.md, WEB_UI_ARCHITECTURE.md (section 3), QUICK_REFERENCE.md

Metrics: input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens

### Prompt Caching
**Files:** TOKEN_TRACKING_FLOW.md, WEB_UI_ARCHITECTURE.md (section 4), QUICK_REFERENCE.md

Configuration: ENABLE_PROMPT_CACHING env var, cache_control with ephemeral type

### Claude Tools
**Files:** QUICK_REFERENCE.md, WEB_UI_ARCHITECTURE.md (section 2), CLAUDE_INTEGRATION_SUMMARY.md

Tools: discover_objects, get_object_fields, execute_salesforce_query, show_last_script

### Frontend Components
**Files:** WEB_UI_ARCHITECTURE.md (section 1), QUICK_REFERENCE.md

Components: Header, Chat Area, Sidebar (Agent Status, Token Usage, System Info)

### Backend Processing
**Files:** WEB_UI_ARCHITECTURE.md (section 2), QUICK_REFERENCE.md, CLAUDE_INTEGRATION_SUMMARY.md

Flow: process_message → process_message_with_claude → tool execution → response streaming

---

## Code Location Quick Reference

| What | File | Lines |
|------|------|-------|
| HTML Structure | index.html | 1-93 |
| Header | index.html | 96-111 |
| Chat Area | index.html | 117-131 |
| Sidebar | index.html | 154-202 |
| Message Handler | index.html | 265-304 |
| Token Display | index.html | 168-192, 462-472 |
| Python Entry | app.py | 1-50 |
| System Prompt | app.py | 69-154 |
| Tool Definitions | app.py | 157-208 |
| AgentSession Class | app.py | 211-915 |
| Token Tracking Init | app.py | 249-253 |
| Prompt Caching | app.py | 475-487 |
| Token Tracking Logic | app.py | 515-541 |
| WebSocket Endpoint | app.py | 918-998 |

---

## Environment Variables Reference

**Required:**
- `E2B_API_KEY` - E2B sandbox API key
- `ANTHROPIC_API_KEY` - Claude API key

**Optional:**
- `CLAUDE_MODEL` - Model selection (default: claude-sonnet-4-5-20250929)
- `ENABLE_PROMPT_CACHING` - Cache toggle (default: true)
- `SF_API_URL` - Salesforce API URL (default: http://localhost:8000)
- `SF_API_KEY` - Salesforce API key (default: test_key_12345)

---

## Testing Checklist

- [ ] WebSocket connection works
- [ ] Connection status indicator shows correct state
- [ ] Can send messages and get responses
- [ ] Agent responses render with Markdown formatting
- [ ] Tool execution shows status indicators (running/completed)
- [ ] Token usage updates in sidebar
- [ ] Multiple conversations accumulate tokens
- [ ] Cache metrics display when available
- [ ] Pattern matching fallback works without ANTHROPIC_API_KEY
- [ ] Streaming text appears (once agent_delta fix implemented)

---

## Performance Metrics

- **First Claude request:** 2-3 seconds (includes cache write)
- **Subsequent requests:** 1-2 seconds (uses cached prompt)
- **Tool execution:** 2-5 seconds (E2B sandbox execution)
- **Total response time:** 5-15 seconds for complex queries
- **Cache cost savings:** 90% on cached tokens
- **Example savings:** 10 requests cost 81% less with caching

---

## Next Steps

1. **Immediate:** Review WEB_UI_ARCHITECTURE.md section 8 (Issues Identified)
2. **Short Term:** Implement agent_delta accumulation (streaming fix)
3. **Medium Term:** Add cache hit indicators and per-request token breakdown
4. **Long Term:** Consider conversation export, cost calculator, request history

---

## Questions?

Refer to the specific documentation file:
- **"How do I...?"** → QUICKSTART.md or QUICK_REFERENCE.md
- **"What is...?"** → WEB_UI_ARCHITECTURE.md or QUICK_REFERENCE.md
- **"Why does token cost...?"** → TOKEN_TRACKING_FLOW.md
- **"How does Claude...?"** → CLAUDE_INTEGRATION_SUMMARY.md
- **"Where is the code...?"** → WEB_UI_ARCHITECTURE.md (Code Locations) or QUICK_REFERENCE.md

---

**Documentation Generated:** November 11, 2025
**Total Documentation:** 2,478 lines across 6 files
**Average Reading Time:** 45-60 minutes for all files, 10-15 minutes for quick reference

