# USD Cost Calculation - Data Flow Diagram

## Overview

This diagram shows how cost data flows from the Claude API through the backend to the frontend display.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER SENDS QUERY                                 │
│                   "Get all leads from last 30 days"                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (index.html)                               │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  WebSocket.send({                                               │    │
│  │    type: "message",                                             │    │
│  │    content: "Get all leads from last 30 days"                   │    │
│  │  })                                                             │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       BACKEND (app.py)                                   │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  async def process_message_with_claude(user_message):          │    │
│  │    # Call Claude API with streaming                            │    │
│  │    async with claude_client.messages.stream(...) as stream:    │    │
│  │      final_message = await stream.get_final_message()          │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CLAUDE API RESPONSE                                 │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  final_message.usage = {                                        │    │
│  │    input_tokens: 800,                                           │    │
│  │    cache_creation_input_tokens: 0,                              │    │
│  │    cache_read_input_tokens: 8500,                               │    │
│  │    output_tokens: 320                                           │    │
│  │  }                                                              │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRICING MODULE (pricing.py)                           │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  request_usage = {                                              │    │
│  │    "input_tokens": 800,                                         │    │
│  │    "cache_creation_input_tokens": 0,                            │    │
│  │    "cache_read_input_tokens": 8500,                             │    │
│  │    "output_tokens": 320                                         │    │
│  │  }                                                              │    │
│  │                                                                 │    │
│  │  request_cost = calculate_cost(                                │    │
│  │    request_usage,                                               │    │
│  │    "claude-sonnet-4-5-20250929"                                 │    │
│  │  )                                                              │    │
│  │                                                                 │    │
│  │  # Returns:                                                     │    │
│  │  {                                                              │    │
│  │    "input_cost": 0.0024,                                        │    │
│  │    "cache_write_cost": 0.0000,                                  │    │
│  │    "cache_read_cost": 0.0026,                                   │    │
│  │    "output_cost": 0.0048,                                       │    │
│  │    "total_cost": 0.0097                                         │    │
│  │  }                                                              │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  BACKEND SESSION TRACKING (app.py)                       │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  # Update session totals                                        │    │
│  │  self.total_input_tokens += 800                                 │    │
│  │  self.total_output_tokens += 320                                │    │
│  │  self.total_cache_read_tokens += 8500                           │    │
│  │                                                                 │    │
│  │  # Calculate total session cost                                │    │
│  │  total_usage = {                                                │    │
│  │    "input_tokens": self.total_input_tokens,                     │    │
│  │    "cache_creation_input_tokens": self.total_cache_creation,    │    │
│  │    "cache_read_input_tokens": self.total_cache_read,            │    │
│  │    "output_tokens": self.total_output_tokens                    │    │
│  │  }                                                              │    │
│  │                                                                 │    │
│  │  total_cost = calculate_cost(total_usage, model)               │    │
│  │  self.total_cost = total_cost['total_cost']                     │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  WEBSOCKET MESSAGE TO FRONTEND                           │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  await self._safe_send({                                        │    │
│  │    "type": "usage",                                             │    │
│  │    "usage": {                                                   │    │
│  │      "input_tokens": 800,                                       │    │
│  │      "output_tokens": 320,                                      │    │
│  │      "cache_creation_tokens": 0,                                │    │
│  │      "cache_read_tokens": 8500,                                 │    │
│  │      "total_input_tokens": 2000,                                │    │
│  │      "total_output_tokens": 770,                                │    │
│  │      "total_cache_creation_tokens": 8500,                       │    │
│  │      "total_cache_read_tokens": 8500                            │    │
│  │    },                                                           │    │
│  │    "cost": {                                                    │    │
│  │      "request_cost": 0.0097,                                    │    │
│  │      "request_breakdown": {...},                                │    │
│  │      "total_cost": 0.052,                                       │    │
│  │      "total_breakdown": {...}                                   │    │
│  │    }                                                            │    │
│  │  })                                                             │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   FRONTEND MESSAGE HANDLER                               │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  ws.onmessage = (event) => {                                    │    │
│  │    const data = JSON.parse(event.data);                         │    │
│  │                                                                 │    │
│  │    switch(data.type) {                                          │    │
│  │      case 'usage':                                              │    │
│  │        updateTokenUsage(data.usage, data.cost);                 │    │
│  │        break;                                                   │    │
│  │    }                                                            │    │
│  │  }                                                              │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND UPDATE FUNCTION                              │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  function updateTokenUsage(usage, cost) {                       │    │
│  │    // Update token counts                                       │    │
│  │    document.getElementById('total-input-tokens')                │    │
│  │      .textContent = usage.total_input_tokens.toLocaleString();  │    │
│  │                                                                 │    │
│  │    // Update costs                                              │    │
│  │    if (cost) {                                                  │    │
│  │      document.getElementById('request-cost')                    │    │
│  │        .textContent = formatCost(cost.request_cost);            │    │
│  │                                                                 │    │
│  │      const totalCostElem =                                      │    │
│  │        document.getElementById('total-cost');                   │    │
│  │      totalCostElem.textContent =                                │    │
│  │        formatCost(cost.total_cost);                             │    │
│  │                                                                 │    │
│  │      // Color-code based on cache usage                         │    │
│  │      if (usage.cache_read_tokens > 0) {                         │    │
│  │        totalCostElem.className =                                │    │
│  │          'font-mono text-lg text-green-600';                    │    │
│  │      }                                                          │    │
│  │    }                                                            │    │
│  │  }                                                              │    │
│  │                                                                 │    │
│  │  function formatCost(cost) {                                    │    │
│  │    if (cost < 0.01) {                                           │    │
│  │      return `$${cost.toFixed(3)}`;                              │    │
│  │    } else {                                                     │    │
│  │      return `$${cost.toFixed(2)}`;                              │    │
│  │    }                                                            │    │
│  │  }                                                              │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        UI DISPLAY UPDATE                                 │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Token Usage                                                    │    │
│  │  -----------                                                    │    │
│  │  Input: 2,000                                                   │    │
│  │  Output: 770                                                    │    │
│  │                                                                 │    │
│  │  Cache Created: 8,500                                           │    │
│  │  Cache Read: 8,500                                              │    │
│  │                                                                 │    │
│  │  This Request: $0.010      ← From request_cost                  │    │
│  │  Session Total: $0.052     ← From total_cost (GREEN!)           │    │
│  │  -----------                                                    │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      USER SEES COST UPDATE                               │
│                                                                          │
│              ✅ Cost is lower than first request                         │
│              ✅ Green color indicates cache efficiency                   │
│              ✅ Session total is cumulative                              │
│              ✅ Can monitor spending in real-time                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Pricing Module (`pricing.py`)
- **Input:** Token usage dict + model name
- **Output:** Cost breakdown with total
- **Pricing:** Based on official Anthropic rates
- **Models:** Sonnet 4.5, Sonnet 4, Haiku 4.5

