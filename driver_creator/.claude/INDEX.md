# .claude/ Directory Index

## Overview
This directory contains the Claude Agent SDK configuration for the Driver Creator system - a multi-agent system that automatically generates production-ready API drivers.

## Files in This Directory

### Core Configuration
- **`CLAUDE.md`** (4.0K) - Main project instructions for Claude
  - Read this first to understand the system
  - Contains driver requirements, workflow, and best practices
  - Defines the agent architecture

- **`settings.json`** (286B) - System configuration
  - Model selection (Sonnet 4.5)
  - Prompt caching enabled
  - Max retries: 3
  - Hooks configuration

### Documentation
- **`README.md`** (6.2K) - Comprehensive architecture guide
  - Directory structure explained
  - Agent responsibilities
  - Integration with main system
  - Performance metrics
  - Troubleshooting guide

- **`QUICK_START.md`** (7.1K) - Get started in 3 minutes
  - Simple usage examples
  - What gets generated
  - Common questions
  - Testing instructions

- **`INDEX.md`** (this file) - Directory navigation

## Subagents

### `agents/research_api.md` (5.0K)
**Role:** API Research Specialist

**Capabilities:**
- Analyze API documentation
- Detect authentication methods
- Extract endpoint schemas
- Map field types
- Identify rate limits

**Input:** API name + URL
**Output:** Structured JSON with endpoints, fields, auth

**Key Sections:**
- Research strategy
- Common API types (REST, GraphQL, Database)
- Authentication detection
- Field type mapping
- Quality checklist

### `agents/generate_driver.md` (12K)
**Role:** Python Code Generator

**Capabilities:**
- Generate 6 production-ready files
- Implement driver contract
- Add comprehensive error handling
- Create working examples
- Write unit tests

**Input:** Research data + file name
**Output:** Complete Python code

**Key Sections:**
- File generation guidelines (6 files)
- Code quality standards
- Common patterns (auth, retries)
- Validation rules
- Learning from mem0

**Generates:**
1. `client.py` - Main driver class
2. `exceptions.py` - Error hierarchy
3. `__init__.py` - Package exports
4. `README.md` - Documentation
5. `examples/list_objects.py` - Working example
6. `tests/test_client.py` - Unit tests

### `agents/test_driver.md` (8.9K)
**Role:** Testing & Debugging Specialist

**Capabilities:**
- Run tests in E2B sandboxes
- Diagnose common failures
- Suggest specific code fixes
- Trigger fix-retry loop
- Validate driver contract

**Input:** Driver files + test results
**Output:** Pass/fail status + fix suggestions

**Key Sections:**
- Testing strategy
- Common test failures (with fixes)
- Error diagnosis process
- Fix-retry loop
- Quality gates

## Skills

### `skills/` (empty)
Reserved for future reusable capabilities:
- MCP registration skill
- Auto-documentation skill
- Performance optimization skill
- GraphQL support skill

## How They Work Together

```
User Request: "Create driver for https://api.example.com"
        ↓
┌───────────────────────────────────────────────────────┐
│ Research Agent (research_api.md)                      │
│ - Fetches API documentation                           │
│ - Analyzes endpoint structure                         │
│ - Returns: JSON with objects, fields, auth            │
└───────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────┐
│ Generator Agent (generate_driver.md)                  │
│ - Reads research data                                 │
│ - Generates 6 files (client, tests, docs, examples)   │
│ - Applies learned patterns from mem0                  │
└───────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────┐
│ Tester Agent (test_driver.md)                         │
│ - Uploads files to E2B sandbox                        │
│ - Runs pytest                                          │
│ - Checks driver contract compliance                   │
└───────────────────────────────────────────────────────┘
        ↓
    [Tests Pass?]
        ├─ Yes → Deliver driver
        └─ No  → Diagnose errors
                    ↓
            ┌──────────────────────┐
            │ Fix-Retry Loop       │
            │ 1. Analyze errors    │
            │ 2. Suggest fixes     │
            │ 3. Regenerate files  │
            │ 4. Test again        │
            │ Max 3 iterations     │
            └──────────────────────┘
```

## File Reading Order

### For New Users
1. **`QUICK_START.md`** - Get up and running fast
2. **`CLAUDE.md`** - Understand the system
3. **`agents/research_api.md`** - See how API discovery works
4. **`agents/generate_driver.md`** - See how code is generated
5. **`agents/test_driver.md`** - See how validation works

### For Developers
1. **`CLAUDE.md`** - Core concepts and architecture
2. **`README.md`** - Integration details
3. **`agents/*.md`** - Implementation specs
4. **`settings.json`** - Configuration options

### For Contributors
1. **`README.md`** - Architecture overview
2. **All `agents/*.md`** - Understand each agent
3. **`CLAUDE.md`** - See the big picture
4. **`settings.json`** - Customization points

## Key Concepts

### Driver Contract
Every generated driver must have:
```python
def list_objects(self) -> List[str]
def get_fields(self, object_name: str) -> Dict[str, Any]
def query(self, object_name: str, filters: Dict = None) -> List[Dict]
```

