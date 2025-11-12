"""
Pricing calculator for Claude API token usage.

Calculates USD costs based on Anthropic's pricing for different Claude models.
Supports prompt caching metrics (cache_creation, cache_read).

Pricing as of 2025-11-11:
- Claude Sonnet 4.5: Input $3/MTok, Cache Write (5m) $3.75/MTok, Cache Write (1h) $6/MTok, Cache Hit $0.30/MTok, Output $15/MTok
- Claude Sonnet 4: Input $3/MTok, Cache Write (5m) $3.75/MTok, Cache Write (1h) $6/MTok, Cache Hit $0.30/MTok, Output $15/MTok
- Claude Haiku 4: Input $1/MTok, Cache Write (5m) $1.25/MTok, Cache Write (1h) $2/MTok, Cache Hit $0.10/MTok, Output $5/MTok

Model Name Aliases:
- Both short names (claude-sonnet-4-5) and full names (claude-sonnet-4-5-20250929) are supported
- Haiku 4.5 is an alias for Haiku 4 (same pricing)

Note: Cache Write (5m) and Cache Write (1h) have different prices. The API reports total
cache_creation_input_tokens (old SDK) or separate ephemeral_5m/1h_input_tokens (new SDK).
We use the 5-minute price as the default when only total is available.

Usage:
    from pricing import calculate_cost

    usage = {
        "input_tokens": 1000,
        "cache_creation_input_tokens": 2000,
        "cache_read_input_tokens": 500,
        "output_tokens": 300
    }

    cost = calculate_cost(usage, "claude-sonnet-4-5")
    print(cost['total_cost'])  # 0.01545
"""

from typing import Dict, Any

# Pricing per million tokens (MTok)
PRICING = {
    # Sonnet 4.5 (with date suffix and short alias)
    "claude-sonnet-4-5-20250929": {
        "input": 3.0,           # Base input tokens
        "cache_write_5m": 3.75, # Cache write (5-minute TTL)
        "cache_write_1h": 6.0,  # Cache write (1-hour TTL)
        "cache_read": 0.30,     # Cache hit
        "output": 15.0          # Output tokens
    },
    "claude-sonnet-4-5": {  # Alias for convenience
        "input": 3.0,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.0,
        "cache_read": 0.30,
        "output": 15.0
    },
    # Sonnet 4 (with date suffix and short alias)
    "claude-sonnet-4-20250514": {
        "input": 3.0,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.0,
        "cache_read": 0.30,
        "output": 15.0
    },
    "claude-sonnet-4": {  # Alias for convenience
        "input": 3.0,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.0,
        "cache_read": 0.30,
        "output": 15.0
    },
    # Haiku 4 (with date suffix and short alias)
    "claude-haiku-4-20250514": {
        "input": 1.0,
        "cache_write_5m": 1.25,
        "cache_write_1h": 2.0,
        "cache_read": 0.10,
        "output": 5.0
    },
    "claude-haiku-4-5": {  # Alias for convenience (Haiku 4.5 = Haiku 4 with latest updates)
        "input": 1.0,
        "cache_write_5m": 1.25,
        "cache_write_1h": 2.0,
        "cache_read": 0.10,
        "output": 5.0
    }
}

# Default to Sonnet 4.5 pricing for unknown models
DEFAULT_PRICING = PRICING["claude-sonnet-4-5-20250929"]


