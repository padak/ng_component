# Token Usage Tracking - Visual Flow Diagrams

## Token Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE API RESPONSE                          │
│  {                                                              │
│    "usage": {                                                   │
│      "input_tokens": 1250,                                      │
│      "output_tokens": 450,                                      │
│      "cache_creation_input_tokens": 2000,                       │
│      "cache_read_input_tokens": 0                               │
│    }                                                             │
│  }                                                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              BACKEND: process_message_with_claude()              │
│                                                                  │
│  # Get usage from final_message                                 │
│  usage = final_message.usage                                    │
│                                                                  │
│  # Accumulate in session                                        │
│  self.total_input_tokens += 1250                                │
│  self.total_output_tokens += 450                                │
│  self.total_cache_creation_tokens += 2000                       │
│  self.total_cache_read_tokens += 0                              │
│                                                                  │
│  # Send to frontend                                             │
│  await send_usage_message({                                     │
│    "input_tokens": 1250,         # Per-request                  │
│    "output_tokens": 450,         # Per-request                  │
│    "cache_creation_tokens": 2000,    # Per-request              │
│    "cache_read_tokens": 0,           # Per-request              │
│    "total_input_tokens": 1250,       # Cumulative               │
│    "total_output_tokens": 450,       # Cumulative               │
│    "total_cache_creation_tokens": 2000,   # Cumulative          │
│    "total_cache_read_tokens": 0           # Cumulative          │
│  })                                                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼ WebSocket message
┌──────────────────────────────────────────────────────────────────┐
│         FRONTEND: handleMessage() → updateTokenUsage()           │
│                                                                  │
│  case 'usage':                                                  │
│    updateTokenUsage(data.usage)                                 │
│    {                                                             │
│      document.getElementById('total-input-tokens')              │
│        .textContent = 1250.toLocaleString() → "1,250"           │
│                                                                  │
│      document.getElementById('total-output-tokens')             │
│        .textContent = 450.toLocaleString() → "450"              │
│                                                                  │
│      document.getElementById('total-cache-creation-tokens')     │
│        .textContent = 2000.toLocaleString() → "2,000"           │
│                                                                  │
│      document.getElementById('total-cache-read-tokens')         │
│        .textContent = 0.toLocaleString() → "0"                  │
│                                                                  │
│      const total = 1250 + 450 → "1,700"                         │
│      document.getElementById('total-all-tokens')                │
│        .textContent = total.toLocaleString()                    │
│    }                                                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │  UI DISPLAYS  │
                   │               │
                   │ Input: 1,250  │
                   │ Output: 450   │
                   │ Cache Created: 2,000 (orange)
                   │ Cache Read: 0 (green)
                   │ Total: 1,700  │
                   └───────────────┘
```

## Multi-Turn Conversation Token Accumulation

```
Request 1: "What objects are available?"
┌─────────────────────────────────────┐
│ Claude Response                     │
│ input_tokens: 850                   │
│ output_tokens: 300                  │
│ cache_creation_tokens: 2000         │
│ cache_read_tokens: 0                │
└─────────────────────────────────────┘
    │
    └─► Session totals:
        input: 850
        output: 300
        cache_creation: 2000
        cache_read: 0

Request 2: "Get all leads"
┌─────────────────────────────────────┐
│ Claude Response                     │
│ input_tokens: 1200                  │
│ output_tokens: 450                  │
│ cache_creation_tokens: 0            │ ◄─── Cache HIT!
│ cache_read_tokens: 2000             │      (90% cheaper)
└─────────────────────────────────────┘
    │
    └─► Session totals:
        input: 850 + 1200 = 2050
        output: 300 + 450 = 750
        cache_creation: 2000 (unchanged)
        cache_read: 0 + 2000 = 2000 ◄─── Shows cache benefit!

