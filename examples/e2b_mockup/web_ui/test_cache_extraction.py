"""
Test script to verify cache token extraction logic.

Tests both old SDK format (flat) and new SDK format (nested).
"""

from typing import Any


class MockUsageOldFormat:
    """Mock usage object in old SDK format (flat structure)."""
    def __init__(self):
        self.input_tokens = 1000
        self.output_tokens = 300
        self.cache_creation_input_tokens = 2000
        self.cache_read_input_tokens = 500


class MockCacheCreation:
    """Mock cache_creation object in new SDK format."""
    def __init__(self, ephemeral_5m: int = 0, ephemeral_1h: int = 0):
        self.ephemeral_5m_input_tokens = ephemeral_5m
        self.ephemeral_1h_input_tokens = ephemeral_1h


class MockUsageNewFormat:
    """Mock usage object in new SDK format (nested structure)."""
    def __init__(self, ephemeral_5m: int = 0, ephemeral_1h: int = 0):
        self.input_tokens = 1000
        self.output_tokens = 300
        self.cache_creation = MockCacheCreation(ephemeral_5m, ephemeral_1h)
        self.cache_read_input_tokens = 500


def extract_cache_tokens(usage: Any) -> tuple[int, int]:
    """
    Extract cache tokens from usage object (supports both old and new formats).

    Returns:
        tuple: (cache_creation, cache_read)
    """
    cache_creation = 0
    cache_read = 0

    # Try new SDK format first (nested cache_creation object)
    if hasattr(usage, 'cache_creation') and usage.cache_creation:
        cache_obj = usage.cache_creation

        # Try ephemeral_5m first (5-minute cache)
        ephemeral_5m = getattr(cache_obj, 'ephemeral_5m_input_tokens', 0) or 0
        # Try ephemeral_1h (1-hour cache)
        ephemeral_1h = getattr(cache_obj, 'ephemeral_1h_input_tokens', 0) or 0

        # Total cache creation is sum of both TTLs
        cache_creation = ephemeral_5m + ephemeral_1h

        print(f"  New SDK format detected:")
        print(f"    - ephemeral_5m_input_tokens: {ephemeral_5m}")
        print(f"    - ephemeral_1h_input_tokens: {ephemeral_1h}")

    # Fall back to old SDK format (flat structure)
    if cache_creation == 0:
        cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
        if cache_creation > 0:
            print(f"  Old SDK format detected:")
            print(f"    - cache_creation_input_tokens: {cache_creation}")

    # Cache read tokens (same in both formats)
    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0

    return cache_creation, cache_read


def test_old_format():
    """Test extraction with old SDK format."""
    print("\n" + "="*60)
    print("Test 1: Old SDK Format (flat structure)")
    print("="*60)

    usage = MockUsageOldFormat()
    cache_creation, cache_read = extract_cache_tokens(usage)

    print(f"\nResults:")
    print(f"  cache_creation: {cache_creation}")
    print(f"  cache_read: {cache_read}")

    assert cache_creation == 2000, f"Expected 2000, got {cache_creation}"
    assert cache_read == 500, f"Expected 500, got {cache_read}"
    print("\n✓ Test PASSED")


def test_new_format_5m_only():
    """Test extraction with new SDK format (5-minute cache only)."""
    print("\n" + "="*60)
    print("Test 2: New SDK Format (5-minute cache only)")
    print("="*60)

    usage = MockUsageNewFormat(ephemeral_5m=1500, ephemeral_1h=0)
    cache_creation, cache_read = extract_cache_tokens(usage)

    print(f"\nResults:")
    print(f"  cache_creation: {cache_creation}")
    print(f"  cache_read: {cache_read}")

    assert cache_creation == 1500, f"Expected 1500, got {cache_creation}"
    assert cache_read == 500, f"Expected 500, got {cache_read}"
    print("\n✓ Test PASSED")


def test_new_format_1h_only():
    """Test extraction with new SDK format (1-hour cache only)."""
    print("\n" + "="*60)
    print("Test 3: New SDK Format (1-hour cache only)")
    print("="*60)

    usage = MockUsageNewFormat(ephemeral_5m=0, ephemeral_1h=3000)
    cache_creation, cache_read = extract_cache_tokens(usage)

    print(f"\nResults:")
    print(f"  cache_creation: {cache_creation}")
    print(f"  cache_read: {cache_read}")

    assert cache_creation == 3000, f"Expected 3000, got {cache_creation}"
    assert cache_read == 500, f"Expected 500, got {cache_read}"
    print("\n✓ Test PASSED")


def test_new_format_mixed():
    """Test extraction with new SDK format (both 5m and 1h caches)."""
    print("\n" + "="*60)
    print("Test 4: New SDK Format (mixed 5m + 1h caches)")
    print("="*60)

    usage = MockUsageNewFormat(ephemeral_5m=1200, ephemeral_1h=800)
    cache_creation, cache_read = extract_cache_tokens(usage)

    print(f"\nResults:")
    print(f"  cache_creation: {cache_creation} (should be 1200 + 800 = 2000)")
    print(f"  cache_read: {cache_read}")

    assert cache_creation == 2000, f"Expected 2000, got {cache_creation}"
    assert cache_read == 500, f"Expected 500, got {cache_read}"
    print("\n✓ Test PASSED")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Cache Token Extraction Test Suite")
    print("="*60)

    test_old_format()
    test_new_format_5m_only()
    test_new_format_1h_only()
    test_new_format_mixed()

    print("\n" + "="*60)
    print("All tests PASSED! ✓")
    print("="*60)
    print("\nConclusion:")
    print("  - Old SDK format (flat) extraction: ✓ Working")
    print("  - New SDK format (nested) extraction: ✓ Working")
    print("  - Handles both 5-minute and 1-hour cache TTLs")
    print("  - Backward compatible with old SDK versions")
    print()
