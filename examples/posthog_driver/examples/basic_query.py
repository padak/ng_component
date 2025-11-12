#!/usr/bin/env python3
"""
Basic PostHog Query Example

Demonstrates:
- Loading driver from environment
- Discovering available resources
- Simple event queries
- Accessing event properties
"""

from posthog_driver import PostHogDriver, PostHogError


def main():
    """Run basic query examples."""
    try:
        # Load driver from environment variables
        print("Connecting to PostHog...")
        driver = PostHogDriver.from_env()
        print("✓ Connected successfully\n")

        # Example 1: Discover available resources
        print("=" * 60)
        print("Example 1: Discover Available Resources")
        print("=" * 60)

        objects = driver.list_objects()
        print(f"Available resources: {', '.join(objects)}\n")

        # Example 2: Get schema for events
        print("=" * 60)
        print("Example 2: Get Events Schema")
        print("=" * 60)

        fields = driver.get_fields("events")
        print(f"Events has {len(fields)} fields:")
        for field_name, field_info in list(fields.items())[:10]:
            print(f"  - {field_name}: {field_info['type']}")
        print(f"  ... and {len(fields) - 10} more\n")

        # Example 3: Query recent events
        print("=" * 60)
        print("Example 3: Query Recent Events")
        print("=" * 60)

        query = """
            SELECT
                event,
                timestamp,
                distinct_id,
                properties.$current_url as url
            FROM events
            WHERE timestamp > now() - INTERVAL 24 HOUR
            ORDER BY timestamp DESC
            LIMIT 10
        """

        results = driver.read(query)
        print(f"Found {len(results)} recent events:")
        for i, event in enumerate(results, 1):
            print(f"\n{i}. Event: {event['event']}")
            print(f"   Time: {event['timestamp']}")
            print(f"   User: {event['distinct_id']}")
            if event.get('url'):
                print(f"   URL: {event['url']}")

        # Example 4: Count events by type
        print("\n" + "=" * 60)
        print("Example 4: Count Events by Type")
        print("=" * 60)

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

        results = driver.read(query)
        print(f"Top 10 events in last 7 days:")
        for i, row in enumerate(results, 1):
            print(f"{i:2d}. {row['event']:30s} {row['count']:>6,d} events")

        # Example 5: Check rate limit status
        print("\n" + "=" * 60)
        print("Example 5: Rate Limit Status")
        print("=" * 60)

        status = driver.get_rate_limit_status()
        print(f"Rate limit: {status['remaining']}/{status['limit']} remaining")
        print(f"Resets at: {status['reset_at']}")

    except PostHogError as e:
        print(f"\n❌ PostHog error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
