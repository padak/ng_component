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
    ├── agent_executor.py      # Main orchestrator
    ├── script_templates.py    # Pre-built templates
    ├── mock_api/              # FastAPI mock Salesforce
    ├── salesforce_driver/     # Python client for agents
    ├── test_data/             # DuckDB with 180 test records
    └── test_scenarios/        # Integration tests
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

All agent-generated code runs in isolated E2B cloud sandboxes:
- Network translation: `localhost:8000` (host) → `host.docker.internal:8000` (sandbox)
- API: Use `Sandbox.create(api_key=...)` not `Sandbox()`
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
# Start Mock API (keep running in separate terminal)
cd examples/e2b_mockup/mock_api
uvicorn main:app --reload --port 8000

# Run E2B integration tests
cd examples/e2b_mockup
python test_executor.py

# Run test scenarios
cd examples/e2b_mockup/test_scenarios
python run_all_scenarios.py

# Test driver locally (without E2B)
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
E2B_API_KEY=your_e2b_api_key      # Required for E2B sandboxes
SF_API_URL=http://localhost:8000   # Mock API endpoint
SF_API_KEY=test_key_12345          # Mock API key
```

## Architecture Flow

```
User Request ("Get leads from last 30 days")
    ↓
AgentExecutor
    ↓
1. Create E2B Sandbox
2. Upload salesforce_driver/ to sandbox
3. Run discovery (optional): list_objects(), get_fields()
4. Generate script from template
5. Execute in sandbox with envs
    ↓
Sandbox → Mock API (host.docker.internal:8000)
    ↓
Mock API → DuckDB (test_data/salesforce.duckdb)
    ↓
Results → AgentExecutor → User
```

## Known Limitations (By Design)

This is a proof-of-concept mockup:

1. **SOQL Parser**: Basic only (SELECT, WHERE, AND, dates). Date comparisons need quotes: `'2024-01-01'` not `2024-01-01`
2. **Templates**: Pre-built scripts. Production would use Claude Sonnet 4.5 to generate dynamically
3. **Single Driver**: Only Salesforce mock. Production supports multiple systems
4. **Mock API**: Simulated data. Production connects to real APIs

## Important Implementation Notes

### E2B SDK API Changes

The E2B code-interpreter SDK uses:
- `Sandbox.create(api_key=...)` to create sandboxes
- `sandbox.sandbox_id` for ID (not `.id`)
- `sandbox.kill()` to cleanup (not `.close()`)
- `sandbox.run_code(code, envs={...})` for execution

### PYTHONPATH for Driver

When testing driver examples locally:
```bash
PYTHONPATH=. python salesforce_driver/examples/script.py
```

### Network Access in Sandbox

Services on host `localhost` are accessible from sandbox via `host.docker.internal`. The `agent_executor.py` automatically translates URLs.

## Testing Strategy

1. **Unit tests**: `mock_api/test_soql_parser.py` (SOQL parsing)
2. **Integration tests**: `test_executor.py` (E2B + driver)
3. **Scenario tests**: `test_scenarios/*.py` (end-to-end capabilities)

Expected results:
- SOQL parser: 12/12 tests pass
- E2B integration: 3/5 tests pass (filesystem and driver loading are optional)
- Scenarios: 5/5 pass (needs E2B_API_KEY)

## What Success Looks Like

✅ Core architecture validated:
- Mock API serves realistic Salesforce responses
- Driver provides discovery capabilities
- E2B sandboxes execute generated code
- Agent can build queries dynamically from discovered schemas

The mockup proves the "discovery → generate → execute" pattern works.

## Next Steps for Production

1. Replace script templates with Claude Sonnet 4.5 API
2. Add more drivers (PostgreSQL, HubSpot, REST APIs)
3. Implement MCP server registration for drivers
4. Enhance SOQL parser (OR, IN, NOT, subqueries)
5. Add caching layer for discovery results
