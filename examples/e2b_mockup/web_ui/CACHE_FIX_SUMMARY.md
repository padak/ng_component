# Cache Token Display Fix Summary

**Date:** 2025-11-11
**Issue:** Cache tokens showing 0 in Web UI despite caching being enabled

## Root Causes

### 1. Incompatible Model Name
**Problem:** User's `.env` had `CLAUDE_MODEL=claude-haiku-4-5` but `pricing.py` only recognized `claude-haiku-4-20250514`

**Impact:** Model name mismatch caused pricing calculation to fall back to default, but didn't affect token extraction

**Fix:** Added model name aliases to `pricing.py`:
- `claude-sonnet-4-5` (alias for `claude-sonnet-4-5-20250929`)
- `claude-sonnet-4` (alias for `claude-sonnet-4-20250514`)
- `claude-haiku-4-5` (alias for `claude-haiku-4-20250514`)

### 2. New Anthropic SDK Response Format (PRIMARY CAUSE)
**Problem:** Anthropic Python SDK version 0.39+ changed the cache metrics structure from flat to nested:

**Old SDK (0.38 and earlier):**
```python
usage = {
    "input_tokens": 1000,
    "cache_creation_input_tokens": 2000,  # Flat field
    "cache_read_input_tokens": 500,
    "output_tokens": 300
}
```

**New SDK (0.39+):**
```python
usage = {
    "input_tokens": 1000,
    "cache_creation": {  # Nested object
        "ephemeral_5m_input_tokens": 1200,  # 5-minute cache
        "ephemeral_1h_input_tokens": 800    # 1-hour cache
    },
    "cache_read_input_tokens": 500,
    "output_tokens": 300
}
```

**Impact:** The old extraction code only checked `usage.cache_creation_input_tokens` (flat field), which doesn't exist in the new SDK format.

**Evidence from user logs:**
```
cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0)
```

This confirms the new nested structure was present but not being extracted.

## Fixes Applied

### 1. Updated `app.py` (lines 613-655)

**Before:**
```python
cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
```

**After:**
```python
cache_creation = 0
cache_read = 0

# Try new SDK format first (nested cache_creation object)
if hasattr(usage, 'cache_creation') and usage.cache_creation:
    cache_obj = usage.cache_creation

    # Extract both TTL types
    ephemeral_5m = getattr(cache_obj, 'ephemeral_5m_input_tokens', 0) or 0
    ephemeral_1h = getattr(cache_obj, 'ephemeral_1h_input_tokens', 0) or 0

    # Total is sum of both
    cache_creation = ephemeral_5m + ephemeral_1h

# Fall back to old SDK format
if cache_creation == 0:
    cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0

# Cache read (same in both formats)
cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
```

**Features:**
- ✓ Supports new nested format (SDK 0.39+)
- ✓ Backward compatible with old flat format (SDK 0.38-)
- ✓ Handles both 5-minute and 1-hour cache TTLs
- ✓ Enhanced debug logging to show breakdown

### 2. Updated `pricing.py` (lines 32-78)

Added model name aliases for user convenience:
- Short names: `claude-sonnet-4-5`, `claude-sonnet-4`, `claude-haiku-4-5`
- Full names: `claude-sonnet-4-5-20250929`, `claude-sonnet-4-20250514`, `claude-haiku-4-20250514`

### 3. Updated `.env.example` (lines 9-21)

Clarified model naming conventions:
```bash
# Options (short names for convenience):
#   claude-sonnet-4-5 (best for complex tasks, coding, computer use)
#   claude-sonnet-4 (balanced performance)
#   claude-haiku-4-5 (fastest, cheapest - 60x cheaper than Sonnet 4.5!)
#
# Full model names with dates (also supported):
#   claude-sonnet-4-5-20250929
#   claude-sonnet-4-20250514
#   claude-haiku-4-20250514
```

## Testing

### Unit Tests
Created `test_cache_extraction.py` to verify:
- ✓ Old SDK format (flat structure)
- ✓ New SDK format with 5-minute cache only
- ✓ New SDK format with 1-hour cache only
- ✓ New SDK format with mixed 5m + 1h caches

All tests pass successfully.

### Integration Test
Run the pricing calculator:
```bash
cd examples/e2b_mockup/web_ui
python3 pricing.py
```

Expected output shows correct calculations for all model types.

## Verification Steps

1. **Update your .env:**
   ```bash
   # Either use short name:
   CLAUDE_MODEL=claude-haiku-4-5

   # Or full name:
   CLAUDE_MODEL=claude-haiku-4-20250514

   # Both work now!
   ENABLE_PROMPT_CACHING=true
   ```

2. **Restart Web UI:**
   ```bash
   cd examples/e2b_mockup/web_ui
   uvicorn app:app --reload --port 8080
   ```

3. **Test caching:**
   - First query: Should show cache creation tokens > 0
   - Second query (within 5 min): Should show cache read tokens > 0

4. **Check logs:**
   ```
   INFO - cache_creation object: CacheCreation(ephemeral_5m_input_tokens=2000, ...)
   INFO - ephemeral_5m_input_tokens: 2000 (5-minute cache)
   INFO - TOTAL cache_creation: 2000 (CACHE CREATED)
   ```

5. **Verify UI:**
   - Cache Created: 2000 (or appropriate value)
   - Cache Read: 0 (first query) or 2000+ (subsequent queries)

## Expected Behavior After Fix

### First Query (Cache Creation)
```
Input: 1000 tokens
Cache Created: 2000 tokens  ← Should be > 0 now!
Cache Read: 0 tokens
Output: 300 tokens
```

### Second Query (Cache Hit)
```
Input: 200 tokens (only new content)
Cache Created: 0 tokens
Cache Read: 2000 tokens  ← Reusing cached system prompt!
Output: 250 tokens
```

## Cost Impact

With caching working correctly:
- **First query:** ~$0.02 (cache write: $3.75/MTok for 5m cache)
- **Second query:** ~$0.001 (cache read: $0.30/MTok - 90% cheaper!)

For Haiku 4.5:
- **First query:** ~$0.007 (cache write: $1.25/MTok)
- **Second query:** ~$0.0003 (cache read: $0.10/MTok - 90% cheaper!)

## Related Documentation

- Anthropic SDK Issue: https://github.com/anthropics/anthropic-sdk-typescript/issues/793
- Anthropic Prompt Caching Docs: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

## Files Modified

1. `/Users/padak/github/ng_component/examples/e2b_mockup/web_ui/app.py` (lines 613-655)
2. `/Users/padak/github/ng_component/examples/e2b_mockup/web_ui/pricing.py` (lines 32-78, 1-32)
3. `/Users/padak/github/ng_component/examples/e2b_mockup/.env.example` (lines 9-21)

## Files Created

1. `/Users/padak/github/ng_component/examples/e2b_mockup/web_ui/test_cache_extraction.py` (test suite)
2. `/Users/padak/github/ng_component/examples/e2b_mockup/web_ui/CACHE_FIX_SUMMARY.md` (this document)
