# Unified Data Analytics Agent - Web UI

AI-powered multi-datasource analytics assistant with natural language query generation for both **Salesforce** and **PostHog**.

## Features

- **Multi-Data Source Support**: Seamlessly switch between Salesforce (SOQL) and PostHog (HogQL)
- **Claude Sonnet 4.5 Integration**: Natural language understanding for analytics queries
- **Dynamic Query Generation**: Automatically generates SOQL or HogQL queries based on data source
- **E2B Sandbox Execution**: Secure, isolated execution environment
- **Discovery-First Approach**: No hardcoded schemas - discovers resources dynamically
- **Real-time Streaming**: Token-by-token response streaming
- **Prompt Caching**: 90% cost reduction on repeated queries
- **Unified Interface**: Single UI for all your data sources

## Architecture

```
User Query ("Show me top leads from last month")
    ↓
Web UI (FastAPI + Claude SDK)
    ↓
Data Source Selector (Salesforce or PostHog)
    ↓
Claude Sonnet 4.5 (with source-specific tools)
    ├── discover_objects
    ├── get_object_fields
    ├── execute_query (SOQL or HogQL)
    └── show_last_script
    ↓
AgentExecutor (Salesforce) OR PostHogAgentExecutor (PostHog)
    ↓
E2B Sandbox → Mock API/PostHog API
    ↓
Results streamed back to user
```

## Setup

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or: venv\Scripts\activate  # On Windows

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# E2B API Key (required for both data sources)
E2B_API_KEY=e2b_xxxxxxxxxxxxxxxxxxxxx

# Anthropic API Key (required for Claude)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx

# PostHog Credentials (required for PostHog queries)
POSTHOG_API_KEY=phx_xxxxxxxxxxxxxxxxxxxxx
POSTHOG_PROJECT_ID=your_project_id
POSTHOG_REGION=us  # or "eu"

# Salesforce Credentials (automatically configured for mock API)
SF_API_URL=http://localhost:8000
SF_API_KEY=test_key_12345

# Optional: Choose Claude model
CLAUDE_MODEL=claude-sonnet-4-5-20250929  # Default (recommended)