### 2. Backend Tracking (`app.py`)
- **Session State:** Tracks cumulative tokens and costs
- **Per-Request:** Calculates individual request costs
- **WebSocket:** Sends cost data to frontend
- **Logging:** Records costs in backend logs

### 3. Frontend Display (`index.html`)
- **Real-time Updates:** Shows costs as they arrive
- **Color Coding:** Green = efficient, Orange = expensive
- **Smart Formatting:** $0.001 vs $1.50
- **Token Breakdown:** Shows cache metrics

## Data Flow Summary

```
User Query
    ↓
WebSocket Send
    ↓
Backend receives
    ↓
Call Claude API
    ↓
Get token usage
    ↓
Calculate costs (pricing.py)
    ↓
Update session totals
    ↓
Send via WebSocket
    ↓
Frontend receives
    ↓
Update UI display
    ↓
User sees costs
```

## Cost Calculation Detail

### Step 1: Extract Tokens
```python
input_tokens = 800
cache_creation = 0
cache_read = 8500
output_tokens = 320
```

### Step 2: Get Pricing
```python
pricing = PRICING["claude-sonnet-4-5-20250929"]
# {
#   "input": 3.0,
#   "cache_write_5m": 3.75,
#   "cache_read": 0.30,
#   "output": 15.0
# }
```

### Step 3: Calculate
```python
input_cost = (800 / 1_000_000) * 3.0 = 0.0024
cache_read_cost = (8500 / 1_000_000) * 0.30 = 0.0026
output_cost = (320 / 1_000_000) * 15.0 = 0.0048
total_cost = 0.0024 + 0.0026 + 0.0048 = 0.0097
```

### Step 4: Format
```python
formatCost(0.0097)  # Returns "$0.010"
```

## WebSocket Message Format

### Complete Message Structure
```json
{
  "type": "usage",
  "usage": {
    "input_tokens": 800,
    "output_tokens": 320,
    "cache_creation_tokens": 0,
    "cache_read_tokens": 8500,
    "total_input_tokens": 2000,
    "total_output_tokens": 770,
    "total_cache_creation_tokens": 8500,
    "total_cache_read_tokens": 8500
  },
  "cost": {
    "request_cost": 0.0097,
    "request_breakdown": {
      "input_cost": 0.0024,
      "cache_write_cost": 0.0000,
      "cache_read_cost": 0.0026,
      "output_cost": 0.0048,
      "total_cost": 0.0097
    },
    "total_cost": 0.052,
    "total_breakdown": {
      "input_cost": 0.006,
      "cache_write_cost": 0.0319,
      "cache_read_cost": 0.0026,
      "output_cost": 0.0115,
      "total_cost": 0.052
    }
  },
  "timestamp": "2025-11-11T10:30:45.123456"
}
```

## Error Handling

### Missing Cost Data
```javascript
if (cost) {
    // Update costs
} else {
    // Skip cost update, show only tokens
}
```

### Invalid Model
```python
pricing = PRICING.get(model_name, DEFAULT_PRICING)
# Falls back to Sonnet 4.5 pricing
```

### Zero Cost
```python
formatCost(0.0)  # Returns "$0.00"
```

---

**This diagram shows the complete end-to-end flow of cost data from Claude API to user display.**