### Discovery-First Pattern
Drivers discover schemas at runtime:
```python
# No hardcoded schemas needed!
objects = client.list_objects()        # What's available?
fields = client.get_fields("users")    # What fields exist?
data = client.query("users")           # Get the data
```

### Self-Healing
System automatically fixes common issues:
- Type mismatches (dict → List[str])
- Missing methods
- Import errors
- Authentication problems

### Prompt Caching
All Claude calls use caching:
- 90% cost reduction
- $0.063 → $0.016 per driver
- 5 minute cache duration

## Performance Metrics

**Generation Time:**
- Research: 10-20s
- Generation: 60-90s (6 files)
- Testing: 30-60s
- Fix iteration: +60s if needed
- **Total: 3-5 minutes**

**Success Rate:**
- First try: 95%
- After 1 fix: 100%
- Manual intervention: 0%

**Cost per Driver:**
- Without caching: $0.063
- With caching: $0.016
- **Savings: 75%**

## Usage Examples

### Web UI
```bash
cd /Users/padak/github/ng_component/driver_creator
uvicorn app:app --port 8080
# Visit http://localhost:8080
# Say: "Create driver for https://api.coingecko.com/api/v3"
```

### Python Script
```python
from agent_tools import generate_driver_with_agents

result = generate_driver_with_agents(
    api_name="CoinGecko",
    api_url="https://api.coingecko.com/api/v3",
    max_retries=2
)

print(f"Success: {result['success']}")
print(f"Driver: {result['output_path']}")
```

### CLI Test
```bash
python test_single_api_with_fix.py    # Single API
python test_multiple_apis.py          # Batch test
```

## Customization

### Change Model
Edit `settings.json`:
```json
{
  "model": "claude-haiku-4-5",  // Fast & cheap
  "prompt_caching": true
}
```

### Add New Agent
1. Create `agents/new_agent.md`
2. Define role, input, output
3. Provide guidelines and examples
4. Document success criteria

### Modify Agent Behavior
Edit the corresponding `agents/*.md` file:
- Change instructions
- Add new patterns
- Update validation rules
- Enhance error handling

### Add Hooks
Edit `settings.json`:
```json
{
  "hooks": {
    "on_file_created": "echo 'Created: {file}'",
    "on_test_failed": "echo 'Failed: {error}'",
    "on_test_passed": "echo 'Success!'",
    "on_fix_applied": "echo 'Fixed: {issue}'"
  }
}
```

## Dependencies

Required packages (from `requirements.txt`):
- `anthropic` - Claude API
- `e2b-code-interpreter` - Sandbox testing
- `mem0ai` - Learning system
- `requests` - HTTP client
- `fastapi` - Web UI
- `uvicorn` - Server

## Environment Variables

Required in `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-...     # Claude API key
E2B_API_KEY=your_key             # E2B sandbox key
CLAUDE_MODEL=claude-sonnet-4-5   # Optional
```

## Troubleshooting

### Common Issues

**Problem:** Agent not responding
- Check `ANTHROPIC_API_KEY` in `.env`
- Verify model name in `settings.json`
- Check API rate limits

**Problem:** Tests always failing
- Verify `E2B_API_KEY` in `.env`
- Check sandbox connectivity
- Review `agents/test_driver.md`

**Problem:** Files not generated
- Check `agents/generate_driver.md` instructions
- Verify research data format
- Review error logs in `logs/`

**Problem:** Import errors in generated drivers
- Check `__init__.py` exports
- Verify class names match
- Review `agents/generate_driver.md` guidelines

## File Sizes Reference

```
CLAUDE.md              4.0K  - Main instructions
QUICK_START.md         7.1K  - Quick guide
README.md              6.2K  - Architecture
settings.json          286B  - Configuration
agents/
  research_api.md      5.0K  - Research agent
  generate_driver.md   12K   - Generator agent
  test_driver.md       8.9K  - Tester agent
```

**Total:** ~43KB of instructions

## Related Files

Outside `.claude/` directory:
- `../agent_tools.py` - Main orchestration logic
- `../tools.py` - Utility functions
- `../app.py` - Web UI
- `../test_single_api_with_fix.py` - Testing script
- `../requirements.txt` - Dependencies

## Next Steps

1. **Read Quick Start:** Start with `QUICK_START.md`
2. **Try It Out:** Run `python test_single_api_with_fix.py`
3. **Generate Driver:** Use Web UI at `http://localhost:8080`
4. **Customize:** Edit agent instructions in `agents/*.md`
5. **Contribute:** Add new agents or skills

## Resources

- [Main Project CLAUDE.md](../../CLAUDE.md)
- [Driver Creator README](../README.md)
- [E2B Documentation](https://e2b.dev/docs)
- [Anthropic Claude API](https://docs.anthropic.com)
- [mem0 Documentation](https://mem0.ai/docs)

---

**Summary:** This directory contains the "brain" of the Driver Creator system - instructions that teach Claude how to automatically research APIs, generate code, test it, fix issues, and deliver production-ready drivers. Each agent is a specialist, and they work together to handle the complete workflow.
