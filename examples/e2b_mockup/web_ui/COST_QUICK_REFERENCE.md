# Cost Calculator - Quick Reference

## What You'll See

When using the Web UI at `http://localhost:8080/static/`, the **Token Usage** sidebar now displays:

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

## Understanding the Costs

### This Request
Shows the cost of the most recent API call.

**Example:** If you ask "Get all leads", this shows what that single query cost.

### Session Total
Cumulative cost for all queries in your current session (since page load).

**Color Coding:**
- **Green** = Using cache efficiently (saving money!)
- **Orange** = Session is getting expensive (>$0.50 total)
- **Default** = Normal usage

## How Caching Saves You Money

### First Request (Cache Write)
```
Cache Created: 8,500 tokens
Cost: $0.032 for cache write
```

### Second Request (Cache Hit)
```
Cache Read: 8,500 tokens
Cost: $0.003 for cache read (90% cheaper!)
```

**Savings Example:**
- Without cache: 10 requests = $0.58
- With cache: 10 requests = $0.23
- **You save: $0.35 (60% cheaper!)**

## Model Pricing Comparison

For the same 10,000 input + 2,000 output tokens:

| Model | Cost | Best For |
|-------|------|----------|
| **Sonnet 4.5** | $0.06 | Complex queries, best quality |
| **Sonnet 4** | $0.06 | Balanced performance |
| **Haiku 4.5** | $0.02 | Simple queries, 3x cheaper! |

## Tips to Save Money

### 1. Enable Prompt Caching (Default: ON)
Already enabled! You'll see green text when cache is working.

### 2. Use Haiku for Simple Queries
Edit `.env` file:
```bash
CLAUDE_MODEL=claude-haiku-4-20250514
```

Restart server:
```bash
uvicorn app:app --reload --port 8080
```

### 3. Group Related Queries
Ask follow-up questions in the same session to maximize cache hits.

**Good:**
```
You: "Get all leads"
You: "Show me leads from last week"  ← Cache hit!
You: "Filter by New status"          ← Cache hit!
```

**Less Efficient:**
```
You: "Get all leads"
[Refresh page]  ← Cache lost!
You: "Show me leads from last week"  ← No cache hit
```

## Real-World Cost Examples

### Example 1: Quick Query
```
Query: "What objects are available?"
Tokens: 1,200 input + 8,500 cache + 300 output
Cost: $0.042
```

### Example 2: Follow-up (Cache Hit)
```
Query: "Get all leads"
Tokens: 800 input + 8,500 cached + 400 output
Cost: $0.010 (76% cheaper!)
```

### Example 3: 10-Query Session
```
Total tokens: 168,500
Total cost: $0.23
Average per query: $0.023
```

### Example 4: Same Session Without Cache
```
Total tokens: 168,500
Total cost: $0.58
Average per query: $0.058
```

**Savings: $0.35 (60%)**

## Monitoring Your Costs

### Watch for Orange
If Session Total turns orange (>$0.50), consider:
- Switching to Haiku model
- Being more specific in queries
- Refreshing less often (preserves cache)

### Check Cache Usage
Green cache numbers = you're saving money!
- **Cache Created** = First-time cost (orange)
- **Cache Read** = Savings (green)

## Frequently Asked Questions

### Q: Why is my first query more expensive?
**A:** The system prompt is being cached. Subsequent queries will be cheaper!

### Q: What happens if I refresh the page?
**A:** Cache is lost, next query will create cache again.

### Q: Can I see a breakdown of costs?
**A:** Currently shows total. Breakdown tooltip coming in future update!

### Q: How accurate are these costs?
**A:** Based on official Anthropic pricing (accurate to 0.001 cents).

### Q: Does this include E2B sandbox costs?
**A:** No, this only shows Claude API costs. E2B costs are separate.

## Need Help?

- Check logs: Backend shows cost calculation per request
- Verify pricing: See `pricing.py` for current rates
- Report issues: Costs not matching? Check model in `.env`

## Pro Tips

1. **First query of session is always most expensive** (cache creation)
2. **Keep sessions alive** to maximize cache hits
3. **Haiku is 3x cheaper** for simple data queries
4. **Green = Good** - You're using cache efficiently!
5. **Watch the Session Total** - Budget your usage

---

**Happy querying! Watch those costs drop with caching! 📉💰**
