# Salesforce Integration Designer Agents

Complete interactive agent system for designing Salesforce integrations using AI and E2B sandboxes.

## Overview

This system provides **two ways** to interact with an AI agent that helps you design Salesforce integration scripts:

1. **CLI Agent** - Command-line interactive chat
2. **Web UI Agent** - Browser-based chat interface

Both agents provide the same capabilities:
- Conversational design process
- Discovery of available Salesforce objects and schemas
- Generation of Python integration scripts
- Execution in isolated E2B sandboxes
- Real-time results display

## Architecture

```
User (CLI or Web Browser)
    ↓
Agent (Claude Sonnet 4 via Agent SDK)
    ↓
AgentExecutor (E2B orchestration)
    ↓
E2B Sandbox (cloud VM)
    ├── Mock API (localhost:8000)
    ├── DuckDB (salesforce.duckdb)
    ├── Salesforce Driver
    └── Generated Script
```

## Prerequisites

1. **API Keys** (add to `.env`):
   ```bash
   E2B_API_KEY=your_e2b_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   SF_API_KEY=test_key_12345  # Already set
   ```

2. **Dependencies** (already installed if you ran pip install):
   ```bash
   pip install -r requirements.txt
   ```

## Option 1: CLI Agent

### Quick Start

```bash
# From examples/e2b_mockup/
python salesforce_designer_agent.py
```

### Features

- **Interactive conversation** - Chat with the agent to design your integration
- **Discovery commands** - Agent can list objects, inspect schemas
- **Script generation** - AI generates Python scripts based on your requirements
- **E2B execution** - Scripts run in isolated sandboxes with real API
- **Result display** - See query results formatted and readable

### Example Session

```
================================================================================
  SALESFORCE INTEGRATION DESIGNER AGENT
================================================================================

I'll help you design Python scripts for Salesforce data operations.
Type 'help' for commands, 'quit' to exit.

You: What Salesforce objects are available?

Agent: Let me check the available objects in the system...
       [Uses Read tool to check driver documentation]

       The system has three main Salesforce objects:

       1. **Lead** - Contact information and sales prospects
          Fields: Id, Name, Email, Company, Status, CreatedDate

       2. **Campaign** - Marketing campaigns
          Fields: Id, Name, Status, StartDate, EndDate, NumberOfLeads

       3. **CampaignMember** - Links leads to campaigns
          Fields: Id, CampaignId, LeadId, Status, CreatedDate

       What would you like to do with this data?

You: Get all leads from the last 30 days

Agent: Perfect! I'll create a script to get leads from the last 30 days.
       Here's what I'll generate:

       ```python
       import sys
       sys.path.insert(0, '/home/user')
       from salesforce_driver import SalesforceClient
       import json
       from datetime import datetime, timedelta

       client = SalesforceClient('http://localhost:8000', 'test_key')

       date_threshold = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

       query = f"""
       SELECT Id, Name, Email, Company, Status, CreatedDate
       FROM Lead
       WHERE CreatedDate >= '{date_threshold}'
       ORDER BY CreatedDate DESC
       """

       leads = client.query(query)

       print(json.dumps({
           'count': len(leads),
           'leads': leads
       }, indent=2))
       ```

       Type 'execute' to run this in E2B sandbox, or 'save' to save it to a file.

You: execute

[E2B sandbox created, Mock API started, script executed...]

Execution Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Success!

Found 45 leads created in last 30 days

Sample leads:
  1. John Smith - Acme Corp (Status: New)
  2. Jane Doe - Tech Solutions (Status: Qualified)
  3. Bob Johnson - Marketing Inc (Status: Working)
  ... and 42 more

Full JSON output:
{
  "count": 45,
  "leads": [...]
}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You: save leads_last_30_days.py

Agent: ✓ Script saved to leads_last_30_days.py

       You can run it anytime with:
       python leads_last_30_days.py
```

### Special Commands

