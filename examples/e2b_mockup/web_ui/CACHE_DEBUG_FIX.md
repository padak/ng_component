# Cache Token Display Fix - Quick Summary

## Problem
Cache metrics showing 0 in Web UI despite `ENABLE_PROMPT_CACHING=true`

## Root Cause
Anthropic Python SDK v0.39+ changed cache metric structure from **flat** to **nested**:

```python
# Old SDK (0.38-): Flat structure
usage.cache_creation_input_tokens = 2000

# New SDK (0.39+): Nested structure
usage.cache_creation = {
    ephemeral_5m_input_tokens: 2000,  # 5-minute TTL cache
    ephemeral_1h_input_tokens: 0      # 1-hour TTL cache
}
```

The extraction code was only checking the old flat field, which doesn't exist in new SDK responses.

## Solution
Updated `app.py` to handle **both** old and new SDK formats:

```python
# Try new SDK format first (nested)
if hasattr(usage, 'cache_creation') and usage.cache_creation:
    ephemeral_5m = usage.cache_creation.ephemeral_5m_input_tokens or 0
    ephemeral_1h = usage.cache_creation.ephemeral_1h_input_tokens or 0
    cache_creation = ephemeral_5m + ephemeral_1h

# Fall back to old SDK format (flat)
if cache_creation == 0:
    cache_creation = usage.cache_creation_input_tokens or 0
```

## Bonus Fix: Model Name Aliases
Added short model name support to `pricing.py`:

- `claude-haiku-4-5` → Works (your .env setting)
- `claude-haiku-4-20250514` → Works (full name)
- `claude-sonnet-4-5` → Works (short name)
- `claude-sonnet-4-5-20250929` → Works (full name)

## Files Modified
1. `app.py` - Lines 613-655 (cache extraction logic)
2. `pricing.py` - Lines 32-78 (model name aliases)
3. `.env.example` - Lines 9-21 (model name documentation)

## Testing
Run the test suite:
```bash
cd examples/e2b_mockup/web_ui
python3 test_cache_extraction.py
```

All 4 tests pass:
- ✓ Old SDK format (flat)
- ✓ New SDK format (5-minute cache)
- ✓ New SDK format (1-hour cache)
- ✓ New SDK format (mixed 5m + 1h)

## Verification
1. Restart Web UI
2. Send first query → Should show `Cache Created: 2000+`
3. Send second query (within 5 min) → Should show `Cache Read: 2000+`

## Expected Logs
```
INFO - cache_creation object: CacheCreation(ephemeral_5m_input_tokens=2000, ephemeral_1h_input_tokens=0)
INFO - ephemeral_5m_input_tokens: 2000 (5-minute cache)
INFO - TOTAL cache_creation: 2000 (CACHE CREATED)
```

## Cost Savings (Haiku 4.5)
- **Without caching:** ~$0.007/request
- **With caching (cache hit):** ~$0.0007/request (90% cheaper!)
