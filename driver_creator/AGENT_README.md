# Agent.py - Driver Creator Agent

**Simple, powerful interface for AI-driven driver generation using Anthropic SDK**

## Overview

`agent.py` provides a clean API for creating production-ready API drivers using Claude AI. It wraps the existing 3-layer self-healing agent architecture with a simple interface for both CLI and programmatic usage.

## Key Features

✅ **3-Layer Self-Healing Architecture**
- Layer 3: Supervisor Agent (handles failures and retries)
- Layer 2: Diagnostic Agent (analyzes errors)
- Layer 1: Defensive Wrappers (validation and recovery)

✅ **Multi-Agent System**
- Research Agent: Analyzes API documentation
- Generator Agent: Creates complete driver code
- Tester Agent: Validates in E2B sandboxes
- Learning Agent: Saves patterns to mem0

✅ **Automatic Testing & Fixing**
- E2B sandbox integration for isolated testing
- Automatic error detection and correction
- Fix-retry loop with adaptive strategies

✅ **Cost Optimization**
- Prompt caching for 90% cost reduction
- Multi-model strategy (Haiku for fast tasks, Sonnet for quality)

## Installation

```bash
# Install dependencies
pip install anthropic e2b-code-interpreter mem0ai python-dotenv

# Set environment variables
export ANTHROPIC_API_KEY=your_anthropic_api_key
export E2B_API_KEY=your_e2b_api_key  # Optional, for testing
export CLAUDE_MODEL=claude-sonnet-4-5  # Optional
```

## Usage

### 1. Command Line Interface

```bash
# Basic usage
python agent.py --api-url https://api.open-meteo.com/v1 --name OpenMeteo

# With custom output directory
python agent.py --api-url https://api.example.com --name Example --output ./my_drivers/example

# Without self-healing (faster but less reliable)
python agent.py --api-url https://api.example.com --name Example --no-supervisor

# With custom model
python agent.py --api-url https://api.example.com --name Example --model claude-haiku-4-5

# Show help
python agent.py --help
```

### 2. Python API (Synchronous)

```python
from agent import DriverCreatorAgent

# Initialize agent
agent = DriverCreatorAgent()

# Create driver (blocks until complete)
result = agent.create_driver_sync(
    api_url="https://api.open-meteo.com/v1",
    api_name="OpenMeteo"
)

if result["success"]:
    print(f"✓ Driver created: {result['output_path']}")
    print(f"  Files: {len(result['files_created'])}")
else:
    print(f"✗ Failed: {result['error']}")
```

### 3. Python API (Async)

```python
import asyncio
from agent import DriverCreatorAgent

async def create_driver():
    # Initialize agent
    agent = DriverCreatorAgent()

    # Create driver asynchronously
    result = await agent.create_driver(
        api_url="https://api.open-meteo.com/v1",
        api_name="OpenMeteo",
        max_retries=5
    )

    # Validate driver
    if result["success"]:
        validation = await agent.validate_driver(result['output_path'])
        print(f"Validation: {len(validation['checks_passed'])} checks passed")

asyncio.run(create_driver())
```

### 4. Custom Configuration

```python
from agent import DriverCreatorAgent

# Initialize with custom settings
agent = DriverCreatorAgent(
    model="claude-haiku-4-5",  # Use cheaper/faster model
    enable_prompt_caching=True
)

# Create driver with custom settings
result = agent.create_driver_sync(
    api_url="https://api.example.com",
    api_name="ExampleAPI",
    output_dir="./custom_output",
    max_retries=3,
    use_supervisor=False  # Disable self-healing
)
```

### 5. WebSocket Integration (FastAPI)

