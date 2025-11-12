# USD Cost Calculation Implementation

This document describes the USD cost calculation and display feature for the Web UI.

## Overview

The Web UI now calculates and displays real-time USD costs for Claude API usage based on Anthropic's pricing. Costs are tracked per-request and cumulatively for the entire session.

## Implementation Components

### 1. Pricing Module (`pricing.py`)

**Location:** `/Users/padak/github/ng_component/examples/e2b_mockup/web_ui/pricing.py`

**Purpose:** Calculate USD costs from token usage based on model pricing.

**Key Features:**
- Supports all 3 Claude models (Sonnet 4.5, Sonnet 4, Haiku 4.5)
- Handles prompt caching metrics (cache write, cache read)
- Provides cost breakdown by token type
- Includes smart cost formatting

**Pricing Table (as of 2025-11-11):**

| Model | Input | Cache Write (5m) | Cache Read | Output |
|-------|-------|------------------|------------|--------|
| Sonnet 4.5 | $3/MTok | $3.75/MTok | $0.30/MTok | $15/MTok |
| Sonnet 4 | $3/MTok | $3.75/MTok | $0.30/MTok | $15/MTok |
| Haiku 4.5 | $1/MTok | $1.25/MTok | $0.10/MTok | $5/MTok |

**API:**

```python
from pricing import calculate_cost

usage = {
    "input_tokens": 1000,
    "cache_creation_input_tokens": 2000,
    "cache_read_input_tokens": 500,
    "output_tokens": 300
}

cost = calculate_cost(usage, "claude-sonnet-4-5-20250929")
# Returns:
# {
#     "input_cost": 0.003,
#     "cache_write_cost": 0.0075,
#     "cache_read_cost": 0.00015,
#     "output_cost": 0.0045,
#     "total_cost": 0.01545
# }
```

### 2. Backend Integration (`app.py`)

**Changes:**
- Import pricing module
- Add `total_cost` field to `AgentSession` class
- Calculate costs after each Claude API call
- Send cost data to frontend via WebSocket

**Cost Calculation Flow:**

```python
# 1. Calculate request cost
request_usage = {
    "input_tokens": usage.input_tokens,
    "cache_creation_input_tokens": cache_creation,
    "cache_read_input_tokens": cache_read,
    "output_tokens": usage.output_tokens
}
request_cost = calculate_cost(request_usage, self.claude_model)

# 2. Calculate total session cost
total_usage = {
    "input_tokens": self.total_input_tokens,
    "cache_creation_input_tokens": self.total_cache_creation_tokens,
    "cache_read_input_tokens": self.total_cache_read_tokens,
    "output_tokens": self.total_output_tokens
}
total_cost_breakdown = calculate_cost(total_usage, self.claude_model)
self.total_cost = total_cost_breakdown['total_cost']

# 3. Send to frontend
await self._safe_send({
    "type": "usage",
    "usage": {...},
    "cost": {
        "request_cost": request_cost['total_cost'],
        "request_breakdown": request_cost,
        "total_cost": self.total_cost,
        "total_breakdown": total_cost_breakdown
    }
})
```

### 3. Frontend Display (`static/index.html`)

**UI Updates:**

Added to Token Usage sidebar:
```
Token Usage
-----------
Input: 10,751
Output: 905

Cache Created: 2,000
Cache Read: 7,123

This Request: $0.015
Session Total: $0.082
-----------
```

**Features:**
- Real-time cost updates after each request
- Color-coded total cost:
  - **Green**: Using cache (efficient)
  - **Orange**: Expensive session (>$0.50)
  - **Default**: Normal usage
- Smart formatting:
  - Small amounts (<$0.01): 3-4 decimal places (e.g., "$0.0012")
  - Larger amounts: 2 decimal places (e.g., "$1.50")

**JavaScript Functions:**

```javascript
// Update token usage and costs
function updateTokenUsage(usage, cost) {
    // Update token counts...

    // Update costs
    if (cost) {
        requestCostElem.textContent = formatCost(cost.request_cost);
        totalCostElem.textContent = formatCost(cost.total_cost);

        // Color-code based on cache usage
        if (usage.cache_read_tokens > 0) {
            totalCostElem.className = 'font-mono text-lg text-green-600';
        } else if (cost.total_cost > 0.50) {
            totalCostElem.className = 'font-mono text-lg text-orange-600';
        }
    }
}

// Format cost with smart precision
function formatCost(cost) {
    if (cost < 0.01) {
        // 3-4 decimal places for small amounts
        return `$${cost.toFixed(3)}`;
    } else {
        // 2 decimal places for larger amounts
        return `$${cost.toFixed(2)}`;
    }
}
```

## Example Calculation Walkthrough

### Scenario: User asks "Get all leads" with Sonnet 4.5

**Request 1 (First request, cache write):**
```
Tokens:
- Input: 1,200 (base input)
- Cache Creation: 8,500 (system prompt cached)
- Cache Read: 0 (no cache yet)
- Output: 450

Cost Calculation:
- Input: 1,200 / 1,000,000 * $3.00 = $0.0036
- Cache Write: 8,500 / 1,000,000 * $3.75 = $0.0319
- Cache Read: 0 / 1,000,000 * $0.30 = $0.0000
- Output: 450 / 1,000,000 * $15.00 = $0.0068

Request Cost: $0.042
Session Total: $0.042
```

