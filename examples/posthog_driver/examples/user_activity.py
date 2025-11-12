#!/usr/bin/env python3
"""
User Activity Analysis Example

Demonstrates:
- Tracking individual user behavior
- Time-based filtering
- Property access patterns
- Activity timeline queries
"""

from posthog_driver import PostHogDriver, PostHogError
from datetime import datetime


def analyze_user_activity(driver: PostHogDriver, user_id: str):
    """Analyze activity for a specific user."""
    print(f"\n{'=' * 60}")
    print(f"User Activity Analysis: {user_id}")
    print('=' * 60)

    # Query 1: User summary
    query = f"""
        SELECT
            distinct_id,
            count() as total_events,
            count(DISTINCT event) as unique_events,
            min(timestamp) as first_seen,
            max(timestamp) as last_seen
        FROM events
        WHERE distinct_id = '{user_id}'
        GROUP BY distinct_id
    """

    summary = driver.read(query)
    if not summary:
        print(f"No activity found for user: {user_id}")
        return

    s = summary[0]
    print(f"\nUser Summary:")
    print(f"  Total events: {s['total_events']:,}")
    print(f"  Unique event types: {s['unique_events']}")
    print(f"  First seen: {s['first_seen']}")
    print(f"  Last seen: {s['last_seen']}")

    # Query 2: Event breakdown
    query = f"""
        SELECT
            event,
            count() as count,
            max(timestamp) as last_occurrence
        FROM events
        WHERE distinct_id = '{user_id}'
        GROUP BY event
        ORDER BY count DESC
    """

    events = driver.read(query)
    print(f"\nEvent Breakdown:")
    for i, e in enumerate(events[:10], 1):
        print(f"  {i:2d}. {e['event']:30s} {e['count']:>4,d}x  (last: {e['last_occurrence']})")

    # Query 3: Recent activity timeline
    query = f"""
        SELECT
            event,
            timestamp,
            properties.$current_url as url,
            properties.browser as browser
        FROM events
        WHERE distinct_id = '{user_id}'
        ORDER BY timestamp DESC
        LIMIT 20
    """

    timeline = driver.read(query)
    print(f"\nRecent Activity Timeline (last 20 events):")
    for i, e in enumerate(timeline, 1):
        time_str = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n  {i:2d}. {time_str}")
        print(f"      Event: {e['event']}")
        if e.get('url'):
            print(f"      URL: {e['url']}")
        if e.get('browser'):
            print(f"      Browser: {e['browser']}")


def analyze_user_cohort(driver: PostHogDriver, min_events: int = 10):
    """Analyze most active users."""
    print(f"\n{'=' * 60}")
    print(f"Most Active Users (>{min_events} events)")
    print('=' * 60)

    query = f"""
        SELECT
            distinct_id,
            count() as event_count,
            count(DISTINCT event) as unique_events,
            max(timestamp) as last_seen
        FROM events
        WHERE timestamp > now() - INTERVAL 30 DAY
        GROUP BY distinct_id
        HAVING event_count > {min_events}
        ORDER BY event_count DESC
        LIMIT 20
    """

    users = driver.read(query)
    print(f"\nFound {len(users)} active users:")
    for i, user in enumerate(users, 1):
        print(f"{i:2d}. User: {user['distinct_id']:30s}")
        print(f"    Events: {user['event_count']:>5,d}  Unique: {user['unique_events']:>3,d}  Last: {user['last_seen']}")


def analyze_user_journey(driver: PostHogDriver, user_id: str):
    """Track user journey through key events."""
    print(f"\n{'=' * 60}")
    print(f"User Journey: {user_id}")
    print('=' * 60)

    # Key events to track
    key_events = [
        ('signup_viewed', 'Viewed signup page'),
        ('signup_started', 'Started signup'),
        ('signup_completed', 'Completed signup'),
        ('first_login', 'First login'),
        ('feature_used', 'Used a feature'),
        ('subscription_viewed', 'Viewed pricing'),
        ('subscription_started', 'Started subscription'),
    ]

    for event_name, description in key_events:
        query = f"""
            SELECT
                event,
                timestamp,
                properties
            FROM events
            WHERE distinct_id = '{user_id}'
              AND event = '{event_name}'
            ORDER BY timestamp
            LIMIT 1
        """

        results = driver.read(query)
        if results:
            timestamp = results[0]['timestamp']
            print(f"✓ {description:30s} {timestamp}")
        else:
            print(f"  {description:30s} (not yet)")


def main():
    """Run user activity analysis examples."""
    try:
        print("Connecting to PostHog...")
        driver = PostHogDriver.from_env()
        print("✓ Connected successfully")

        # Example 1: Get a sample user ID first
        query = """
            SELECT distinct_id
            FROM events
            WHERE timestamp > now() - INTERVAL 7 DAY
            GROUP BY distinct_id
            HAVING count() > 5
            LIMIT 1
        """

        sample_users = driver.read(query)
        if not sample_users:
            print("\n❌ No users with sufficient activity found in last 7 days")
            print("Try loading sample data or adjusting the time range")
            return

        sample_user_id = sample_users[0]['distinct_id']

        # Example 2: Analyze specific user
        analyze_user_activity(driver, sample_user_id)

        # Example 3: Analyze user cohort
        analyze_user_cohort(driver, min_events=5)

        # Example 4: User journey analysis
        analyze_user_journey(driver, sample_user_id)

    except PostHogError as e:
        print(f"\n❌ PostHog error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
