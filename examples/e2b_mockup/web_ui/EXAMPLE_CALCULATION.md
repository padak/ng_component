# Example Cost Calculation Walkthrough

This document shows a complete example of how costs are calculated for a typical user session.

## Scenario: User Explores Salesforce Data

### Request 1: "What objects are available?"

**User Action:** First query of the session

**Token Usage:**
```json
{
  "input_tokens": 1200,
  "cache_creation_input_tokens": 8500,  // System prompt cached
  "cache_read_input_tokens": 0,         // No cache yet
  "output_tokens": 450
}
```

**Cost Calculation (Sonnet 4.5):**

| Token Type | Tokens | Price/MTok | Calculation | Cost |
|------------|--------|------------|-------------|------|
| Input | 1,200 | $3.00 | 1,200 / 1,000,000 × $3.00 | $0.0036 |
| Cache Write | 8,500 | $3.75 | 8,500 / 1,000,000 × $3.75 | $0.0319 |
| Cache Read | 0 | $0.30 | 0 / 1,000,000 × $0.30 | $0.0000 |
| Output | 450 | $15.00 | 450 / 1,000,000 × $15.00 | $0.0068 |
| **TOTAL** | | | | **$0.0423** |

**UI Display:**
```
This Request: $0.042
Session Total: $0.042
```

---

### Request 2: "Get all leads"

**User Action:** Follow-up query in same session

**Token Usage:**
```json
{
  "input_tokens": 800,
  "cache_creation_input_tokens": 0,     // Cache already exists
  "cache_read_input_tokens": 8500,      // System prompt from cache!
  "output_tokens": 320
}
```

**Cost Calculation (Sonnet 4.5):**

| Token Type | Tokens | Price/MTok | Calculation | Cost |
|------------|--------|------------|-------------|------|
| Input | 800 | $3.00 | 800 / 1,000,000 × $3.00 | $0.0024 |
| Cache Write | 0 | $3.75 | 0 / 1,000,000 × $3.75 | $0.0000 |
| Cache Read | 8,500 | $0.30 | 8,500 / 1,000,000 × $0.30 | **$0.0026** |
| Output | 320 | $15.00 | 320 / 1,000,000 × $15.00 | $0.0048 |
| **TOTAL** | | | | **$0.0097** |

**Cache Savings:**
- Without cache: 8,500 tokens × $3.00/MTok = $0.0255
- With cache: 8,500 tokens × $0.30/MTok = $0.0026
- **Saved: $0.0229 (90% cheaper!)**

**UI Display:**
```
This Request: $0.010    ← Much cheaper!
Session Total: $0.052   ← Cumulative
```

**Color:** Total now shows in **green** (cache being used)

---

### Request 3: "Show me leads from last 30 days"

**User Action:** Another follow-up query

**Token Usage:**
```json
{
  "input_tokens": 950,
  "cache_creation_input_tokens": 0,
  "cache_read_input_tokens": 8500,      // Cache hit again!
  "output_tokens": 280
}
```

**Cost Calculation (Sonnet 4.5):**

| Token Type | Tokens | Price/MTok | Cost |
|------------|--------|------------|------|
| Input | 950 | $3.00 | $0.0029 |
| Cache Read | 8,500 | $0.30 | $0.0026 |
| Output | 280 | $15.00 | $0.0042 |
| **TOTAL** | | | **$0.0097** |

**UI Display:**
```
This Request: $0.010
Session Total: $0.062
```

**Color:** Still **green** (efficient cache usage)

---

## Session Summary (3 Requests)

### Total Tokens Used
```
Input tokens: 2,950
Cache creation tokens: 8,500
Cache read tokens: 17,000
Output tokens: 1,050
──────────────────────────────
Total: 29,500 tokens
```

### Total Costs
```
Request 1: $0.042
Request 2: $0.010
Request 3: $0.010
──────────────────
Total: $0.062
```

