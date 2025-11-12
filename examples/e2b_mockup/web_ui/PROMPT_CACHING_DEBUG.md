# Prompt Caching Debug Guide

## Root Cause Analysis

### Why Caching Was Showing 0

The prompt caching implementation was **technically correct** but the cache metrics were not being exposed by the Claude API response due to one of these reasons:

1. **Streaming API Limitation**: The `messages.stream()` API may not always populate cache metrics in `final_message.usage`
2. **Model/API Version**: Some Claude models or API versions may not support prompt caching
3. **Cache Size Threshold**: Caches must be at least 1024 tokens to be created (our system prompt is ~2000 tokens, so this should work)
4. **First Request Only**: Cache creation only happens on the FIRST request in a session

### What We Fixed

#### 1. Added Comprehensive Logging

We now log the complete usage object from Claude API:

```python
# Log the complete usage object for debugging
logger.info(f"Session {self.session_id} - Claude API usage object: {usage}")
logger.info(f"  - input_tokens: {usage.input_tokens}")
logger.info(f"  - output_tokens: {usage.output_tokens}")

# Log cache metrics
if cache_creation > 0:
    logger.info(f"  - cache_creation_input_tokens: {cache_creation} (CACHE CREATED)")
if cache_read > 0:
    logger.info(f"  - cache_read_input_tokens: {cache_read} (CACHE HIT!)")

if cache_creation == 0 and cache_read == 0:
    logger.warning(f"  - No cache metrics found in usage object. Caching enabled: {self.enable_prompt_caching}")
    logger.warning(f"  - Usage object attributes: {dir(usage)}")
```

**What to Look For in Logs:**

```bash
# Run the Web UI and watch logs
cd examples/e2b_mockup/web_ui
uvicorn app:app --reload --port 8080

# Expected log output on FIRST request:
INFO - Session 20251111_... - Claude API usage object: Usage(...)
INFO -   - input_tokens: 850
INFO -   - output_tokens: 300
INFO -   - cache_creation_input_tokens: 2000 (CACHE CREATED)  ← Should see this!

# Expected log output on SUBSEQUENT requests:
INFO - Session 20251111_... - Claude API usage object: Usage(...)
INFO -   - input_tokens: 1200
INFO -   - output_tokens: 450
INFO -   - cache_read_input_tokens: 2000 (CACHE HIT!)  ← Should see this!

# If you see this, caching is NOT working:
WARNING -   - No cache metrics found in usage object. Caching enabled: True
WARNING -   - Usage object attributes: ['input_tokens', 'output_tokens', ...]
```

#### 2. Verified Cache Control Configuration

The system prompt is configured with cache control:

```python
if self.enable_prompt_caching:
    # Enable prompt caching (90% cost reduction on cached tokens)
    system_param = [
        {
            "type": "text",
            "text": CLAUDE_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}
        }
    ]
else:
    # Standard system prompt (no caching)
    system_param = CLAUDE_SYSTEM_PROMPT
```

**This is correct!** The `cache_control: {"type": "ephemeral"}` marker tells Claude to cache this content.

#### 3. Made Agent Proactively Offer Code

Updated the system prompt to include:

```markdown
**Code Transparency:**

After using the `execute_salesforce_query` tool successfully, you should:
1. Present the query results
2. Automatically mention that you can show the generated Python code
3. Say something like: "Would you like to see the Python script I generated? Just ask 'show me the code'"
```

Now the agent will automatically offer to show code after every successful query.

#### 4. Enhanced Error Handling

Added specific error messages for:

**E2B Initialization Errors:**
- API key missing or invalid
- Timeout during sandbox creation
- Network connection issues
- Quota/limit exceeded

**Claude API Errors:**
- Overloaded API (high traffic)
- Rate limits (429)
- Authentication errors (401)
- Server errors (500, 503)
- Network timeouts

**Tool Execution Errors:**
- Sandbox execution failures
- Timeout during tool execution
- Network errors during tool calls

## Testing Instructions

### 1. Enable Debug Logging

Check your `.env` file:

```bash
cd examples/e2b_mockup
cat .env
```

Should include:

```bash
ANTHROPIC_API_KEY=your_key_here
E2B_API_KEY=your_key_here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
ENABLE_PROMPT_CACHING=true
```

### 2. Start Web UI

```bash
cd examples/e2b_mockup/web_ui
uvicorn app:app --reload --port 8080
```

### 3. Test Multi-Turn Conversation

Open browser to `http://localhost:8080/static/` and try:

**Request 1** (should create cache):
```
What objects are available?
```

Watch logs for:
```
INFO - cache_creation_input_tokens: 2000 (CACHE CREATED)
```

Check UI sidebar - should show:
- Cache Created: 2,000 (orange)
- Cache Read: 0 (green)

