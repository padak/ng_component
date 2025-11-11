# Next Steps: AgentSDK Integration

## Current State

The Web UI currently uses **template-based script generation** with pattern matching:
- User says "get all leads" → matches template → executes pre-built script
- Limitations: no understanding of context, no code generation, fixed patterns

## Goal

Replace the template system with **Claude Agent SDK (Anthropic)** for intelligent, conversational integration script generation.

## What Needs to Be Done

### 1. Replace AgentExecutor Pattern Matching with Claude Agent SDK

**Current implementation** (`web_ui/app.py` lines 161-224):
```python
async def process_message(self, user_message: str):
    # Simple pattern matching
    if 'leads' in user_lower:
        await self.handle_query_request(user_message)
```

**Target implementation**:
```python
async def process_message(self, user_message: str):
    # Use Claude Agent SDK to understand intent and generate scripts
    response = await self.claude_agent.query(user_message)
    # Agent generates Python code dynamically using discovery tools
```

### 2. Install Agent SDK Dependencies

Add to `examples/e2b_mockup/requirements.txt`:
```
anthropic>=0.40.0
# OR claude-agent-sdk if available
```

### 3. Create Claude Agent System Prompt

The agent needs to:
1. **Understand user intent** (conversational, not pattern matching)
2. **Use discovery tools** (`list_objects()`, `get_fields()`) to learn schema
3. **Generate Python scripts** dynamically that use `SalesforceClient`
4. **Execute in E2B** via existing `AgentExecutor.execute_script()`
5. **Display results** and optionally show generated code

**Key capabilities to implement**:
- Discovery-first approach (don't hardcode field names!)
- Generate SOQL queries based on discovered schema
- Handle follow-up questions ("show me the code", "filter by status New")
- Remember conversation context

### 4. Integration Architecture

```
User message
    ↓
WebSocket (app.py)
    ↓
Claude Agent SDK
    ↓
Agent generates Python script using:
    - Discovery tools (list_objects, get_fields)
    - SalesforceClient API
    - User requirements
    ↓
AgentExecutor.execute_script()
    ↓
E2B Sandbox execution
    ↓
Results back to user via WebSocket
```

### 5. Key Files to Modify

- **`web_ui/app.py`**: Replace pattern matching with Agent SDK
- **`agent_executor.py`**: Keep as-is (execution engine)
- **`script_templates.py`**: Keep for reference/examples
- **`requirements.txt`**: Add anthropic SDK

### 6. Agent Tools Definition

The Claude Agent needs access to these tools (via function calling):

```python
tools = [
    {
        "name": "discover_objects",
        "description": "List available Salesforce objects (Lead, Campaign, etc.)",
        "input_schema": {}
    },
    {
        "name": "discover_fields",
        "description": "Get field schema for a Salesforce object",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string"}
            }
        }
    },
    {
        "name": "execute_script",
        "description": "Execute Python script in E2B sandbox",
        "input_schema": {
            "type": "object",
            "properties": {
                "script": {"type": "string"},
                "description": {"type": "string"}
            }
        }
    }
]
```

### 7. Example Agent System Prompt

```
You are an expert Salesforce integration assistant. You help users query Salesforce data
by generating Python scripts that execute in E2B cloud sandboxes.

TOOLS AVAILABLE:
- discover_objects(): List available Salesforce objects
- discover_fields(object_name): Get field schema for an object
- execute_script(script, description): Run Python code in E2B sandbox

ALWAYS use discovery tools first to understand the schema before generating queries.

When user asks for data:
1. Discover available objects and fields
2. Generate a Python script using SalesforceClient
3. Execute it in the sandbox
4. Return results in a conversational way

The SalesforceClient is available at localhost:8000 inside the sandbox.

Example script structure:
```python
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient

client = SalesforceClient(
    api_url='http://localhost:8000',
    api_key='test_key'
)

# Discover fields first
schema = client.get_fields("Lead")
fields = list(schema['fields'].keys())

# Build query dynamically
query = f"SELECT {', '.join(fields[:10])} FROM Lead LIMIT 10"
results = client.query(query)

print(json.dumps(results))
```

Be conversational, explain what you're doing, and show code when user asks.
```

### 8. Testing Checklist

After implementation, test:
- [ ] "Get all leads" - should discover schema and generate query
- [ ] "Show me leads from last 30 days" - should use date filtering
- [ ] "Get 10 leads" - should respect limit
- [ ] "Show me the code" - should display generated Python script
- [ ] "What objects are available?" - should run discovery
- [ ] "Filter by status New" - should add WHERE clause
- [ ] Follow-up questions work (context preserved)

### 9. Environment Variables

Make sure these are set in `examples/e2b_mockup/.env`:
```bash
E2B_API_KEY=your_e2b_key
ANTHROPIC_API_KEY=your_anthropic_key  # NEW - for Agent SDK
SF_API_URL=http://localhost:8000
SF_API_KEY=test_key_12345
```

### 10. Reference Implementation

See `examples/e2b_mockup/salesforce_designer_agent.py` for a CLI-based agent example using similar patterns (though it needs updates to match the latest architecture).

## Success Criteria

✅ User can ask natural language questions
✅ Agent discovers schema dynamically (no hardcoded fields)
✅ Agent generates correct Python scripts
✅ Scripts execute in E2B sandbox successfully
✅ Results display in Web UI with markdown formatting
✅ User can ask "show me the code" and see generated script
✅ Conversation context is maintained across messages
✅ No more template pattern matching needed

## Commands to Run After Integration

```bash
# Start Web UI
cd examples/e2b_mockup/web_ui
./start.sh

# Visit http://localhost:8080/static/
# Test with natural language queries
```

## Notes

- The E2B sandbox setup (`AgentExecutor`) is already working - keep it!
- Mock API with DuckDB is already running inside sandbox - don't change it!
- Just replace the "brain" (pattern matching → Claude Agent SDK)
- All discovery and execution infrastructure is ready to use