### Without Caching
```
Request 1: $0.042 (same)
Request 2: $0.035 (no cache)
Request 3: $0.035 (no cache)
──────────────────
Total: $0.112
```

### **Savings: $0.050 (45% cheaper with cache!)**

---

## Model Comparison for Same Session

### Sonnet 4.5 (Default)
```
Total cost: $0.062
```

### Sonnet 4
```
Total cost: $0.062
(Same pricing as Sonnet 4.5)
```

### Haiku 4.5
```
Request 1:
  Input: 1,200 / 1,000,000 × $1.00 = $0.0012
  Cache Write: 8,500 / 1,000,000 × $1.25 = $0.0106
  Output: 450 / 1,000,000 × $5.00 = $0.0023
  Total: $0.0141

Request 2:
  Input: 800 / 1,000,000 × $1.00 = $0.0008
  Cache Read: 8,500 / 1,000,000 × $0.10 = $0.0009
  Output: 320 / 1,000,000 × $5.00 = $0.0016
  Total: $0.0032

Request 3:
  Similar to Request 2: $0.0032

Session Total: $0.0205
```

### **Haiku is 3x cheaper: $0.062 vs $0.021**

---

## Visual Representation

### Cost Over Time
```
Request 1 (cache write):  ████████ $0.042
Request 2 (cache hit):    ██       $0.010
Request 3 (cache hit):    ██       $0.010
                          ──────────────────
                          Total:   $0.062
```

### Savings Visualization
```
Without Cache: ████████████████████ $0.112
With Cache:    ███████████          $0.062
               ────────────────────
Saved:         █████████            $0.050 (45%)
```

---

## Frontend Display Evolution

### Initial State
```
Token Usage
-----------
Input: 0
Output: 0
Cache Created: 0
Cache Read: 0

This Request: $0.000
Session Total: $0.000
```

### After Request 1
```
Token Usage
-----------
Input: 1,200
Output: 450
Cache Created: 8,500     ← Orange (expensive)
Cache Read: 0

This Request: $0.042
Session Total: $0.042    ← Default color
```

### After Request 2
```
Token Usage
-----------
Input: 2,000
Output: 770
Cache Created: 8,500
Cache Read: 8,500        ← Green (savings!)

This Request: $0.010     ← Cheaper!
Session Total: $0.052    ← Green (using cache)
```

### After Request 3
```
Token Usage
-----------
Input: 2,950
Output: 1,050
Cache Created: 8,500
Cache Read: 17,000       ← More cache hits!

This Request: $0.010
Session Total: $0.062    ← Still green
```

---

## Technical Implementation

### Backend (app.py)
```python
# Calculate request cost
request_usage = {
    "input_tokens": 800,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 8500,
    "output_tokens": 320
}
request_cost = calculate_cost(request_usage, "claude-sonnet-4-5-20250929")
# Returns: {"total_cost": 0.0097, ...}

# Calculate session total
total_cost = 0.0423 + 0.0097  # = 0.052

# Send to frontend
await self._safe_send({
    "type": "usage",
    "usage": {...},
    "cost": {
        "request_cost": 0.0097,
        "total_cost": 0.052
    }
})
```

### Frontend (index.html)
```javascript
function updateTokenUsage(usage, cost) {
    // Update request cost
    document.getElementById('request-cost').textContent = formatCost(0.0097);
    // Shows: "$0.010"

    // Update total cost
    document.getElementById('total-cost').textContent = formatCost(0.052);
    // Shows: "$0.05"

    // Color green if using cache
    if (usage.cache_read_tokens > 0) {
        totalCostElem.className = 'font-mono text-lg text-green-600';
    }
}
```

---

## Key Takeaways

1. **First request is always most expensive** (cache creation)
2. **Subsequent requests are 76% cheaper** (cache hits)
3. **Green = Good** (you're saving money!)
4. **Haiku is 3x cheaper** (for simple queries)
5. **Keep sessions alive** to maximize cache benefits

---

**This is exactly what users will see in the Web UI!**