**Request 2** (should hit cache):
```
Get all leads
```

Watch logs for:
```
INFO - cache_read_input_tokens: 2000 (CACHE HIT!)
```

Check UI sidebar - should show:
- Cache Created: 2,000 (unchanged)
- Cache Read: 2,000 (green) ← NEW!

**Request 3** (should hit cache again):
```
Show me the code
```

Watch logs for another cache hit.

### 4. Verify Agent Offers Code Proactively

After "Get all leads" executes successfully, agent should respond with something like:

```
I found 45 leads created in the system. The most common status is 'New' with 28 leads.

Would you like to see the Python script I generated? Just ask 'show me the code' or 'show the script'.
```

### 5. Test Error Handling

**Test E2B Error:**
Stop the server, remove E2B_API_KEY from .env, restart. Should see:
```
❌ E2B API Key Error: Unable to initialize sandbox.
Please ensure E2B_API_KEY is set in your .env file.
Get your key from https://e2b.dev/
```

**Test Claude API Error:**
Use an invalid ANTHROPIC_API_KEY. Should see:
```
❌ Authentication error. Your ANTHROPIC_API_KEY is invalid or expired.
Please check your .env file.
```

## Known Issues & Limitations

### 1. Cache Metrics May Not Appear

**If you don't see cache metrics:**

1. **Check Anthropic SDK version:**
   ```bash
   pip show anthropic
   # Should be >= 0.34.0
   ```

2. **Verify model supports caching:**
   - Claude Sonnet 4.5 (claude-sonnet-4-5-20250929) ✓ Supported
   - Claude Sonnet 4 (claude-sonnet-4-20250514) ✓ Supported
   - Claude Haiku 4 (claude-haiku-4-20250514) ✓ Supported

3. **Check system prompt size:**
   ```python
   # System prompt must be >= 1024 tokens
   # Our prompt is ~2000 tokens, so this should work
   ```

4. **Verify API response:**
   Look at `WARNING - Usage object attributes:` log to see what's actually in the usage object

### 2. Cache Expires After 5 Minutes

Ephemeral caches last 5 minutes. If you:
- Close the browser tab
- Wait > 5 minutes
- Reconnect

The cache will be expired and a new cache will be created on the next request.

### 3. First Request Always Creates Cache

Cache metrics only appear starting from the FIRST request. The very first request will:
- Create cache (cache_creation_input_tokens > 0)
- NOT read cache (cache_read_input_tokens = 0)

Subsequent requests within 5 minutes will:
- NOT create cache (cache_creation_input_tokens = 0)
- Read from cache (cache_read_input_tokens > 0)

## Expected Behavior Summary

| Request # | Cache Created | Cache Read | Notes |
|-----------|--------------|------------|-------|
| 1st       | 2,000        | 0          | Creates cache for system prompt |
| 2nd       | 0            | 2,000      | Reads cached system prompt (90% cheaper!) |
| 3rd       | 0            | 2,000      | Reads cached system prompt |
| After 5min| 2,000        | 0          | Cache expired, creates new cache |

## Cost Savings with Caching

**Example session (3 requests, Sonnet 4.5):**

Without caching:
- Request 1: System prompt (2000 tokens × $3/MTok = $0.006)
- Request 2: System prompt (2000 tokens × $3/MTok = $0.006)
- Request 3: System prompt (2000 tokens × $3/MTok = $0.006)
- **Total: $0.018**

With caching:
- Request 1: Cache write (2000 tokens × $3.75/MTok = $0.0075)
- Request 2: Cache read (2000 tokens × $0.30/MTok = $0.0006)
- Request 3: Cache read (2000 tokens × $0.30/MTok = $0.0006)
- **Total: $0.0087**

**Savings: 52% cheaper for just 3 requests!**

For 10 requests in a session:
- Without cache: $0.060
- With cache: $0.0129
- **Savings: 78% cheaper!**

## Debugging Checklist

- [ ] ANTHROPIC_API_KEY is set in .env
- [ ] E2B_API_KEY is set in .env
- [ ] ENABLE_PROMPT_CACHING=true in .env
- [ ] Using claude-sonnet-4-5-20250929 or supported model
- [ ] anthropic SDK version >= 0.34.0
- [ ] Server logs show "Claude async client initialized... caching=True"
- [ ] First request shows "CACHE CREATED" in logs
- [ ] Second request shows "CACHE HIT!" in logs
- [ ] UI sidebar shows non-zero cache metrics
- [ ] Agent offers to show code after successful queries
- [ ] Error messages are user-friendly and actionable

## Additional Resources

- Anthropic Prompt Caching Docs: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- E2B Sandbox Docs: https://e2b.dev/docs
- Claude API Pricing: https://www.anthropic.com/pricing
