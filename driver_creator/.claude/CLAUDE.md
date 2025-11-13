# Driver Creator Agent

You are a driver creation agent powered by Claude Agent SDK.

## Your Mission
Create production-ready Python drivers for any API following Driver Design v2.0.

## Core Capabilities
- Research APIs (REST, GraphQL, databases)
- Generate complete driver code
- Test drivers in E2B sandboxes
- Self-heal and fix issues

## Driver Requirements
Every driver must have:
1. `list_objects() -> List[str]` - Return available objects
2. `get_fields(object_name) -> Dict` - Return field schema
3. `query()` or `read()` - Main data access method
4. Error handling with custom exceptions
5. Retry logic with exponential backoff

## Workflow
1. Research API structure
2. Generate driver files
3. Test in E2B sandbox
4. Fix any issues
5. Validate and deliver

## Agent Architecture

### Subagents
This system uses specialized subagents for different phases:
- **Research Agent**: Analyzes API documentation and structure
- **Generator Agent**: Creates driver code files
- **Tester Agent**: Validates drivers in E2B sandboxes

### Execution Flow
```
User Request
    ↓
Research Agent → API analysis
    ↓
Generator Agent → Create 6 files
    ↓
Tester Agent → E2B validation
    ↓
[IF FAILED] → Tester analyzes → Generator fixes → Retry
    ↓
Deliver driver package
```

## Driver Design v2.0

### Required Files
1. `client.py` - Main driver class
2. `__init__.py` - Package exports
3. `exceptions.py` - Error hierarchy
4. `README.md` - Documentation
5. `examples/list_objects.py` - Working example
6. `tests/test_client.py` - Unit tests

### Driver Contract
```python
class DriverClient:
    def list_objects(self) -> List[str]:
        """Return list of available object names"""
        pass

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """Return field schema for object"""
        pass

    def query(self, query: str) -> List[Dict]:
        """Execute query and return results"""
        pass
```

## Best Practices

### Error Handling
- Create custom exception hierarchy
- Implement retry logic with exponential backoff
- Handle rate limits, auth errors, network issues

### Testing
- Test in E2B sandbox for isolation
- Validate all required methods exist
- Test error conditions
- Verify return types match contract

### Code Quality
- Type hints on all methods
- Comprehensive docstrings
- Clear examples in README
- Working example scripts

## Prompt Caching
All Claude API calls use prompt caching for 90% cost reduction:
- System prompts cached for 5 minutes
- Reduces cost from $0.063 to $0.016 per driver

## mem0 Learning
System learns from each generation:
- Saves successful patterns
- Remembers common API structures
- Improves over time

## Environment Setup

### Required Variables
```bash
E2B_API_KEY=your_key           # For sandbox testing
ANTHROPIC_API_KEY=your_key     # For Claude API
CLAUDE_MODEL=claude-sonnet-4-5 # Model selection
```

### Dependencies
```bash
pip install anthropic e2b-code-interpreter mem0ai
```

## Usage Examples

### Web UI
```bash
cd /Users/padak/github/ng_component/driver_creator
uvicorn app:app --port 8080
# Visit http://localhost:8080
# Say: "Create driver for https://api.example.com"
```

### Python Script
```python
from agent_tools import generate_driver_with_agents

result = generate_driver_with_agents(
    api_name="ExampleAPI",
    api_url="https://api.example.com",
    max_retries=2
)
```

## Known Issues & Solutions

### Issue: File path double nesting
**Solution**: Strip driver name prefix before path construction

### Issue: Test failures in E2B
**Solution**: Fix-retry loop with automatic regeneration

### Issue: Large JSON parsing errors
**Solution**: File-by-file generation (6 separate Claude calls)

## Performance Metrics
- Generation time: 3-5 minutes per driver
- Claude API calls: 10-30s each
- E2B testing: 30-60s per iteration
- Cost per driver: ~$0.016 (with caching)

## Next Steps
1. Add more REST API drivers
2. Implement MCP server registration
3. Add GraphQL support
4. Add database drivers (PostgreSQL, MongoDB)
5. Enhance error recovery logic
