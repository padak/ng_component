# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository implements an **Agent-Based Integration System** - a proof-of-concept demonstrating how AI agents can dynamically generate and execute integration scripts for external systems (like Salesforce) without hardcoded schemas.

**Core Vision**: "10% is the technical logic itself, 90% is productization — and the agent handles those 90%."

See `docs/prd.md` for complete product requirements.

## Repository Structure

```
ng_component/
├── docs/
│   ├── prd.md           # Product Requirements Document
│   └── idea.md          # Original concept notes
│
└── examples/e2b_mockup/  # Working proof-of-concept
    ├── agent_executor.py      # Main orchestrator (uploads & starts everything in E2B)
    ├── script_templates.py    # Pre-built templates for generating scripts
    ├── example_usage.py       # Usage examples
    ├── test_executor.py       # Main test suite
    ├── mock_api/              # FastAPI mock Salesforce (uploaded to sandbox)
    ├── salesforce_driver/     # Python client for agents (uploaded to sandbox)
    ├── test_data/             # DuckDB with 180 test records (uploaded to sandbox)
    ├── test_scenarios/        # Integration test scenarios
    └── web_ui/                # Web UI with Claude SDK integration
        ├── app.py             # FastAPI + WebSocket backend with Claude Sonnet 4.5
        ├── static/index.html  # Chat interface frontend
        └── CLAUDE_INTEGRATION_SUMMARY.md  # Integration documentation
```

## Key Architecture Concepts

### Discovery-First Pattern

Agents don't need pre-existing knowledge of system schemas:

```python
# 1. Discover objects
objects = client.list_objects()  # ["Lead", "Campaign", ...]

# 2. Discover fields
fields = client.get_fields("Lead")  # {schema with types}

# 3. Generate query dynamically
query = f"SELECT {', '.join(fields.keys())} FROM Lead"
```

### E2B Sandbox Execution

All agent-generated code runs in isolated E2B cloud sandboxes (VMs):

**Architecture:**
- Mock API, DuckDB, and driver all run INSIDE the sandbox
- Scripts call `localhost:8000` (same machine, inside sandbox)
- No network translation needed - everything is local to the sandbox
- AgentExecutor uploads: API code, database file, driver code

**API:**
- Use `Sandbox.create(api_key=...)` not `Sandbox()`
- Cleanup: Use `sandbox.kill()` not `sandbox.close()`

### Driver Contract

Every driver must implement:
- `list_objects() -> List[str]` - Discover available objects
- `get_fields(object_name: str) -> Dict[str, Any]` - Get field schema
- `query(soql: str) -> List[Dict]` - Execute queries

## Common Development Commands

### Setup

```bash
# Install dependencies (use project venv)
source .venv/bin/activate
pip install -r examples/e2b_mockup/requirements.txt

# Initialize test database
cd examples/e2b_mockup/test_data
python setup.py
```

### Running Components

```bash
# Run Web UI with Claude SDK (RECOMMENDED for interactive use)
cd examples/e2b_mockup/web_ui
uvicorn app:app --reload --port 8080
# Visit http://localhost:8080/static/

# Run E2B integration tests (AgentExecutor handles Mock API automatically)
cd examples/e2b_mockup
python test_executor.py

# Run test scenarios
cd examples/e2b_mockup/test_scenarios
python run_all_scenarios.py

# Test driver locally (without E2B, requires manually starting Mock API)
cd examples/e2b_mockup/mock_api
python main.py  # Start in separate terminal

# Then in another terminal:
cd examples/e2b_mockup
PYTHONPATH=. SF_API_URL=http://localhost:8000 SF_API_KEY=test_key \
  python salesforce_driver/examples/list_objects.py
```

### Testing SOQL Parser

```bash
cd examples/e2b_mockup/mock_api
python test_soql_parser.py
```

## Environment Variables

Required in `examples/e2b_mockup/.env`:

```bash
E2B_API_KEY=your_e2b_api_key                    # Required for E2B sandboxes
ANTHROPIC_API_KEY=your_anthropic_key            # Required for Claude SDK in Web UI
CLAUDE_MODEL=claude-sonnet-4-5-20250929         # Optional: Choose Claude model (default: Sonnet 4.5)
SF_API_URL=http://localhost:8000                # Used inside sandbox (always localhost:8000)
SF_API_KEY=test_key_12345                       # Mock API key
```

**Notes:**
- `SF_API_URL` should always be `http://localhost:8000` because this URL is used by scripts running inside the E2B sandbox to connect to the Mock API also running inside the same sandbox
- `ANTHROPIC_API_KEY` is only needed for the Web UI. If not set, Web UI falls back to pattern-matching mode
- `CLAUDE_MODEL` options (short names accepted, will be mapped to full IDs):
  - `claude-sonnet-4-5` → `claude-sonnet-4-5-20250929` (default) - Best for complex tasks. **Supports prompt caching** ✓
  - `claude-sonnet-4` → `claude-sonnet-4-20250514` - Balanced performance. **Supports prompt caching** ✓
  - `claude-haiku-4-5` → `claude-haiku-4-5-20251001` - Fastest, cheapest (60x cheaper than Sonnet 4.5!). **Supports prompt caching** ✓
  - `claude-haiku-3-5` → `claude-3-5-haiku-20241022` - Fast and cheap. **Supports prompt caching** ✓