Request 3: "Filter by status"
┌─────────────────────────────────────┐
│ Claude Response                     │
│ input_tokens: 1100                  │
│ output_tokens: 380                  │
│ cache_creation_tokens: 0            │
│ cache_read_tokens: 2000             │ ◄─── Cache HIT again!
└─────────────────────────────────────┘
    │
    └─► Session totals:
        input: 850 + 1200 + 1100 = 3150
        output: 300 + 450 + 380 = 1130
        cache_creation: 2000 (one-time cost)
        cache_read: 2000 + 2000 = 4000 ◄─── Total cached reads
```

## Token Breakdown in UI

```
Sidebar "Token Usage" Card:
┌────────────────────────────────┐
│ Input:              1,250       │ ◄─── Regular input tokens
├────────────────────────────────┤
│ Output:               450       │ ◄─── Generated tokens
├────────────────────────────────┤
│ Cache Created:      2,000       │ ◄─── Orange text
│                                 │     (paid in full, written once)
├────────────────────────────────┤
│ Cache Read:         2,000       │ ◄─── Green text
│                                 │     (90% cheaper, reused)
├────────────────────────────────┤
│ Total:              1,700       │ ◄─── input + output
│                                 │     (excludes cache metrics)
└────────────────────────────────┘

Cost Analysis (if using claude-sonnet-4-5):
  - Input tokens: 1,250 × $15/1M = $0.01875
  - Output tokens: 450 × $75/1M = $0.03375
  - Cache created: 2,000 × $15/1M = $0.03 (first time only)
  - Cache read: 2,000 × $1.50/1M = $0.003 (90% discount!)
  
  Per request cost: ~$0.05625
  Without caching: ~$0.065 (cost per cache reuse)
```

## Token Usage Timeline

```
Timeline of a Multi-Turn Conversation:

Time  | Event                          | Backend State              | Frontend Display
------|--------------------------------|----------------------------|----------------------------------
0:00  | User: "What objects?"          |                            |
0:05  | Claude streaming response      | -                          | [Agent is thinking...]
0:10  | ✅ agent_delta (complete)      | -                          | Shows thinking indicator
0:12  | usage sent                     | total_input: 850           | Updates counters
      |                                | total_output: 300          | Input: 850, Output: 300
      |                                | cache_created: 2000        | Cache: 2,000
0:15  | ✅ agent_message (final)       | -                          | Displays response
      |                                |                            |
1:00  | User: "Get all leads"          |                            |
1:05  | Claude streaming response      | -                          | [Agent is thinking...]
1:12  | ✅ Tool: discover_objects      | -                          | ⚙️ Using tool: discover_objects
1:20  | ✅ Tool: completed             | -                          | ✅ Using tool: discover_objects
1:22  | Claude continues streaming     | -                          | [Agent is thinking...]
1:25  | ✅ Tool: execute_salesforce    | -                          | ⚙️ Using tool: execute_salesforce_query
2:00  | ✅ Tool: completed             | -                          | ✅ Using tool: execute_salesforce_query
2:05  | ✅ agent_delta (complete)      | -                          | [Agent is thinking...]
2:10  | usage sent                     | total_input: 2050          | Updates counters
      |                                | total_output: 750          | Input: 2,050, Output: 750
      |                                | cache_read: 2000          | Cache Read: 2,000 ◄─── Hit!
2:15  | ✅ agent_message (final)       | -                          | Displays response
```

## Cache Control Configuration

```
Request Header:
┌──────────────────────────────────────────────────────┐
│ system: [                                            │
│   {                                                  │
│     "type": "text",                                  │
│     "text": "You are an expert...[~2000 tokens]",    │
│     "cache_control": {                               │
│       "type": "ephemeral"                            │
│     }                                                │
│   }                                                  │
│ ]                                                    │
└──────────────────────────────────────────────────────┘
                      │
         ┌────────────┴─────────────┐
         │                          │
    First Request            Subsequent Requests
         │                          │
         ▼                          ▼
    ┌──────────┐            ┌──────────────┐
    │ WRITE    │            │ READ         │
    │ CACHE    │            │ CACHE        │
    │          │            │              │
    │ Cost: 3× │            │ Cost: 0.3×   │
    │ Full     │            │ (90% save)   │
    └──────────┘            └──────────────┘
         │                          │
         │ cache_creation_          │ cache_read_
         │ input_tokens: 2000       │ input_tokens: 2000
         │                          │
         └──────────────┬───────────┘
                        │
                        ▼
                  Usage Metrics
                  Sent to Frontend