- `help` - Show available commands
- `execute` - Execute the last generated script in E2B
- `save <filename>` - Save the last generated script
- `clear` - Clear conversation history
- `quit` or `exit` - Exit the agent

## Option 2: Web UI Agent

### Quick Start

```bash
# From examples/e2b_mockup/
cd web_ui
./start.sh

# Or manually:
uvicorn web_ui.app:app --reload --port 8080
```

Then open: **http://localhost:8080/static/**

### Features

- **Modern chat interface** - Beautiful UI with message bubbles
- **Real-time updates** - See agent thinking and tool usage
- **Formatted results** - JSON syntax highlighting, formatted output
- **Connection status** - Visual indicator when connected
- **Auto-scroll** - Always see the latest messages

### Example Queries

Try these in the Web UI:

```
"What objects are available?"
"What fields does Lead have?"
"Get all leads from last 30 days"
"Show me leads with status New"
"Get leads for Summer Campaign"
"Help"
```

### Web UI Screenshot Flow

1. **Connect** - Green dot shows connection status
2. **Ask** - Type your question or request
3. **Watch** - See agent thinking, using tools
4. **Results** - Beautifully formatted query results
5. **Iterate** - Refine your query based on results

## Agent Capabilities

### Discovery

The agent can discover what's available in Salesforce:

```
"What objects are available?"
→ Lists: Lead, Campaign, CampaignMember

"What fields does Lead have?"
→ Shows schema: Id, Name, Email, Company, Status, CreatedDate, etc.
```

### Query Generation

Based on natural language, generates SOQL queries:

```
"Get leads from last 30 days"
→ WHERE CreatedDate >= '2024-10-10'

"Show me New leads"
→ WHERE Status = 'New'

"Get leads for Summer Campaign"
→ Joins Campaign and CampaignMember tables
```

### Execution

Scripts run in **isolated E2B sandboxes**:

- ✅ No access to your local machine
- ✅ Clean environment per execution
- ✅ Mock API with realistic test data (180 records)
- ✅ Results returned safely

### Result Display

Results are formatted and easy to read:

- **Count** - Total records found
- **Sample** - First few records
- **JSON** - Complete data structure
- **Status breakdown** - For lead queries

## Advanced Usage

### CLI: Save and Reuse Scripts

```python
You: save my_query.py
Agent: ✓ Saved to my_query.py

# Later, run directly:
$ python my_query.py
```

### CLI: Iterate on Queries

```python
You: Get all leads

Agent: [generates script with all fields]

You: Actually, I only need Name and Email

Agent: [regenerates with just those fields]
```

### Web UI: Multiple Queries

The Web UI maintains one E2B sandbox per session, so you can:

1. Run discovery
2. Execute first query
3. Refine based on results
4. Execute second query
5. Continue iterating

All using the **same sandbox** for performance!

## Architecture Details

### E2B Sandbox Contents

When you execute a script, the E2B sandbox contains:

```
/home/user/
├── mock_api/
│   ├── main.py          # FastAPI server
│   ├── db.py            # DuckDB interface
│   └── soql_parser.py   # SOQL → SQL translator
├── test_data/
│   └── salesforce.duckdb  # 180 test records
├── salesforce_driver/
│   ├── client.py        # SalesforceClient
│   └── exceptions.py
└── [your_script.py]     # Generated script
```

### Execution Flow

1. **Upload** - AgentExecutor uploads all files to E2B sandbox
2. **Start API** - Mock API starts on `localhost:8000` inside sandbox
3. **Execute** - Your script runs, queries `localhost:8000`
4. **Return** - Results streamed back to you

Everything happens **inside the sandbox** - no network calls to your machine!

### Test Data

The Mock API serves **180 test records**:
- **Leads**: 100 records with various statuses (New, Qualified, Working, etc.)
- **Campaigns**: 10 marketing campaigns
- **CampaignMembers**: 70 lead-campaign associations

See `test_data/seeds/` for the CSV source data.

## Troubleshooting

### CLI Agent Issues