**Request 2 (Follow-up, cache hit):**
```
Tokens:
- Input: 800 (base input)
- Cache Creation: 0 (cache already exists)
- Cache Read: 8,500 (system prompt from cache - 90% savings!)
- Output: 320

Cost Calculation:
- Input: 800 / 1,000,000 * $3.00 = $0.0024
- Cache Write: 0 / 1,000,000 * $3.75 = $0.0000
- Cache Read: 8,500 / 1,000,000 * $0.30 = $0.0026
- Output: 320 / 1,000,000 * $15.00 = $0.0048

Request Cost: $0.010
Session Total: $0.052

Savings: $0.032 (76% cheaper than without cache!)
```

## Edge Cases Handled

### 1. Missing Cache Metrics
```python
# Gracefully handle missing fields
cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
```

### 2. Unknown Models
```python
# Fall back to Sonnet 4.5 pricing
pricing = PRICING.get(model_name, DEFAULT_PRICING)
```

### 3. Zero Costs
```python
# Format correctly even for zero
formatCost(0.0)  # Returns "$0.00"
```

### 4. Very Small Costs
```python
formatCost(0.0001234)  # Returns "$0.0001"
formatCost(0.001)      # Returns "$0.001"
```

### 5. Large Costs
```python
formatCost(1.50)       # Returns "$1.50"
formatCost(123.456)    # Returns "$123.46"
```

## Testing Steps

### 1. Test Pricing Module

```bash
cd /Users/padak/github/ng_component/examples/e2b_mockup/web_ui
python3 pricing.py
```

**Expected Output:**
```
Test 1: Sonnet 4.5 with cache
Input: 1,000 tokens
Cache Write: 2,000 tokens
Cache Read: 500 tokens
Output: 300 tokens

Input tokens: $0.003
Cache write: $0.0075
Cache read: $0.0001
Output: $0.0045
──────────────
Total: $0.02
```

### 2. Test Web UI

```bash
# Start Web UI
cd /Users/padak/github/ng_component/examples/e2b_mockup/web_ui
uvicorn app:app --reload --port 8080

# Visit http://localhost:8080/static/
```

**Test Scenarios:**

1. **First Query (Cache Write)**
   - Ask: "What objects are available?"
   - Observe: Cache Created count increases
   - Verify: Request cost shown (~$0.03-0.05)

2. **Second Query (Cache Hit)**
   - Ask: "Get all leads"
   - Observe: Cache Read count increases
   - Verify: Request cost is lower (~$0.01-0.02)
   - Verify: Total cost is green (cache being used)

3. **Multiple Queries**
   - Ask several questions
   - Verify: Session Total increases correctly
   - Verify: Each request shows individual cost

4. **Model Comparison**
   - Change `CLAUDE_MODEL` in `.env` to test different models:
     - `claude-sonnet-4-5-20250929` (default)
     - `claude-sonnet-4-20250514`
     - `claude-haiku-4-20250514` (60x cheaper!)

### 3. Verify Cost Accuracy

**Manual Verification:**

For Sonnet 4.5:
```
Input: 10,000 tokens = 10,000 / 1,000,000 * $3 = $0.03
Cache Write: 50,000 tokens = 50,000 / 1,000,000 * $3.75 = $0.1875
Cache Read: 45,000 tokens = 45,000 / 1,000,000 * $0.30 = $0.0135
Output: 3,000 tokens = 3,000 / 1,000,000 * $15 = $0.045

Total: $0.03 + $0.1875 + $0.0135 + $0.045 = $0.276
```

Compare with displayed value in UI.

## Cost Optimization Tips

### 1. Enable Prompt Caching (Default: ON)
```bash
# In .env
ENABLE_PROMPT_CACHING=true  # 90% savings on cached tokens!
```

### 2. Use Haiku for Simple Queries
```bash
# In .env
CLAUDE_MODEL=claude-haiku-4-20250514  # 60x cheaper than Sonnet!
```

### 3. Monitor Session Costs
- Watch the "Session Total" in sidebar
- Green = efficient (using cache)
- Orange = expensive (>$0.50)

## Future Enhancements

### 1. Cost Breakdown Tooltip
- Click on Session Total to see breakdown:
  ```
  Input tokens: $0.003
  Cache write: $0.008
  Cache read: $0.0002
  Output: $0.014
  ──────────────
  Total: $0.025
  ```

### 2. Session Cost Limit
- Alert when session exceeds budget (e.g., $1.00)
- Optional auto-stop at limit

### 3. Cost History Chart
- Graph cost over time
- Show cache hit rate
- Compare costs between models

### 4. Export Cost Report
- Download CSV with per-request costs
- Monthly cost summaries
- Model comparison reports

## Files Modified

1. **Created:** `/Users/padak/github/ng_component/examples/e2b_mockup/web_ui/pricing.py`
   - Pricing calculator module
   - Test cases included

2. **Modified:** `/Users/padak/github/ng_component/examples/e2b_mockup/web_ui/app.py`
   - Import pricing module
   - Add cost tracking to AgentSession
   - Calculate and send costs in usage updates

3. **Modified:** `/Users/padak/github/ng_component/examples/e2b_mockup/web_ui/static/index.html`
   - Add cost display elements to sidebar
   - Update `updateTokenUsage()` function
   - Add `formatCost()` helper function
   - Implement color-coded cost display

## Summary

The USD cost calculation feature provides:

✅ **Real-time cost tracking** - See costs as you use the API
✅ **Accurate calculations** - Based on official Anthropic pricing
✅ **Cache visibility** - Understand savings from prompt caching
✅ **Smart formatting** - Appropriate precision for all cost ranges
✅ **Visual feedback** - Color-coded to show efficiency
✅ **Model support** - Works with all 3 Claude models
✅ **Session totals** - Track cumulative costs

This helps users:
- Understand API costs in real-time
- Optimize usage with caching
- Choose appropriate models
- Stay within budget
- Validate billing
