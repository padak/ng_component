# Prompt for Next Session: AgentSDK Integration

Copy this prompt into a new Claude Code session:

---

## Task: Integrate Claude Agent SDK into Web UI

I have a working **E2B-based Salesforce integration system** with a Web UI (`examples/e2b_mockup/web_ui/`). Currently it uses **template-based pattern matching** to generate scripts. I need to replace this with **Claude Agent SDK** for intelligent, conversational script generation.

### Current Architecture (Working ✅)
- ✅ **Web UI**: WebSocket-based chat at `http://localhost:8080/static/`
- ✅ **E2B Sandbox**: Cloud VM with Mock Salesforce API + DuckDB (180 test records)
- ✅ **AgentExecutor**: Manages sandbox, uploads files, executes scripts
- ✅ **Script Templates**: Pre-built Python scripts for common queries
- ✅ **Discovery Tools**: `list_objects()`, `get_fields()`, `query()`

### What Needs to Change
Replace pattern matching in `web_ui/app.py` (lines 161-224) with Claude Agent SDK that:
1. Understands natural language queries conversationally
2. Uses discovery tools to learn schema dynamically (don't hardcode field names!)
3. Generates Python scripts on-the-fly using `SalesforceClient`
4. Executes via existing `AgentExecutor.execute_script()`
5. Displays results and optionally shows generated code

### Key Requirements
- **Discovery-first**: Agent must call `get_fields()` before generating queries
- **Context preservation**: Remember conversation for follow-ups like "show me the code"
- **Dynamic generation**: No hardcoded field names (database has FirstName/LastName, not Name)
- **Natural language**: Handle "get 10 leads", "filter by status New", "last 30 days", etc.
- **Code display**: When user asks "show me the code", display generated Python script

### Files to Review
1. `examples/e2b_mockup/web_ui/NEXT_STEPS.md` - Detailed integration guide
2. `examples/e2b_mockup/web_ui/app.py` - Current implementation (replace pattern matching)
3. `examples/e2b_mockup/agent_executor.py` - Keep as-is (execution engine)
4. `examples/e2b_mockup/salesforce_driver/` - The driver that agents use
5. `CLAUDE.md` - Architecture documentation

### Environment
- Python 3.11+
- E2B API key configured (sandbox working)
- Need to add: `ANTHROPIC_API_KEY` for Agent SDK

### Success Criteria
Test these queries after integration:
- "Get all leads" → discovers schema, generates query
- "Show me 10 leads from last 30 days" → respects limit and date filter
- "Show me the code" → displays generated Python script
- "What objects are available?" → runs discovery
- "Filter by status New" → adds WHERE clause
- Follow-up questions work without repeating context

### Starting Point
```bash
cd examples/e2b_mockup/web_ui
cat NEXT_STEPS.md  # Read the detailed guide
cat app.py | grep -A 50 "async def process_message"  # See current implementation
```

Please integrate Claude Agent SDK to replace the template pattern matching system while keeping all the E2B infrastructure intact.