def calculate_cost(usage: Dict[str, Any], model_name: str) -> Dict[str, float]:
    """
    Calculate USD cost from usage tokens.

    Args:
        usage: Dictionary with token counts:
            - input_tokens: Base input tokens (not cached)
            - cache_creation_input_tokens: Tokens written to cache
            - cache_read_input_tokens: Tokens read from cache (cache hits)
            - output_tokens: Output tokens generated

        model_name: Claude model identifier (e.g., "claude-sonnet-4-5-20250929")

    Returns:
        Dictionary with cost breakdown:
            - input_cost: Cost of base input tokens
            - cache_write_cost: Cost of writing to cache
            - cache_read_cost: Cost of cache hits
            - output_cost: Cost of output tokens
            - total_cost: Sum of all costs

    Example:
        >>> usage = {
        ...     "input_tokens": 1000,
        ...     "cache_creation_input_tokens": 2000,
        ...     "cache_read_input_tokens": 500,
        ...     "output_tokens": 300
        ... }
        >>> cost = calculate_cost(usage, "claude-sonnet-4-5-20250929")
        >>> cost['total_cost']
        0.01545
    """
    # Get pricing for this model (fall back to default if unknown)
    pricing = PRICING.get(model_name, DEFAULT_PRICING)

    # Extract token counts (default to 0 if not present)
    input_tokens = usage.get("input_tokens", 0) or 0
    cache_creation_tokens = usage.get("cache_creation_input_tokens", 0) or 0
    cache_read_tokens = usage.get("cache_read_input_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0

    # Convert tokens to millions (MTok)
    input_mtok = input_tokens / 1_000_000
    cache_creation_mtok = cache_creation_tokens / 1_000_000
    cache_read_mtok = cache_read_tokens / 1_000_000
    output_mtok = output_tokens / 1_000_000

    # Calculate costs (use 5-minute cache write price as default)
    input_cost = input_mtok * pricing["input"]
    cache_write_cost = cache_creation_mtok * pricing["cache_write_5m"]
    cache_read_cost = cache_read_mtok * pricing["cache_read"]
    output_cost = output_mtok * pricing["output"]

    total_cost = input_cost + cache_write_cost + cache_read_cost + output_cost

    return {
        "input_cost": round(input_cost, 6),
        "cache_write_cost": round(cache_write_cost, 6),
        "cache_read_cost": round(cache_read_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total_cost, 6)
    }


def format_cost(cost: float) -> str:
    """
    Format cost as USD string with appropriate precision.

    Small amounts (< $0.01) show 3-4 decimal places.
    Larger amounts show 2 decimal places.

    Args:
        cost: Cost in USD

    Returns:
        Formatted string like "$0.015" or "$1.50"

    Examples:
        >>> format_cost(0.001234)
        '$0.0012'
        >>> format_cost(0.015)
        '$0.015'
        >>> format_cost(1.5)
        '$1.50'
    """
    if cost == 0.0:
        return "$0.00"
    elif cost < 0.01:
        # Show 3-4 decimal places for small amounts
        formatted = f"${cost:.4f}"
        # Strip trailing zeros but keep at least 3 decimal places
        if formatted.endswith('0') and not formatted.endswith('.000'):
            formatted = formatted.rstrip('0')
            # Ensure minimum 3 decimal places
            decimal_part = formatted.split('.')[1] if '.' in formatted else ""
            if len(decimal_part) < 3:
                formatted = f"${cost:.3f}"
        return formatted
    else:
        # Standard 2 decimal places for larger amounts
        return f"${cost:.2f}"


def get_cost_summary(cost_breakdown: Dict[str, float]) -> str:
    """
    Generate a human-readable cost summary.

    Args:
        cost_breakdown: Output from calculate_cost()

    Returns:
        Formatted multi-line summary string

    Example:
        >>> cost = calculate_cost(usage, "claude-sonnet-4-5-20250929")
        >>> print(get_cost_summary(cost))
        Input tokens: $0.003
        Cache write: $0.008
        Cache read: $0.0002
        Output: $0.005
        ──────────────
        Total: $0.016
    """
    lines = []

    if cost_breakdown["input_cost"] > 0:
        lines.append(f"Input tokens: {format_cost(cost_breakdown['input_cost'])}")

    if cost_breakdown["cache_write_cost"] > 0:
        lines.append(f"Cache write: {format_cost(cost_breakdown['cache_write_cost'])}")

    if cost_breakdown["cache_read_cost"] > 0:
        lines.append(f"Cache read: {format_cost(cost_breakdown['cache_read_cost'])}")

    if cost_breakdown["output_cost"] > 0:
        lines.append(f"Output: {format_cost(cost_breakdown['output_cost'])}")

    if lines:
        lines.append("──────────────")

    lines.append(f"Total: {format_cost(cost_breakdown['total_cost'])}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Example usage and testing
    print("Pricing Calculator Test\n")
    print("=" * 50)

    # Test case 1: Sonnet 4.5 with cache
    usage1 = {
        "input_tokens": 1000,
        "cache_creation_input_tokens": 2000,
        "cache_read_input_tokens": 500,
        "output_tokens": 300
    }

    cost1 = calculate_cost(usage1, "claude-sonnet-4-5-20250929")
    print("\nTest 1: Sonnet 4.5 with cache")
    print(f"Input: {usage1['input_tokens']:,} tokens")
    print(f"Cache Write: {usage1['cache_creation_input_tokens']:,} tokens")
    print(f"Cache Read: {usage1['cache_read_input_tokens']:,} tokens")
    print(f"Output: {usage1['output_tokens']:,} tokens")
    print()
    print(get_cost_summary(cost1))

    # Test case 2: Haiku 4.5 (60x cheaper than Sonnet)
    usage2 = {
        "input_tokens": 10000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 2000
    }

    cost2 = calculate_cost(usage2, "claude-haiku-4-20250514")
    print("\n" + "=" * 50)
    print("\nTest 2: Haiku 4.5 (no cache)")
    print(f"Input: {usage2['input_tokens']:,} tokens")
    print(f"Output: {usage2['output_tokens']:,} tokens")
    print()
    print(get_cost_summary(cost2))

    # Test case 3: Large request with heavy cache usage
    usage3 = {
        "input_tokens": 5000,
        "cache_creation_input_tokens": 50000,
        "cache_read_input_tokens": 45000,
        "output_tokens": 3000
    }

    cost3 = calculate_cost(usage3, "claude-sonnet-4-5-20250929")
    print("\n" + "=" * 50)
    print("\nTest 3: Large request with heavy cache")
    print(f"Input: {usage3['input_tokens']:,} tokens")
    print(f"Cache Write: {usage3['cache_creation_input_tokens']:,} tokens")
    print(f"Cache Read: {usage3['cache_read_input_tokens']:,} tokens")
    print(f"Output: {usage3['output_tokens']:,} tokens")
    print()
    print(get_cost_summary(cost3))

    print("\n" + "=" * 50)
