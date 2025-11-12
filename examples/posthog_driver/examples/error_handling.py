#!/usr/bin/env python3
"""
Error Handling Example

Demonstrates:
- Handling all PostHog exception types
- Graceful degradation
- Retry strategies
- Debug mode usage
"""

from posthog_driver import (
    PostHogDriver,
    PostHogError,
    AuthenticationError,
    ConnectionError,
    ObjectNotFoundError,
    QuerySyntaxError,
    RateLimitError,
    TimeoutError
)
import time
import os


def authentication_example():
    """Demonstrate authentication error handling."""
    print(f"\n{'=' * 60}")
    print("Example 1: Authentication Error Handling")
    print('=' * 60)

    try:
        # Try with invalid credentials
        driver = PostHogDriver(
            api_url="https://us.posthog.com",
            api_key="invalid_key",
            project_id="12345"
        )
        driver.list_objects()

    except AuthenticationError as e:
        print(f"✓ Caught AuthenticationError: {e.message}")
        print(f"  Details: {e.details}")
        print("\n  Recovery steps:")
        print("  1. Check POSTHOG_API_KEY environment variable")
        print("  2. Verify API key format (starts with phx_ or pheu_)")
        print("  3. Confirm key hasn't been revoked in PostHog settings")
        print("  4. Check POSTHOG_PROJECT_ID is correct")


def connection_example():
    """Demonstrate connection error handling."""
    print(f"\n{'=' * 60}")
    print("Example 2: Connection Error Handling")
    print('=' * 60)

    try:
        # Try with invalid URL
        driver = PostHogDriver(
            api_url="https://invalid-posthog-url.example.com",
            api_key="phx_test_key",
            project_id="12345",
            timeout=5
        )

    except ConnectionError as e:
        print(f"✓ Caught ConnectionError: {e.message}")
        print(f"  Details: {e.details}")
        print("\n  Recovery steps:")
        print("  1. Check POSTHOG_API_URL or POSTHOG_REGION setting")
        print("  2. Verify network connectivity")
        print("  3. Check firewall allows HTTPS (port 443)")
        print("  4. Try increasing timeout parameter")


def object_not_found_example():
    """Demonstrate object not found error handling."""
    print(f"\n{'=' * 60}")
    print("Example 3: Object Not Found Error Handling")
    print('=' * 60)

    try:
        driver = PostHogDriver.from_env()

        # Try to get fields for non-existent object
        driver.get_fields("invalid_object")

    except ObjectNotFoundError as e:
        print(f"✓ Caught ObjectNotFoundError: {e.message}")

        # Check for suggestions
        suggestions = e.details.get('suggestions', [])
        if suggestions:
            print(f"  Did you mean: {', '.join(suggestions)}?")

        # Recover by listing available objects
        print("\n  Recovery: Listing available objects...")
        driver = PostHogDriver.from_env()
        objects = driver.list_objects()
        print(f"  Available: {', '.join(objects)}")


def query_syntax_example():
    """Demonstrate query syntax error handling."""
    print(f"\n{'=' * 60}")
    print("Example 4: Query Syntax Error Handling")
    print('=' * 60)

    try:
        driver = PostHogDriver.from_env()

        # Try invalid HogQL query
        invalid_query = "SELECT FROM events"  # Missing column list
        driver.read(invalid_query)

    except QuerySyntaxError as e:
        print(f"✓ Caught QuerySyntaxError: {e.message}")
        print(f"  Query: {e.details.get('query', 'N/A')}")

        if 'position' in e.details:
            print(f"  Error at position: {e.details['position']}")

        print("\n  Recovery: Using correct syntax...")
        driver = PostHogDriver.from_env()
        correct_query = "SELECT event, timestamp FROM events LIMIT 5"
        results = driver.read(correct_query)
        print(f"  ✓ Query succeeded, got {len(results)} results")