```

## Per-Request vs Cumulative Tokens

```
Session with 3 Requests:

Request 1: "What objects?"
│
├─ Per-request metrics:          Cumulative so far:
│  input: 850                     input: 850
│  output: 300                    output: 300
│  cache_creation: 2000           cache_creation: 2000
│  cache_read: 0                  cache_read: 0
│
└─► Send to frontend: {
      "input_tokens": 850,                    ◄─ Per-request
      "total_input_tokens": 850,              ◄─ Cumulative
      "cache_creation_tokens": 2000,          ◄─ Per-request
      "total_cache_creation_tokens": 2000     ◄─ Cumulative
    }

Request 2: "Get all leads"
│
├─ Per-request metrics:          Cumulative so far:
│  input: 1200                    input: 2050
│  output: 450                    output: 750
│  cache_creation: 0              cache_creation: 2000
│  cache_read: 2000               cache_read: 2000
│
└─► Send to frontend: {
      "input_tokens": 1200,                   ◄─ Per-request (new)
      "total_input_tokens": 2050,             ◄─ Cumulative (updated)
      "cache_read_tokens": 2000,              ◄─ Per-request (new)
      "total_cache_read_tokens": 2000         ◄─ Cumulative (updated)
    }

Request 3: "Filter by status"
│
├─ Per-request metrics:          Cumulative so far:
│  input: 1100                    input: 3150
│  output: 380                    output: 1130
│  cache_creation: 0              cache_creation: 2000
│  cache_read: 2000               cache_read: 4000
│
└─► Send to frontend: {
      "input_tokens": 1100,                   ◄─ Per-request
      "total_input_tokens": 3150,             ◄─ Cumulative (updated)
      "cache_read_tokens": 2000,              ◄─ Per-request
      "total_cache_read_tokens": 4000         ◄─ Cumulative (updated)
    }

Frontend Display Shows: ▌ CUMULATIVE TOTALS ONLY ▌
(Per-request metrics available but not displayed)
```

## Important Notes

### Token Counting
- **Input tokens** = System prompt + conversation history + user message
- **Output tokens** = Claude's generated response
- **Cache creation tokens** = First time system prompt is sent (charged fully)
- **Cache read tokens** = Subsequent requests reusing cached system prompt (charged 10%)

### Cache Behavior
- Cache is **per-session** (per WebSocket connection)
- Cache **persists for 5 minutes** (ephemeral)
- If user disconnects and reconnects within 5 minutes, cache is available
- If 5 minutes elapse, cache expires and new cache is created

### Cost Savings
```
Without caching:
Every request pays for system prompt (~2000 tokens × $15/MTok = $0.03)

With caching:
Request 1: $0.03 (cache write)
Request 2-N: $0.003 each (cache read, 90% discount)

For 10 requests:
Without cache: $0.30
With cache: $0.03 + (9 × $0.003) = $0.057
Savings: 81% cheaper!
```

### Current Frontend Display Issue
The frontend currently only displays **cumulative totals**:
- `total_input_tokens`
- `total_output_tokens` 
- `total_cache_creation_tokens`
- `total_cache_read_tokens`

The per-request metrics are sent but not displayed:
- `input_tokens` (per-request) ← Available but not shown
- `output_tokens` (per-request) ← Available but not shown
- `cache_creation_tokens` (per-request) ← Available but not shown
- `cache_read_tokens` (per-request) ← Available but not shown

**Recommendation:** Consider adding an expandable "Details" section to show per-request breakdown for transparency.