```python
from fastapi import FastAPI, WebSocket
from agent import DriverCreatorAgent

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    agent = DriverCreatorAgent()

    # Receive request
    data = await websocket.receive_json()

    # Send status
    await websocket.send_json({
        "type": "status",
        "message": "Creating driver..."
    })

    # Create driver
    result = await agent.create_driver(
        data["api_url"],
        data["api_name"]
    )

    # Send result
    await websocket.send_json({
        "type": "result",
        "success": result["success"],
        "data": result
    })
```

## API Reference

### Class: `DriverCreatorAgent`

Main interface for driver creation.

#### `__init__(api_key=None, model=None, enable_prompt_caching=True)`

Initialize the agent.

**Args:**
- `api_key` (str, optional): Anthropic API key (defaults to `ANTHROPIC_API_KEY` env var)
- `model` (str, optional): Claude model to use (defaults to `claude-sonnet-4-5`)
- `enable_prompt_caching` (bool): Enable prompt caching for cost savings (default: True)

**Raises:**
- `ValueError`: If `ANTHROPIC_API_KEY` not found

#### `async create_driver(api_url, api_name, output_dir=None, max_retries=7, use_supervisor=True)`

Create a complete driver for the given API.

**Args:**
- `api_url` (str): Base URL of the API (e.g., "https://api.example.com/v1")
- `api_name` (str): Name of the API (e.g., "ExampleAPI")
- `output_dir` (str, optional): Output directory (defaults to `generated_drivers/<name>`)
- `max_retries` (int): Maximum fix-retry iterations (default: 7)
- `use_supervisor` (bool): Use 3-layer self-healing (default: True)

**Returns:**
```python
{
    "success": bool,
    "driver_name": str,
    "output_path": str,
    "files_created": List[str],
    "test_results": Dict,
    "iterations": int,
    "execution_time": float,
    "supervisor_attempts": int,  # If use_supervisor=True
    "diagnostics_run": int       # If use_supervisor=True
}
```

**Raises:**
- `ValueError`: If `api_url` or `api_name` is invalid
- `RuntimeError`: If generation fails after all retries

#### `create_driver_sync(api_url, api_name, output_dir=None, max_retries=7, use_supervisor=True)`

Synchronous version of `create_driver()`. Same API, blocks until completion.

#### `async validate_driver(driver_path)`

Validate a generated driver against Driver Design v2.0 specification.

**Args:**
- `driver_path` (str): Path to the driver directory

**Returns:**
```python
{
    "valid": bool,
    "checks_passed": List[str],
    "checks_failed": List[str],
    "warnings": List[str],
    "todos_count": int
}
```

#### `async test_driver(driver_path, driver_name, test_api_url=None, use_mock_api=False)`

Test a generated driver in an E2B sandbox.

**Args:**
- `driver_path` (str): Path to the driver directory
- `driver_name` (str): Name of the driver package
- `test_api_url` (str, optional): API URL for testing (defaults to localhost:8000)
- `use_mock_api` (bool): Whether to start a mock API in the sandbox

**Returns:**
```python
{
    "success": bool,
    "tests_passed": int,
    "tests_failed": int,
    "errors": List[Dict],
    "output": str
}
```

#### `get_session_logs()`

Get logs from the current session.

**Returns:**
- `str`: Session log content

## Architecture

### Multi-Agent System

```
User Request
    ↓
┌─────────────────────────────────────────────────┐
│ Layer 3: Supervisor Agent                      │
│ - Orchestrates entire process                  │
│ - Monitors for failures                        │
│ - Launches diagnostic agent on errors          │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Layer 2: Diagnostic Agent                      │
│ - Analyzes generation failures                 │
│ - Identifies root causes                       │
│ - Suggests fix strategies                      │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Layer 1: Defensive Wrappers                    │
│ - Validation on every file generation          │
│ - Automatic retry on syntax errors             │
│ - JSON parsing error recovery                  │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Core Agents                                     │
│ - Research Agent → API analysis                │
│ - Generator Agent → Code generation            │
│ - Tester Agent → E2B testing                   │
│ - Learning Agent → mem0 storage                │
└─────────────────────────────────────────────────┘
```