def rate_limit_example():
    """Demonstrate rate limit handling."""
    print(f"\n{'=' * 60}")
    print("Example 5: Rate Limit Handling")
    print('=' * 60)

    try:
        driver = PostHogDriver.from_env(max_retries=2)

        # Check current rate limit status
        status = driver.get_rate_limit_status()
        print(f"Current rate limit: {status['remaining']}/{status['limit']}")

        # Simulate rate limit (would require many rapid requests in production)
        print("\nNote: Rate limit errors are automatically retried with exponential backoff")
        print("The driver will retry up to max_retries times before raising RateLimitError")

        # In production, if you hit rate limit:
        if status['remaining'] < 10:
            print("\n⚠ Approaching rate limit!")
            print(f"  Remaining: {status['remaining']}")
            print(f"  Resets at: {status['reset_at']}")
            print("  Waiting before continuing...")
            time.sleep(5)

    except RateLimitError as e:
        print(f"✓ Caught RateLimitError: {e.message}")
        retry_after = e.details.get('retry_after', 60)
        print(f"  Retry after: {retry_after} seconds")
        print(f"  Rate limit: {e.details.get('limit')} requests/minute")

        print("\n  Recovery strategies:")
        print(f"  1. Wait {retry_after} seconds and retry")
        print("  2. Reduce query frequency")
        print("  3. Use smaller batch sizes")
        print("  4. Increase max_retries parameter")


def timeout_example():
    """Demonstrate timeout error handling."""
    print(f"\n{'=' * 60}")
    print("Example 6: Timeout Error Handling")
    print('=' * 60)

    try:
        # Use very short timeout to demonstrate
        driver = PostHogDriver.from_env(timeout=1)

        # Try a potentially slow query
        query = """
            SELECT *
            FROM events
            WHERE timestamp > now() - INTERVAL 365 DAY
            LIMIT 100000
        """
        driver.read(query)

    except TimeoutError as e:
        print(f"✓ Caught TimeoutError: {e.message}")
        print(f"  Details: {e.details}")

        print("\n  Recovery strategies:")
        print("  1. Increase timeout parameter")
        print("  2. Reduce time range in WHERE clause")
        print("  3. Add more filters to reduce result set")
        print("  4. Use smaller LIMIT")
        print("  5. Break query into smaller time windows")

        print("\n  Recovering with optimized query...")
        driver = PostHogDriver.from_env(timeout=30)
        optimized_query = """
            SELECT event, timestamp, distinct_id
            FROM events
            WHERE timestamp > now() - INTERVAL 1 DAY
            LIMIT 100
        """
        results = driver.read(optimized_query)
        print(f"  ✓ Optimized query succeeded, got {len(results)} results")


def retry_strategy_example():
    """Demonstrate custom retry strategy."""
    print(f"\n{'=' * 60}")
    print("Example 7: Custom Retry Strategy")
    print('=' * 60)

    def execute_with_retry(driver, query, max_attempts=3):
        """Execute query with custom retry logic."""
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"  Attempt {attempt}/{max_attempts}...")
                results = driver.read(query)
                print(f"  ✓ Success! Got {len(results)} results")
                return results

            except RateLimitError as e:
                retry_after = e.details.get('retry_after', 60)
                if attempt < max_attempts:
                    print(f"  ⚠ Rate limited, waiting {retry_after}s...")
                    time.sleep(retry_after)
                else:
                    print(f"  ❌ Max retries exceeded")
                    raise

            except TimeoutError as e:
                if attempt < max_attempts:
                    print(f"  ⚠ Timeout, retrying with longer timeout...")
                    driver = PostHogDriver.from_env(timeout=driver.timeout * 2)
                else:
                    print(f"  ❌ Max retries exceeded")
                    raise

            except QuerySyntaxError as e:
                print(f"  ❌ Query syntax error, cannot retry: {e.message}")
                raise

        return None

    try:
        driver = PostHogDriver.from_env()
        query = "SELECT event, timestamp FROM events LIMIT 10"
        execute_with_retry(driver, query)

    except PostHogError as e:
        print(f"\n❌ Query failed after all retries: {e.message}")