- **Prompt Caching:** Supported by Opus 4.1/4/3, Sonnet 4.5/4/3.7, and Haiku 4.5/3.5/3. See [Anthropic docs](https://docs.claude.com/en/docs/build-with-claude/prompt-caching).
- Get your Anthropic API key from: https://console.anthropic.com/

## Architecture Flow

```
User Request ("Get leads from last 30 days")
    ↓
AgentExecutor (on host)
    ↓
1. Create E2B Sandbox (cloud VM)
2. Upload mock_api/ code to sandbox
3. Upload test_data/salesforce.duckdb to sandbox
4. Upload salesforce_driver/ to sandbox
5. Start Mock API inside sandbox (localhost:8000)
6. Run discovery (optional): list_objects(), get_fields()
7. Generate script from template
8. Execute script in sandbox
    ↓
    [Inside E2B Sandbox]
    Python Script → Salesforce Driver → Mock API (localhost:8000) → DuckDB
                   ←                   ←                           ←
    ↓
Results → AgentExecutor → User
```

**Key Points:**
- All components (API, DB, driver, scripts) run inside the same E2B sandbox
- No network communication between host and sandbox needed
- Scripts use `localhost:8000` to connect to API on same machine

## Web UI with Claude SDK Integration

The Web UI (`examples/e2b_mockup/web_ui/`) demonstrates the production-ready vision of the system:

**Features:**
- **Claude Sonnet 4.5 Integration**: Natural language query understanding with streaming responses
- **Tool Use**: Agent uses 4 tools for dynamic interaction:
  - `discover_objects` - List available Salesforce objects
  - `get_object_fields` - Get schema for specific object
  - `execute_salesforce_query` - Generate and execute Python scripts on-the-fly
  - `show_last_script` - Display generated code
- **Discovery-First**: Agent discovers schema before generating queries (no hardcoded field names!)
- **Streaming**: Token-by-token response streaming for better UX
- **Conversational**: Multi-turn conversations with full context preservation
- **WebSocket**: Real-time bidirectional communication
- **Prompt Caching**: 90% cost reduction on system prompt (cached for 5 minutes)
- **Model Selection**: Choose between Sonnet 4.5 (best), Sonnet 4 (balanced), or Haiku 4 (fastest/cheapest)

**Architecture:**
```
User Query (WebSocket)
    ↓
Web UI Backend (FastAPI + Claude SDK)
    ↓
Claude Sonnet 4.5 (with tools)
    ↓
Tool Execution → AgentExecutor → E2B Sandbox
    ↓
Results streamed back to user
```

**Starting the Web UI:**
```bash
cd examples/e2b_mockup/web_ui
uvicorn app:app --reload --port 8080
# Visit: http://localhost:8080/static/
```

**Example Queries:**
- "What data do you have?" → Discovers available objects
- "Show me all leads" → Generates and executes query
- "Get leads from last 30 days" → Adds date filtering
- "Show me the code" → Displays generated Python script

See `web_ui/CLAUDE_INTEGRATION_SUMMARY.md` for complete integration documentation.

## Known Limitations (By Design)

This is a proof-of-concept mockup:

1. **SOQL Parser**: Basic only (SELECT, WHERE, AND, dates). Date comparisons need quotes: `'2024-01-01'` not `2024-01-01`
2. **Mock Data**: Test database has 180 records across 4 tables (Account, Lead, Opportunity, Campaign)
3. **Single Driver**: Only Salesforce mock. Production supports multiple systems
4. **Mock API**: Simulated data. Production connects to real APIs

## Important Implementation Notes

### E2B SDK API

The E2B code-interpreter SDK uses:
- `Sandbox.create(api_key=...)` to create sandboxes
- `sandbox.sandbox_id` for ID (not `.id`)
- `sandbox.kill()` to cleanup (not `.close()`)
- `sandbox.run_code(code, envs={...})` for execution
- `sandbox.files.write(path, content)` to upload files (text or binary)

**Output Handling:**
- `result.text` - Last expression value (not print statements!)
- `result.logs.stdout` - List of stdout lines from print()
- `result.logs.stderr` - List of stderr lines
- `result.error` - Exception if code failed

Example:
```python
# This returns None in result.text
result = sandbox.run_code("print('Hello')")
print(result.logs.stdout)  # ['Hello\n']

# This returns 8 in result.text
result = sandbox.run_code("x = 5 + 3\nx")
print(result.text)  # 8
```

### PYTHONPATH for Driver

When testing driver examples locally:
```bash
PYTHONPATH=. python salesforce_driver/examples/script.py
```

### Network Access in Sandbox

All services run INSIDE the E2B sandbox:
- Mock API is uploaded and started inside the sandbox on `localhost:8000`
- DuckDB database file is uploaded to the sandbox filesystem
- Scripts execute inside the sandbox and call `localhost:8000`
- No network translation needed - everything is local to the sandbox VM

### Using AgentExecutor

The `AgentExecutor` class handles all E2B setup automatically:

```python
from agent_executor import AgentExecutor

# Create executor (automatically uploads everything to E2B and starts Mock API)
executor = AgentExecutor()

# Execute a request (generates script, runs in E2B sandbox, returns results)
result = executor.execute("Get all leads from last 30 days")

# Result contains:
# - result['success']: True/False
# - result['data']: List of records
# - result['script']: Generated Python code
# - result['output']: Execution output

# Cleanup
executor.close()  # Kills sandbox and Mock API
```

**What AgentExecutor does automatically:**
1. Creates E2B sandbox (cloud VM)
2. Uploads `mock_api/` folder to `/home/user/mock_api/`
3. Uploads `test_data/salesforce.duckdb` to `/home/user/test_data/`
4. Uploads `salesforce_driver/` to `/home/user/salesforce_driver/`
5. Installs dependencies (fastapi, uvicorn, duckdb, pydantic)
6. Starts uvicorn on background port 8000
7. Waits for API to be ready
8. Executes your script with `PYTHONPATH=/home/user`

## Testing Strategy

1. **Unit tests**: `mock_api/test_soql_parser.py` (SOQL parsing)
2. **Integration tests**: `test_executor.py` (E2B + driver)
3. **Scenario tests**: `test_scenarios/*.py` (end-to-end capabilities)

Expected results:
- SOQL parser: 12/12 tests pass
- E2B integration: All core tests pass (upload, API startup, driver integration)
- Scenarios: 5/5 pass (needs E2B_API_KEY)

**Verified Working (2025-11-10):**
```
✓ Files uploaded to E2B sandbox (mock_api, test_data, salesforce_driver)
✓ Mock API starts inside sandbox on localhost:8000
✓ Driver queries API successfully from within sandbox
✓ Complete flow: Upload → Start API → Query → Return results
✓ Web UI with Claude SDK: Natural language → Tool use → Script generation → Execution
✓ Streaming responses with real-time tool execution status
✓ Campaign object properly mapped (Account, Lead, Opportunity, Campaign all working)
```

## What Success Looks Like

✅ Core architecture validated:
- Mock API serves realistic Salesforce responses
- Driver provides discovery capabilities
- E2B sandboxes execute generated code
- Agent can build queries dynamically from discovered schemas

The mockup proves the "discovery → generate → execute" pattern works.

## Common Pitfalls

### ❌ Don't: Try to run Mock API on host machine
```python
# WRONG - This won't work with E2B sandboxes
# Start API locally: cd mock_api && python main.py
# Sandbox tries to reach host localhost - FAILS!
```

### ✅ Do: Let AgentExecutor handle everything
```python
# CORRECT - AgentExecutor uploads and starts API in sandbox
executor = AgentExecutor()  # Everything automatic!
```

### ❌ Don't: Use host.docker.internal
```python
# WRONG - E2B is NOT Docker, this doesn't exist
api_url = "http://host.docker.internal:8000"
```

### ✅ Do: Use localhost in sandbox
```python
# CORRECT - Everything runs in same E2B VM
api_url = "http://localhost:8000"
```

### ❌ Don't: Expect print() in result.text
```python
# WRONG - result.text will be None!
result = sandbox.run_code("print('Hello')")
print(result.text)  # None
```

### ✅ Do: Use result.logs.stdout for print output
```python
# CORRECT - print() goes to logs.stdout
result = sandbox.run_code("print('Hello')")
print(result.logs.stdout)  # ['Hello\n']

# Or return a value for result.text
result = sandbox.run_code("'Hello'")  # Last expression
print(result.text)  # 'Hello'
```

## Next Steps for Production

1. ✅ ~~Replace script templates with Claude Sonnet 4.5 API for dynamic generation~~ → **DONE** (Web UI)
2. ✅ ~~Add prompt caching for 90% cost reduction~~ → **DONE** (Implemented 2025-11-11)
3. ✅ ~~Implement proper error handling~~ → **DONE** (API overload, rate limits, auth errors)
4. Add more drivers (PostgreSQL, HubSpot, REST APIs)
5. Implement MCP server registration for drivers
6. Enhance SOQL parser (OR, IN, NOT, subqueries)
7. Add discovery results caching per session
8. Add monitoring and logging for production use
9. Implement retry logic with exponential backoff for API errors
10. Add user authentication and session persistence
11. Create frontend for managing multiple data source connections