### Execution Flow

1. **Research Phase**
   - Analyze API documentation
   - Identify endpoints, auth, rate limits
   - Retrieve relevant memories from past generations

2. **Generation Phase**
   - Generate 6 files separately (client.py, __init__.py, exceptions.py, README.md, examples/, tests/)
   - Validate each file (syntax, required methods, no TODOs)
   - Retry on validation errors

3. **Testing Phase**
   - Upload driver to E2B sandbox
   - Run comprehensive test suite
   - Collect errors and failures

4. **Fix Phase** (if tests fail)
   - Tester Agent analyzes errors
   - Suggests specific code edits
   - Apply edits and retry tests
   - Max 7 iterations

5. **Learning Phase**
   - Extract patterns from generation
   - Save learnings to mem0
   - Improve future generations

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional
E2B_API_KEY=your_e2b_api_key              # For sandbox testing
CLAUDE_MODEL=claude-sonnet-4-5             # Model selection
ENABLE_PROMPT_CACHING=true                 # Cost optimization

# Advanced (for self-healing)
MAX_SUPERVISOR_ATTEMPTS=3                  # Layer 3 retries
MAX_FIX_RETRY_ITERATIONS=7                 # Fix-retry iterations
MAX_FILE_GENERATION_RETRIES=3              # Layer 1 retries
```

### Model Options

- `claude-sonnet-4-5` (default) - Best quality, supports caching
- `claude-sonnet-4` - Good balance, supports caching
- `claude-haiku-4-5` - Fastest/cheapest (60x cheaper!), supports caching
- `claude-haiku-3-5` - Fast and cheap, supports caching

## Performance

- **Generation time:** 3-5 minutes per driver
- **Cost per driver:** ~$0.016 (with caching, down from $0.063)
- **Success rate:** >90% on first attempt with self-healing
- **Claude API calls:** 10-30s each
- **E2B testing:** 30-60s per iteration

## Troubleshooting

### Error: "ANTHROPIC_API_KEY not found"

**Solution:** Set the environment variable:
```bash
export ANTHROPIC_API_KEY=your_key
```

### Warning: "E2B_API_KEY not set"

**Effect:** Driver testing will be skipped. Generation will still work.

**Solution:** Set E2B API key if you want testing:
```bash
export E2B_API_KEY=your_key
```

### Warning: "mem0 not available"

**Effect:** Learning phase will be skipped. Generation will still work.

**Solution:** Install mem0ai:
```bash
pip install mem0ai
```

### Error: "Generation failed after all retries"

**Possible causes:**
1. API is unreachable
2. API requires authentication (provide real API key)
3. Complex API structure

**Solution:** Try with `--no-supervisor` for debugging or check session logs.

## Examples

See `example_agent_usage.py` for more examples:
- Simple synchronous usage
- Async usage with progress monitoring
- WebSocket integration
- Batch processing
- Custom configuration

## Testing

Run the test suite:
```bash
python test_agent_api.py
```

## Comparison with Old System

| Aspect | Old System | New (agent.py) |
|--------|-----------|---------------|
| Interface | Multiple scattered functions | Single clean API |
| Usage | Complex setup | Simple import |
| CLI | No CLI | Full CLI with --help |
| Async Support | Limited | Full async/await |
| Documentation | Scattered | Comprehensive |
| Testing | Manual | Test suite included |
| Examples | Few | Multiple examples |

## Related Files

- `agent_tools.py` - Core multi-agent implementation (Layer 1-3)
- `tools.py` - Validation, testing, and research functions
- `app.py` - FastAPI web UI integration
- `.claude/CLAUDE.md` - Project instructions for Claude

## License

Same as parent project.

## Support

For issues or questions:
1. Check session logs: `agent.get_session_logs()`
2. Review `logs/session_*/` directory
3. Enable debug logging in `.env`
