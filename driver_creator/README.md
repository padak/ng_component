# Driver Creator Agent

🤖 **AI-powered tool for generating production-ready data integration drivers**

Driver Creator Agent uses Claude Sonnet 4.5 to automatically generate driver code following the [Driver Design v2.0](../docs/driver_design_v2.md) specification. The agent researches APIs, generates scaffolds, validates code, and tests drivers in isolated E2B sandboxes - saving 75%+ development time.

---

## 🎯 What It Does

Given an API name (like "PostHog", "Stripe", "PostgreSQL"), the agent:

1. **Researches** → Fetches documentation, analyzes API structure, identifies patterns
2. **Evaluates** → Determines automation level (LEVEL_1/2/3: 90%/60%/40%)
3. **Generates** → Creates complete driver scaffold with templates
4. **Validates** → Checks against Driver Design v2.0 spec
5. **Tests** → Runs driver in E2B sandbox to verify functionality

**Result:** Production-ready driver in 2-4 hours (vs 8-14 hours manual development)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11-3.13** (⚠️ Python 3.14 not yet supported due to pydantic-core compatibility)
- [Anthropic API key](https://console.anthropic.com/)
- [E2B API key](https://e2b.dev/) (for driver testing)

> **Note:** Python 3.14 is too new - pydantic-core (required by FastAPI) doesn't support it yet. Please use Python 3.11, 3.12, or 3.13.

### Installation

```bash
# Navigate to driver_creator directory
cd driver_creator

# Create virtual environment with Python 3.11-3.13
# Option 1: Use system Python (if 3.11-3.13)
python3.13 -m venv venv  # or python3.12, python3.11

# Option 2: Use pyenv to install specific version
# pyenv install 3.13.0
# pyenv local 3.13.0
# python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify Python version (must be 3.11-3.13)
python --version

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# ANTHROPIC_API_KEY=sk-ant-...
# E2B_API_KEY=e2b_...
```

### Run the Agent

```bash
# Start the web UI (with reload exclusions to prevent restart during driver generation)
uvicorn app:app --reload --reload-exclude 'generated_drivers/*' --port 8081

# Open browser
open http://localhost:8081/static/
```

**Important:** Use `--reload-exclude 'generated_drivers/*'` to prevent uvicorn from restarting when drivers are generated. Without this, E2B testing will be interrupted!

---

## 💬 Example Conversations

### Create PostHog Driver

```
You: Create a driver for PostHog API

Agent: I'll research PostHog API and generate a driver. Let me start by fetching documentation...

[Agent uses research_api tool]

Agent: I found PostHog API:
- Type: REST API
- Query Language: HogQL (SQL-like)
- Authentication: API Key (Bearer token)
- Endpoints: /api/query, /api/event, /api/person, /api/session
- Pagination: Cursor-based (SEEK)
- Rate Limit: 2400 requests/hour
- Complexity: MEDIUM

[Agent uses evaluate_complexity tool]

Agent: I can automate 60% of this driver:

✅ Can Generate:
- Driver scaffold (BaseDriver implementation)
- HogQL query execution
- Discovery methods (list_objects, get_fields)
- Exception hierarchy
- README with examples
- Basic unit tests

⚠️ Needs Your Input:
- HogQL query parser (complex syntax)
- Property flattening logic
- SEEK-based pagination implementation
- Integration tests with real API

Shall I proceed with generation?

You: Yes, generate it

[Agent uses generate_driver_scaffold tool]

Agent: ✅ Driver generated!

📁 Created: generated_drivers/posthog_driver/
📄 Files: 9 files (1,234 lines of code)
✅ Complete: 7 files
⚠️ TODOs: 2 files need review

[Agent uses validate_driver tool]

Agent: Validation Results:
✅ BaseDriver inheritance: OK
✅ Required methods: OK
✅ Exception hierarchy: OK
✅ Documentation: OK
✅ Examples: OK (3 examples)
⚠️ TODOs: 2 remaining (review needed)

[Agent uses test_driver_in_e2b tool]

Agent: Testing in E2B sandbox...

Test Results:
✅ Driver initialization
✅ list_objects() - 4 objects found
✅ get_fields() - 23 fields validated
✅ read() - Query executed successfully
✅ Error handling - Proper exceptions

🎉 Driver validated! Ready for production use.

Next steps:
1. Review TODOs in client.py (lines 156, 234)
2. Implement HogQL query parser
3. Add integration tests

Download driver?
```

---

## 🛠️ Features

### 1. API Research

The agent automatically fetches and analyzes API documentation:

- Identifies API type (REST, GraphQL, SQL database)
- Detects authentication methods (API key, OAuth, JWT)
- Discovers endpoints and data structures
- Recognizes query languages (HogQL, SOQL, SQL)
- Assesses pagination styles (cursor, offset, page)

### 2. Complexity Evaluation

Classifies drivers into automation levels:

**LEVEL 1: Simple REST APIs (90% automation)**
- Examples: Weather API, JSONPlaceholder
- Time saved: 8 hours → 1 hour

**LEVEL 2: Query-Based Systems (60% automation)**
- Examples: PostHog (HogQL), Salesforce (SOQL), PostgreSQL (SQL)
- Time saved: 12 hours → 5 hours

**LEVEL 3: Complex Integrations (40% automation)**
- Examples: Multi-tenant SaaS, custom protocols
- Time saved: 14 hours → 8 hours

### 3. Code Generation

Generates complete driver scaffold:

```
posthog_driver/
├── __init__.py          # Version, exports
├── client.py            # BaseDriver implementation (with TODOs)
├── exceptions.py        # Full exception hierarchy
├── README.md            # Complete documentation
├── examples/
│   ├── list_objects.py  # Example: Discovery
│   └── query_data.py    # Example: Querying
└── tests/
    └── test_client.py   # Unit tests with mocks
```

### 4. Validation

Checks driver against Driver Design v2.0:

- ✅ BaseDriver inheritance
- ✅ Required methods (list_objects, get_fields, read)
- ✅ Exception hierarchy (8+ custom exceptions)
- ✅ Documentation (README with required sections)
- ✅ Examples (3+ working scripts)
- ✅ Type hints (98%+ coverage)

### 5. E2B Testing

Tests driver in isolated sandbox:

- Creates E2B cloud VM
- Uploads driver files
- Optionally starts mock API
- Runs comprehensive test suite:
  - Driver initialization
  - Discovery methods
  - Query execution
  - Error handling
- Returns detailed pass/fail results

---

## 🔧 Configuration

### Environment Variables

```bash
# Anthropic API Key (required)
ANTHROPIC_API_KEY=sk-ant-...

# E2B API Key (required for testing)
E2B_API_KEY=e2b_...

# Claude Model (optional, default: claude-sonnet-4-5)
CLAUDE_MODEL=claude-sonnet-4-5
# Options: claude-sonnet-4-5, claude-sonnet-4, claude-haiku-4-5

# Server Configuration
HOST=0.0.0.0
PORT=8081

# Debug Mode
DEBUG=false
```

### Model Selection

- **claude-sonnet-4-5** (default) - Best for complex drivers, supports prompt caching
- **claude-sonnet-4** - Balanced performance
- **claude-haiku-4-5** - Fastest, cheapest (60x cheaper than Sonnet 4.5!)

All models support **prompt caching** (90% cost reduction on repeated prompts).

---

## 🏗️ Architecture

```
User (Browser)
    ↓ WebSocket
FastAPI Backend (app.py)
    ↓ Messages API
Claude Sonnet 4.5 (with 5 tools)
    ↓ Tool calls
Tool Handlers (tools.py):
  - research_api()          → Fetch API docs
  - evaluate_complexity()   → Assess automation level
  - generate_scaffold()     → Jinja2 templates
  - validate_driver()       → Spec compliance check
  - test_driver_in_e2b()   → E2B sandbox testing
    ↓
Agent returns: Code + TODOs + Validation + Test results
    ↓ WebSocket stream
Browser: Code preview + TODO list + Validation status
```

---

## 📖 Agent Tools

### 1. `research_api`

Fetches and analyzes API documentation.

**Input:** API name (e.g., "PostHog")
**Output:** API type, auth methods, endpoints, query language, complexity

### 2. `evaluate_complexity`

Assesses automation capability.

**Input:** Research data
**Output:** Automation level (1/2/3), percentage, what can be automated

### 3. `generate_driver_scaffold`

Generates driver files from templates.

**Input:** API name, research data
**Output:** Complete driver scaffold with TODOs

### 4. `validate_driver`

Validates driver against Driver Design v2.0 spec.

**Input:** Driver path
**Output:** Validation results (pass/fail for each check)

### 5. `test_driver_in_e2b`

Tests driver in isolated E2B sandbox.

**Input:** Driver path, driver name, test API URL
**Output:** Test results (tests passed/failed, errors, suggestions)

---

## 📂 Project Structure

```
driver_creator/
├── app.py                        # FastAPI + WebSocket backend
├── tools.py                      # Agent tool implementations
├── templates/                    # Jinja2 templates for code generation
│   ├── __init__.py.j2
│   ├── client.py.j2
│   ├── exceptions.py.j2
│   ├── README.md.j2
│   ├── example_script.py.j2
│   └── test_client.py.j2
├── static/                       # Web UI
│   ├── index.html
│   ├── style.css
│   └── app.js
├── generated_drivers/            # Output directory
│   └── posthog_driver/          # Example generated driver
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🧪 Testing

### Manual Testing

```bash
# 1. Start the agent
uvicorn app:app --reload --port 8081

# 2. Open browser
open http://localhost:8081/static/

# 3. Try generating a driver
You: "Create a driver for Stripe Payment API"

# 4. Review generated code
# Check: generated_drivers/stripe_driver/

# 5. Verify E2B testing worked
# Look for test results in chat
```

### Automated Testing

```bash
# Run unit tests (future)
pytest tests/

# Test with mock APIs
cd generated_drivers/posthog_driver
pytest tests/test_client.py
```

---

## 🎓 Learn More

- 📚 [Driver Design v2.0 Spec](../docs/driver_design_v2.md)
- 📖 [Driver Creator PRD](../docs/prd-agent-driver-creator.md)
- 🏗️ [Architecture Overview](../CLAUDE.md)
- 🔧 [Web UI Integration](../examples/e2b_mockup/web_ui/CLAUDE_INTEGRATION_SUMMARY.md)

---

## 🐛 Troubleshooting

### "Connection failed" in browser

**Problem:** WebSocket cannot connect to backend

**Solution:**
```bash
# Check if backend is running
uvicorn app:app --reload --port 8081

# Check firewall allows port 8081
# Open http://localhost:8081/health to verify
```

### "ANTHROPIC_API_KEY not found"

**Problem:** API key not set in environment

**Solution:**
```bash
# Edit .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# Or set in environment
export ANTHROPIC_API_KEY=sk-ant-...
```

### "E2B_API_KEY not found" during testing

**Problem:** E2B key not set (required for test_driver_in_e2b tool)

**Solution:**
```bash
# Get API key from https://e2b.dev/
echo "E2B_API_KEY=e2b_..." >> .env
```

### Generated driver has many TODOs

**Expected behavior** for complex drivers (LEVEL_2/3):
- Agent generates 60-90% complete code
- TODOs mark complex logic that needs human input
- Review TODOs and implement custom logic
- Re-run validation after completion

### E2B tests fail

**Possible causes:**
1. Mock API not available → Set `use_mock_api=True`
2. Invalid API credentials → Check test_credentials
3. API endpoint changed → Regenerate driver with updated research
4. E2B timeout → Increase timeout or reduce test scope

---

## 🤝 Contributing

Contributions welcome! To add new features:

1. **New Templates:** Add Jinja2 templates to `templates/`
2. **New Tools:** Add tool functions to `tools.py`
3. **Agent Improvements:** Update system prompt in `app.py`
4. **UI Enhancements:** Modify `static/` files

---

## 📝 License

MIT

---

## 🙏 Acknowledgments

- Built with [Anthropic Claude](https://www.anthropic.com/)
- Isolated testing with [E2B Code Interpreter](https://e2b.dev/)
- Following [Driver Design v2.0](../docs/driver_design_v2.md) specification
- Inspired by Anthropic's [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)

---

**Ready to build the future of driver development! 🚀**
