# PostHog Analytics Agent - Web UI

AI-powered PostHog analytics assistant with natural language HogQL query generation.

## Features

- **Claude Sonnet 4.5 Integration**: Natural language understanding for analytics queries
- **HogQL Query Generation**: Automatically generates and executes HogQL queries
- **E2B Sandbox Execution**: Secure, isolated execution environment
- **Discovery-First Approach**: No hardcoded schemas - discovers resources dynamically
- **Real-time Streaming**: Token-by-token response streaming
- **Prompt Caching**: 90% cost reduction on repeated queries

## Architecture

```
User Query ("Show me top events from last week")
    ↓
Web UI (FastAPI + Claude SDK)
    ↓
Claude Sonnet 4.5 (with tools)
    ├── discover_objects
    ├── get_object_fields
    ├── execute_posthog_query
    └── show_last_script
    ↓
PostHogAgentExecutor → E2B Sandbox → PostHog API
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

Create a `.env` file in this directory:

```bash
# PostHog Credentials
POSTHOG_API_KEY=phx_xxxxxxxxxxxxxxxxxxxxx
POSTHOG_PROJECT_ID=245832
POSTHOG_REGION=us  # or "eu" for EU cloud

# E2B API Key (for sandboxes)
E2B_API_KEY=e2b_xxxxxxxxxxxxxxxxxxxxx

# Anthropic API Key (for Claude)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx

# Optional: Choose Claude model
CLAUDE_MODEL=claude-sonnet-4-5-20250929  # Default (recommended)
# Other options:
#   claude-sonnet-4-20250514 (balanced)
#   claude-haiku-4-5-20251001 (fastest, cheapest)

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

## Usage Examples

### Example Queries

1. **Discover available data:**
   - "What data do you have?"
   - "What resources are available?"

2. **Event analysis:**
   - "Show me the most popular events from the last week"
   - "What are the top 10 events today?"
   - "Get all pageview events from the last 30 days"

3. **User activity:**
   - "Show me the most active users"
   - "Get user activity from the last 7 days"

4. **Time-based analysis:**
   - "Show daily event counts for the last month"
   - "What's the trend in user signups this week?"

5. **Property filtering:**
   - "Show events where browser is Chrome"
   - "Get all events with property X = Y"

6. **View generated code:**
   - "Show me the code"
   - "Display the script"

## How It Works

### Discovery-First Pattern

The agent doesn't need pre-existing knowledge of your PostHog schema:

1. **User asks:** "Show me top events"
2. **Agent discovers:** Calls `discover_objects()` → finds "events", "persons", etc.
3. **Agent explores:** Calls `get_fields("events")` → gets schema
4. **Agent generates:** Creates HogQL query based on schema
5. **Agent executes:** Runs query in E2B sandbox against PostHog API
6. **Agent presents:** Formats results with insights

### Tool Use

Claude has access to 4 tools:

1. **discover_objects**
   - Lists available PostHog resources
   - Returns: events, persons, cohorts, insights, etc.

2. **get_object_fields**
   - Gets schema for a specific resource
   - Returns: field names, types, descriptions

3. **execute_posthog_query**
   - Generates Python script with HogQL query
   - Executes in E2B sandbox
   - Returns: Query results as JSON

4. **show_last_script**
   - Displays the generated Python code
   - Useful for learning and debugging

### HogQL Examples

The agent generates queries like:

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

# User activity
driver.read('''
    SELECT distinct_id, count() as actions
    FROM events
    WHERE timestamp >= now() - INTERVAL 7 DAY
    GROUP BY distinct_id
    ORDER BY actions DESC
    LIMIT 100
''')

# Daily trends
driver.read('''
    SELECT toStartOfDay(timestamp) as day, count() as events
    FROM events
    WHERE timestamp >= now() - INTERVAL 30 DAY
    GROUP BY day
    ORDER BY day
''')
```

## System Architecture

### Components

**Frontend (static/index.html)**
- Tailwind CSS UI with real-time WebSocket
- Markdown rendering for agent responses
- Collapsible code blocks
- Quick action buttons
- Token usage and cost tracking

**Backend (app.py)**
- FastAPI with WebSocket support
- Claude SDK integration (streaming)
- Session management
- Prompt caching for cost optimization

**Executor (posthog_agent_executor.py)**
- E2B sandbox management
- PostHog driver upload
- Script execution
- Discovery orchestration

**Driver (../posthog_driver/)**
- PostHog API client
- HogQL query execution
- BaseDriver contract implementation

### Data Flow

```
1. User types: "Show me top events"
2. WebSocket sends message to backend
3. Backend calls Claude API with tools
4. Claude decides to use discover_objects tool
5. Backend calls executor.run_discovery()
6. Executor runs script in E2B sandbox
7. Script uses PostHogDriver to query API
8. Results returned to Claude
9. Claude analyzes and generates response
10. Response streamed to frontend
11. User sees: "I found 10 popular events..."
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

**Error: "POSTHOG_API_KEY is required"**
- Solution: Set `POSTHOG_API_KEY` and `POSTHOG_PROJECT_ID` in `.env`
- Get key from: https://posthog.com/project/settings/project-api-keys

**Error: "Failed to initialize agent"**
- Check that all API keys are valid
- Verify internet connection
- Check E2B service status: https://status.e2b.dev/

### Query Issues

**Error: "Unknown resource"**
- Solution: Ask "What data do you have?" to discover available resources
- The agent will show you what's available in your PostHog project

**Error: "Query syntax error"**
- The agent should handle HogQL syntax automatically
- If errors persist, try asking to "show me the code" and check the query
- HogQL docs: https://posthog.com/docs/hogql

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
posthog_ui/
├── app.py                          # FastAPI backend with Claude integration
├── posthog_agent_executor.py      # E2B sandbox management
├── static/
│   └── index.html                  # Frontend UI
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (create this)
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

## License

This project is part of the ng_component proof-of-concept and follows the same license.

## Support

For issues and questions:
- PostHog docs: https://posthog.com/docs
- HogQL reference: https://posthog.com/docs/hogql
- E2B docs: https://e2b.dev/docs
- Claude docs: https://docs.anthropic.com/

## Next Steps

1. Try example queries in the UI
2. Explore your PostHog data with natural language
3. View generated HogQL queries ("show me the code")
4. Experiment with different time ranges and filters
5. Monitor costs and optimize with prompt caching