def debug_mode_example():
    """Demonstrate debug mode for troubleshooting."""
    print(f"\n{'=' * 60}")
    print("Example 8: Debug Mode")
    print('=' * 60)

    print("\nEnabling debug mode for detailed logging...")

    try:
        # Enable debug mode
        driver = PostHogDriver.from_env(debug=True)

        print("\n--- Debug output starts ---")
        # Simple query with debug output
        results = driver.read("SELECT event FROM events LIMIT 3")
        print("--- Debug output ends ---\n")

        print(f"✓ Query returned {len(results)} results")
        print("\nDebug mode shows:")
        print("  - API URLs being called")
        print("  - Request parameters")
        print("  - Response status codes")
        print("  - Rate limit headers")
        print("  - Error details")

    except PostHogError as e:
        print(f"Error in debug mode: {e.message}")


def comprehensive_error_handling():
    """Demonstrate comprehensive error handling in production code."""
    print(f"\n{'=' * 60}")
    print("Example 9: Comprehensive Production Error Handling")
    print('=' * 60)

    try:
        # Load driver with production settings
        driver = PostHogDriver.from_env(
            timeout=30,
            max_retries=3,
            debug=False
        )

        # Execute query with full error handling
        query = """
            SELECT
                event,
                count() as count
            FROM events
            WHERE timestamp > now() - INTERVAL 7 DAY
            GROUP BY event
            ORDER BY count DESC
            LIMIT 10
        """

        print("\nExecuting query with full error handling...")
        results = driver.read(query)

        print(f"✓ Success! Top events:")
        for row in results:
            print(f"  {row['event']:30s} {row['count']:>6,d}")

    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e.message}")
        print("   Action: Check API credentials in .env file")

    except ConnectionError as e:
        print(f"❌ Connection failed: {e.message}")
        print("   Action: Check network and API URL")

    except ObjectNotFoundError as e:
        print(f"❌ Object not found: {e.message}")
        suggestions = e.details.get('suggestions', [])
        if suggestions:
            print(f"   Suggestions: {', '.join(suggestions)}")

    except QuerySyntaxError as e:
        print(f"❌ Invalid query syntax: {e.message}")
        print(f"   Query: {e.details.get('query', 'N/A')}")
        print("   Action: Check HogQL syntax in README")

    except RateLimitError as e:
        print(f"❌ Rate limit exceeded: {e.message}")
        retry_after = e.details.get('retry_after', 60)
        print(f"   Action: Wait {retry_after}s and retry")

    except TimeoutError as e:
        print(f"❌ Query timeout: {e.message}")
        print("   Action: Reduce time range or increase timeout")

    except PostHogError as e:
        print(f"❌ PostHog error: {e.message}")
        print(f"   Details: {e.details}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("   Action: Check logs and report issue")


def main():
    """Run all error handling examples."""
    print("=" * 60)
    print("PostHog Driver Error Handling Examples")
    print("=" * 60)

    # Check if environment is configured
    if not os.getenv('POSTHOG_API_KEY'):
        print("\n⚠ Warning: POSTHOG_API_KEY not set")
        print("Some examples will demonstrate error conditions")
        print("Set up .env file for full functionality\n")

    # Run all examples
    authentication_example()
    connection_example()

    # Only run these if we have valid credentials
    if os.getenv('POSTHOG_API_KEY'):
        object_not_found_example()
        query_syntax_example()
        rate_limit_example()
        timeout_example()
        retry_strategy_example()
        debug_mode_example()
        comprehensive_error_handling()
    else:
        print("\n(Skipping remaining examples - configure .env first)")

    print("\n" + "=" * 60)
    print("Error Handling Examples Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
