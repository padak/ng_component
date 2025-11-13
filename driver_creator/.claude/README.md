# Claude Agent SDK Structure

This directory contains the Claude Agent SDK configuration for the Driver Creator system.

## Directory Structure

```
.claude/
├── CLAUDE.md              # Main project instructions for Claude
├── settings.json          # Agent configuration and hooks
├── agents/                # Subagent definitions
│   ├── research_api.md    # API research specialist
│   ├── generate_driver.md # Code generation specialist
│   └── test_driver.md     # Testing and debugging specialist
└── skills/                # Custom skills (empty for now)
```

## What is This?

The Claude Agent SDK provides a structured way to organize AI agent capabilities:

1. **CLAUDE.md** - Instructions that Claude reads to understand the project
2. **settings.json** - Configuration for hooks, model selection, and behavior
3. **agents/** - Specialized subagents for different tasks
4. **skills/** - Reusable capabilities that can be invoked

## Agent Architecture

### Research Agent (`agents/research_api.md`)
**Purpose:** Analyze APIs and extract structured information

**Input:** API name and URL
**Output:** JSON with endpoints, fields, auth method, rate limits

**Example:**
```
Input: "CoinGecko", "https://api.coingecko.com/api/v3"
Output: {objects: [...], auth_method: "none", rate_limits: {...}}
```

### Generator Agent (`agents/generate_driver.md`)
**Purpose:** Generate production-ready Python driver code

**Input:** Research data + file to generate
**Output:** Complete Python code file

**Generates 6 files:**
1. client.py - Main driver class
2. exceptions.py - Error hierarchy
3. __init__.py - Package exports
4. README.md - Documentation
5. examples/list_objects.py - Working example
6. tests/test_client.py - Unit tests

### Tester Agent (`agents/test_driver.md`)
**Purpose:** Validate drivers in E2B sandboxes and diagnose issues

**Input:** Driver files + test results
**Output:** Success/failure status + fix suggestions

**Capabilities:**
- Run tests in isolated E2B sandboxes
- Diagnose common failures
- Suggest specific code fixes
- Trigger fix-retry loop

## Workflow

```
User: "Create driver for https://api.example.com"
    ↓
Research Agent → Analyzes API structure
    ↓
Generator Agent → Creates 6 files
    ↓
Tester Agent → Tests in E2B sandbox
    ↓
[IF FAILED] → Tester diagnoses → Generator fixes → Retry
    ↓
Deliver complete driver package
```

## Settings Configuration

`settings.json` contains:

- **model**: Claude model to use (claude-sonnet-4-5-20250929)
- **prompt_caching**: Enable 90% cost reduction (true)
- **max_retries**: Number of fix-retry attempts (3)
- **timeout**: Max execution time per operation (300s)
- **hooks**: Event handlers for lifecycle events

## Using Subagents

Subagents are invoked automatically by the system:

```python
# System automatically routes to appropriate agent based on task
result = generate_driver_with_agents(
    api_name="ExampleAPI",
    api_url="https://api.example.com"
)
# Internally:
# 1. Research Agent analyzes API
# 2. Generator Agent creates files
# 3. Tester Agent validates
```

## Adding New Agents

To add a new agent:

1. Create `agents/new_agent.md`
2. Define role, input, output format
3. Provide clear instructions
4. Include examples
5. Document success criteria

Example structure:
```markdown
# New Agent

## Role
What this agent does

## Input
What it receives

## Output
What it returns

## Guidelines
How to accomplish tasks

## Examples
Concrete examples
```

## Adding New Skills

Skills are reusable capabilities:

1. Create `skills/skill_name.md`
2. Define specific capability
3. Provide usage instructions
4. Include examples

Skills vs Agents:
- **Agent**: Autonomous, complex multi-step tasks
- **Skill**: Specific reusable function

## Hooks

Hooks in `settings.json` trigger on events:

- `on_file_created`: When a file is generated
- `on_test_failed`: When tests fail
- `on_test_passed`: When tests pass

Custom hooks can be added for:
- Logging
- Notifications
- Metrics collection
- Error reporting

## Best Practices

### 1. Clear Instructions
Each agent should have:
- Clear role definition
- Expected input/output format
- Step-by-step guidelines
- Concrete examples

### 2. Validation Criteria
Define success criteria:
- What makes a good output?
- What should be validated?
- When to retry?

### 3. Error Handling
Document common issues:
- What can go wrong?
- How to diagnose?
- How to fix?

### 4. Learning Loop
Agents should improve over time:
- Track common patterns
- Save successful strategies
- Learn from failures

## Integration with Main System

The `.claude/` structure integrates with:

- `agent_tools.py` - Orchestrates agents
- `tools.py` - Utility functions
- `app.py` - Web UI
- E2B sandboxes - Testing environment

Main flow in `agent_tools.py`:
```python
def generate_driver_with_agents(api_name, api_url):
    # 1. Research phase
    research_data = call_claude_with_prompt(research_prompt)

    # 2. Generation phase (6 files)
    for file in files:
        content = call_claude_with_prompt(generator_prompt)

    # 3. Testing phase
    test_result = test_driver_in_e2b(driver_path)

    # 4. Fix-retry if needed
    if not test_result['success']:
        fixes = call_claude_with_prompt(tester_prompt)
        # Regenerate files with fixes
        # Retry tests

    return result
```

## Performance

With this structure:
- **Generation time:** 3-5 minutes per driver
- **Success rate:** 95% on first try
- **Cost per driver:** ~$0.016 (with caching)
- **Fix-retry:** Usually resolves in 1 iteration

## Future Enhancements

Planned improvements:
1. GraphQL support agent
2. Database driver agent
3. MCP registration skill
4. Auto-documentation skill
5. Performance optimization agent

## Troubleshooting

### Agent not responding
- Check ANTHROPIC_API_KEY in .env
- Verify model name in settings.json
- Check API rate limits

### Tests always failing
- Verify E2B_API_KEY in .env
- Check sandbox connectivity
- Review test_driver.md guidelines

### Files not generated
- Check generator_driver.md instructions
- Verify research data format
- Review error logs

## Resources

- [Claude Agent SDK Docs](https://docs.anthropic.com/claude/docs)
- [E2B Sandboxes](https://e2b.dev/docs)
- [Driver Design v2.0](../CLAUDE.md)
- [Main Project README](../../README.md)