**"ANTHROPIC_API_KEY not set"**
```bash
# Add to .env:
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**"E2B_API_KEY not set"**
```bash
# Add to .env:
E2B_API_KEY=e2b_...
```

**Agent hangs or times out**
- Check internet connection (needs to reach Anthropic API)
- Verify API keys are valid
- Check E2B account quota

### Web UI Issues

**"Cannot connect to WebSocket"**
```bash
# Make sure server is running:
cd web_ui
./start.sh

# Check if port 8080 is available:
lsof -i :8080
```

**"Connection refused"**
- Ensure you're accessing `http://localhost:8080/static/` (note the `/static/` path)
- Check server logs for errors
- Verify all dependencies installed

**WebSocket disconnects**
- Normal after inactivity
- Browser will auto-reconnect
- Refresh page if needed

### E2B Execution Issues

**"Failed to create sandbox"**
- Check E2B API key validity
- Verify E2B account has quota remaining
- Check internet connectivity

**"Mock API not responding"**
- This is handled automatically by AgentExecutor
- If persists, check E2B sandbox logs
- May indicate E2B service issue

## Development

### Extending the Agent

The agent's behavior is defined in the **system prompt** in:
- `salesforce_designer_agent.py` (CLI)
- `web_ui/app.py` (Web UI)

To add new capabilities:

1. **Update system prompt** - Add new instructions
2. **Add new templates** - In `script_templates.py`
3. **Test** - Verify agent can use new capabilities

### Adding New Drivers

To support other systems (PostgreSQL, HubSpot, etc.):

1. Create driver in `<system>_driver/` (similar to `salesforce_driver/`)
2. Implement: `list_objects()`, `get_fields()`, `query()`
3. Update agent system prompt to know about new driver
4. Agent will automatically discover and use it!

### Running Tests

```bash
# Test the E2B integration
python test_executor.py

# Test the Web UI WebSocket
python web_ui/test_websocket.py
```

## Production Considerations

This is a **demo/mockup** system. For production:

### Replace Mock API

- [ ] Connect to real Salesforce API
- [ ] Implement OAuth authentication
- [ ] Handle rate limiting
- [ ] Add retry logic

### Enhance Agent

- [ ] Use Claude Sonnet 4.5 for better reasoning
- [ ] Add conversation history persistence
- [ ] Implement user authentication
- [ ] Add rate limiting per user

### Security

- [ ] Validate all user inputs
- [ ] Sanitize generated SQL/SOQL
- [ ] Implement proper CORS policies
- [ ] Add audit logging
- [ ] Encrypt sensitive data

### Scaling

- [ ] Add request queuing
- [ ] Implement E2B sandbox pooling
- [ ] Cache discovery results
- [ ] Add monitoring and alerting

## Files

```
examples/e2b_mockup/
├── salesforce_designer_agent.py    # CLI interactive agent
├── agent_executor.py               # E2B orchestrator
├── script_templates.py             # Pre-built templates
├── web_ui/
│   ├── app.py                      # FastAPI WebSocket server
│   ├── static/
│   │   └── index.html              # Web UI frontend
│   ├── test_websocket.py           # WebSocket test client
│   ├── start.sh                    # Quick start script
│   ├── README.md                   # Web UI docs
│   └── QUICKSTART.md               # Web UI quick start
├── salesforce_driver/              # Salesforce client
├── mock_api/                       # Mock Salesforce API
├── test_data/                      # Test database
└── AGENT_README.md                 # This file
```

## Next Steps

1. **Try the CLI agent**: `python salesforce_designer_agent.py`
2. **Try the Web UI**: `cd web_ui && ./start.sh`
3. **Experiment with queries**: Ask the agent to help you explore data
4. **Save useful scripts**: Build a library of integration scripts
5. **Extend**: Add new drivers for other systems!

## Support

For issues:
- Check `web_ui/README.md` for Web UI troubleshooting
- Check `web_ui/QUICKSTART.md` for quick setup
- Check `README.md` for E2B architecture details

---

**Happy Integrating! 🚀**