# Optional: Enable prompt caching (default: true)
ENABLE_PROMPT_CACHING=true
```

**Get your API keys:**
- PostHog: https://posthog.com/project/settings/project-api-keys
- E2B: https://e2b.dev/
- Anthropic: https://console.anthropic.com/

### 3. Run the Server

```bash
uvicorn app:app --reload --port 8080
```

### 4. Access the Web UI

Open your browser to: **http://localhost:8080/static/**

## Usage

### Switching Data Sources

Use the dropdown in the top-right corner to switch between:
- **Salesforce**: Query CRM data with SOQL
- **PostHog**: Analyze product analytics with HogQL

The agent will automatically reconfigure when you switch, maintaining separate conversation contexts.

### Example Queries

#### Salesforce Queries

1. **Discover available data:**
   - "What objects do you have?"
   - "What fields are available in Lead?"

2. **Lead analysis:**
   - "Show me all open leads from the last month"
   - "Get leads with status = 'Qualified'"

3. **Account queries:**
   - "Show me all accounts created this year"
   - "List top 10 accounts by name"

4. **Opportunity tracking:**
   - "Show me opportunities with amount > 10000"
   - "Get all closed won opportunities"

#### PostHog Queries

1. **Discover available data:**
   - "What data do you have?"
   - "What fields are in events?"

2. **Event analysis:**
   - "Show me the most popular events from the last week"
   - "What are the top 10 events today?"

3. **User activity:**
   - "Show me the most active users"
   - "Get user activity from the last 7 days"

4. **Time-based analysis:**
   - "Show daily event counts for the last month"
   - "What's the trend in user signups this week?"

5. **View generated code:**
   - "Show me the code"
   - "Display the script"

## How It Works

### Discovery-First Pattern

The agent doesn't need pre-existing knowledge of your data schemas:

1. **User asks:** "Show me top leads"
2. **Agent discovers:** Calls `discover_objects()` → finds "Lead", "Account", etc.
3. **Agent explores:** Calls `get_fields("Lead")` → gets schema
4. **Agent generates:** Creates SOQL query based on schema
5. **Agent executes:** Runs query in E2B sandbox
6. **Agent presents:** Formats results with insights

### Tool Use

Claude has access to 4 tools (configured per data source):

**For Salesforce:**
1. **discover_objects** - Lists Salesforce objects (Lead, Account, Opportunity, etc.)
2. **get_object_fields** - Gets schema for a specific object
3. **execute_salesforce_query** - Generates and executes SOQL queries
4. **show_last_script** - Displays generated Python code

**For PostHog:**
1. **discover_objects** - Lists PostHog resources (events, persons, cohorts, etc.)
2. **get_object_fields** - Gets schema for a specific resource
3. **execute_posthog_query** - Generates and executes HogQL queries
4. **show_last_script** - Displays generated Python code

### Query Examples

**Salesforce (SOQL):**
```python
# Top leads from last 30 days
client.query('''
    SELECT Id, Name, Email, Status, CreatedDate
    FROM Lead
    WHERE CreatedDate >= 2024-10-01
    ORDER BY CreatedDate DESC
    LIMIT 100
''')
```

**PostHog (HogQL):**
```python
# Top events from last 7 days
driver.read('''
    SELECT event, count() as total
    FROM events
    WHERE timestamp >= now() - INTERVAL 7 DAY
    GROUP BY event
    ORDER BY total DESC
    LIMIT 10
''')
```

## System Architecture

### Components

**Frontend (static/index.html)**
- Tailwind CSS UI with real-time WebSocket
- Data source selector dropdown
- Markdown rendering for agent responses
- Collapsible code blocks
- Quick action buttons
- Token usage and cost tracking

**Backend (app.py)**
- FastAPI with WebSocket support
- Claude SDK integration (streaming)
- Multi-data source support (Salesforce + PostHog)
- Session management
- Prompt caching for cost optimization

**Executors**
- `AgentExecutor` (from e2b_mockup) - Salesforce queries
- `PostHogAgentExecutor` (from posthog_ui) - PostHog queries

**Drivers**
- `SalesforceClient` - Salesforce mock API client
- `PostHogDriver` - PostHog API client

### Data Flow

```
1. User selects data source (Salesforce or PostHog)
2. User types: "Show me top leads"
3. WebSocket sends message to backend
4. Backend calls Claude API with source-specific tools
5. Claude decides to use discover_objects tool
6. Backend calls appropriate executor
7. Executor runs script in E2B sandbox
8. Script queries API (Mock Salesforce or PostHog)
9. Results returned to Claude
10. Claude analyzes and generates response
11. Response streamed to frontend
12. User sees: "I found 50 leads..."
```

## Cost Optimization

### Prompt Caching

**Enabled by default** - reduces costs by 90% on repeated queries!

```bash
ENABLE_PROMPT_CACHING=true
```

**How it works:**
- System prompt (3,000+ tokens) cached for 5 minutes
- First request: Full cost
- Subsequent requests: 90% cheaper (cached prompt)

**Example costs:**
- Without caching: $0.045 per request
- With caching: $0.005 per request (after first)

### Model Selection

Choose the right model for your use case:

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| Sonnet 4.5 | Medium | $$ | Complex analytics, multi-step queries |
| Sonnet 4 | Fast | $ | Balanced performance |
| Haiku 4.5 | Fastest | ¢ | Simple queries, high volume (60x cheaper!) |

```bash
# Set in .env
CLAUDE_MODEL=claude-haiku-4-5-20251001  # For cost optimization
```

## Troubleshooting

### Connection Issues

**Error: "E2B_API_KEY is required"**
- Solution: Set `E2B_API_KEY` in your `.env` file
- Get key from: https://e2b.dev/

**Error: "ANTHROPIC_API_KEY not found"**
- Solution: Set `ANTHROPIC_API_KEY` in `.env`
- Get key from: https://console.anthropic.com/

**Error: "POSTHOG_API_KEY is required"**
- Solution: Set `POSTHOG_API_KEY` and `POSTHOG_PROJECT_ID` in `.env`
- Get key from: https://posthog.com/project/settings/project-api-keys

### Query Issues

**Error: "Unknown resource"**
- Solution: Ask "What data do you have?" to discover available resources
- The agent will show you what's available

**Error: "Query syntax error"**
- The agent should handle syntax automatically
- If errors persist, try asking to "show me the code" and check the query

### Performance Issues

**Slow responses:**
- Check your internet connection
- E2B sandbox creation takes 5-10 seconds on first request
- Subsequent queries are faster (sandbox is reused)

**High costs:**
- Enable prompt caching: `ENABLE_PROMPT_CACHING=true`
- Use Haiku 4.5 for simple queries: `CLAUDE_MODEL=claude-haiku-4-5-20251001`
- Monitor usage in the UI sidebar

## API Endpoints

- `ws://localhost:8080/chat` - WebSocket endpoint for chat
- `GET /health` - Health check
- `GET /api/info` - API information
- `GET /` - Root redirect
- `GET /static/` - Web UI

## Development

### Running in Development Mode

```bash
# With auto-reload
uvicorn app:app --reload --port 8080

# With debug logging
LOG_LEVEL=DEBUG uvicorn app:app --reload --port 8080
```

### Project Structure

```
unified_ui/
├── app.py                          # Unified backend with both data sources
├── static/
│   └── index.html                  # Frontend UI with data source selector
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
└── README.md                       # This file
```

## Production Considerations

1. **Security**
   - Use environment variables for all credentials
   - Never commit `.env` to version control
   - Consider rate limiting for public deployments

2. **Scaling**
   - Each WebSocket connection creates its own E2B sandbox
   - Monitor E2B usage and costs
   - Consider sandbox pooling for high traffic

3. **Monitoring**
   - Track token usage and costs per session
   - Log Claude API errors
   - Monitor E2B sandbox creation failures

4. **Cost Management**
   - Enable prompt caching (90% savings)
   - Use Haiku 4.5 for simple queries (60x cheaper)
   - Set user session timeouts
   - Monitor monthly API costs

## Advantages of Unified UI

- **Single Interface**: One UI for all your data sources
- **Consistent Experience**: Same familiar interface regardless of data source
- **Easy Comparison**: Switch between sources to compare data
- **Cost Efficient**: Shared infrastructure and prompt caching
- **Simpler Deployment**: One application to maintain

## License

This project is part of the ng_component proof-of-concept and follows the same license.

## Support

For issues and questions:
- Salesforce mock docs: See `examples/e2b_mockup/README.md`
- PostHog docs: https://posthog.com/docs
- HogQL reference: https://posthog.com/docs/hogql
- E2B docs: https://e2b.dev/docs
- Claude docs: https://docs.anthropic.com/

## Next Steps

1. Try example queries in the UI
2. Switch between Salesforce and PostHog data sources
3. Explore your data with natural language
4. View generated queries ("show me the code")
5. Experiment with different time ranges and filters
6. Monitor costs and optimize with prompt caching
