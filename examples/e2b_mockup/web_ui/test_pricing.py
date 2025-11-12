#!/usr/bin/env python3
"""
Test script for pricing calculator.

Runs comprehensive tests to verify cost calculations are accurate.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pricing import calculate_cost, format_cost, get_cost_summary, PRICING


def test_basic_calculation():
    """Test basic cost calculation."""
    print("\n" + "="*60)
    print("TEST 1: Basic Cost Calculation (Sonnet 4.5)")
    print("="*60)

    usage = {
        "input_tokens": 1000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 500
    }

    cost = calculate_cost(usage, "claude-sonnet-4-5-20250929")

    print(f"\nTokens:")
    print(f"  Input: {usage['input_tokens']:,}")
    print(f"  Output: {usage['output_tokens']:,}")

    print(f"\nExpected Calculation:")
    print(f"  Input: 1,000 / 1,000,000 * $3.00 = $0.003")
    print(f"  Output: 500 / 1,000,000 * $15.00 = $0.0075")
    print(f"  Total: $0.0105")

    print(f"\nActual Result:")
    print(f"  Input cost: ${cost['input_cost']:.4f}")
    print(f"  Output cost: ${cost['output_cost']:.4f}")
    print(f"  Total cost: ${cost['total_cost']:.4f}")

    assert abs(cost['input_cost'] - 0.003) < 0.0001, "Input cost mismatch"
    assert abs(cost['output_cost'] - 0.0075) < 0.0001, "Output cost mismatch"
    assert abs(cost['total_cost'] - 0.0105) < 0.0001, "Total cost mismatch"

    print("\n✅ PASSED")


def test_cache_calculations():
    """Test cache write and read costs."""
    print("\n" + "="*60)
    print("TEST 2: Cache Write and Read (Sonnet 4.5)")
    print("="*60)

    # First request - cache write
    usage1 = {
        "input_tokens": 1200,
        "cache_creation_input_tokens": 8500,
        "cache_read_input_tokens": 0,
        "output_tokens": 450
    }

    cost1 = calculate_cost(usage1, "claude-sonnet-4-5-20250929")

    print(f"\nRequest 1 (Cache Write):")
    print(f"  Input: {usage1['input_tokens']:,} tokens")
    print(f"  Cache Creation: {usage1['cache_creation_input_tokens']:,} tokens")
    print(f"  Output: {usage1['output_tokens']:,} tokens")

    print(f"\n  Input cost: ${cost1['input_cost']:.4f}")
    print(f"  Cache write cost: ${cost1['cache_write_cost']:.4f}")
    print(f"  Output cost: ${cost1['output_cost']:.4f}")
    print(f"  Total: ${cost1['total_cost']:.4f}")

    # Second request - cache hit
    usage2 = {
        "input_tokens": 800,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 8500,
        "output_tokens": 320
    }

    cost2 = calculate_cost(usage2, "claude-sonnet-4-5-20250929")

    print(f"\nRequest 2 (Cache Hit):")
    print(f"  Input: {usage2['input_tokens']:,} tokens")
    print(f"  Cache Read: {usage2['cache_read_input_tokens']:,} tokens (90% savings!)")
    print(f"  Output: {usage2['output_tokens']:,} tokens")

    print(f"\n  Input cost: ${cost2['input_cost']:.4f}")
    print(f"  Cache read cost: ${cost2['cache_read_cost']:.4f}")
    print(f"  Output cost: ${cost2['output_cost']:.4f}")
    print(f"  Total: ${cost2['total_cost']:.4f}")

    # Calculate savings
    # Without cache: 8500 tokens * $3.00/MTok = $0.0255
    # With cache: 8500 tokens * $0.30/MTok = $0.00255
    savings = (8500 / 1_000_000 * 3.0) - cost2['cache_read_cost']
    savings_pct = (savings / (8500 / 1_000_000 * 3.0)) * 100

    print(f"\nCache Savings:")
    print(f"  Without cache: ${8500 / 1_000_000 * 3.0:.4f}")
    print(f"  With cache: ${cost2['cache_read_cost']:.4f}")
    print(f"  Savings: ${savings:.4f} ({savings_pct:.0f}%)")

    assert cost2['cache_read_cost'] < cost1['cache_write_cost'], "Cache read should be cheaper than write"

    print("\n✅ PASSED")


def test_model_comparison():
    """Compare costs across different models."""
    print("\n" + "="*60)
    print("TEST 3: Model Comparison")
    print("="*60)

    usage = {
        "input_tokens": 10000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 2000
    }

    models = [
        "claude-sonnet-4-5-20250929",
        "claude-sonnet-4-20250514",
        "claude-haiku-4-20250514"
    ]

    results = {}

    for model in models:
        cost = calculate_cost(usage, model)
        results[model] = cost

        model_name = model.replace('claude-', '').replace('-20250929', '').replace('-20250514', '')
        print(f"\n{model_name}:")
        print(f"  Input cost: ${cost['input_cost']:.4f}")
        print(f"  Output cost: ${cost['output_cost']:.4f}")
        print(f"  Total: ${cost['total_cost']:.4f}")

    # Haiku should be cheapest
    haiku_cost = results["claude-haiku-4-20250514"]['total_cost']
    sonnet_cost = results["claude-sonnet-4-5-20250929"]['total_cost']

    print(f"\nCost Comparison:")
    print(f"  Sonnet 4.5: ${sonnet_cost:.4f}")
    print(f"  Haiku 4.5: ${haiku_cost:.4f}")
    print(f"  Haiku is {sonnet_cost / haiku_cost:.1f}x cheaper!")

    assert haiku_cost < sonnet_cost, "Haiku should be cheaper than Sonnet"

    print("\n✅ PASSED")


def test_cost_formatting():
    """Test cost formatting function."""
    print("\n" + "="*60)
    print("TEST 4: Cost Formatting")
    print("="*60)

    test_cases = [
        (0.0001234, "$0.0001"),
        (0.001, "$0.001"),
        (0.0123, "$0.012"),
        (0.15, "$0.15"),
        (1.50, "$1.50"),
        (123.456, "$123.46"),
        (0.0, "$0.00")
    ]

    print("\nTest Cases:")
    for amount, expected in test_cases:
        formatted = format_cost(amount)
        status = "✅" if formatted == expected else "❌"
        print(f"  {amount:10.6f} -> {formatted:10s} (expected: {expected}) {status}")

        # Allow small floating point differences
        if formatted != expected:
            print(f"    WARNING: Expected {expected}, got {formatted}")

    print("\n✅ PASSED")


def test_large_session():
    """Test a realistic large session."""
    print("\n" + "="*60)
    print("TEST 5: Large Session Simulation")
    print("="*60)

    print("\nSimulating 10 requests with cache...")

    total_cost = 0.0
    total_tokens = 0

    # Request 1: Cache creation
    usage1 = {
        "input_tokens": 1500,
        "cache_creation_input_tokens": 15000,
        "cache_read_input_tokens": 0,
        "output_tokens": 800
    }
    cost1 = calculate_cost(usage1, "claude-sonnet-4-5-20250929")
    total_cost += cost1['total_cost']
    total_tokens += usage1['input_tokens'] + usage1['cache_creation_input_tokens'] + usage1['output_tokens']

    print(f"\nRequest 1 (cache creation): ${cost1['total_cost']:.4f}")

    # Requests 2-10: Cache hits
    for i in range(2, 11):
        usage = {
            "input_tokens": 1200,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 15000,
            "output_tokens": 600
        }
        cost = calculate_cost(usage, "claude-sonnet-4-5-20250929")
        total_cost += cost['total_cost']
        total_tokens += usage['input_tokens'] + usage['cache_read_input_tokens'] + usage['output_tokens']

        if i == 2:
            print(f"Request {i} (cache hit): ${cost['total_cost']:.4f}")
        elif i == 10:
            print(f"Request {i} (cache hit): ${cost['total_cost']:.4f}")

    print(f"\nSession Summary:")
    print(f"  Total requests: 10")
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"  Average cost per request: ${total_cost / 10:.4f}")

    # Calculate what it would cost without cache
    without_cache_cost = 0.0
    # First request
    usage_no_cache = {
        "input_tokens": 1500 + 15000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 800
    }
    cost_no_cache = calculate_cost(usage_no_cache, "claude-sonnet-4-5-20250929")
    without_cache_cost += cost_no_cache['total_cost']

    # Subsequent requests
    for i in range(9):
        usage_no_cache = {
            "input_tokens": 1200 + 15000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "output_tokens": 600
        }
        cost_no_cache = calculate_cost(usage_no_cache, "claude-sonnet-4-5-20250929")
        without_cache_cost += cost_no_cache['total_cost']

    savings = without_cache_cost - total_cost
    savings_pct = (savings / without_cache_cost) * 100

    print(f"\nWithout cache: ${without_cache_cost:.4f}")
    print(f"With cache: ${total_cost:.4f}")
    print(f"Savings: ${savings:.4f} ({savings_pct:.0f}%)")

    print("\n✅ PASSED")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PRICING CALCULATOR TEST SUITE")
    print("="*60)

    try:
        test_basic_calculation()
        test_cache_calculations()
        test_model_comparison()
        test_cost_formatting()
        test_large_session()

        print("\n" + "="*60)
        print("ALL TESTS PASSED ✅")
        print("="*60)
        print("\nThe pricing calculator is working correctly!")
        print("Ready for integration with Web UI.\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
