#!/usr/bin/env python3
"""
Aggregation and Analytics Example

Demonstrates:
- GROUP BY queries
- Aggregation functions (count, sum, avg)
- Time-based grouping
- Multi-dimensional analysis
"""

from posthog_driver import PostHogDriver, PostHogError


def daily_active_users(driver: PostHogDriver):
    """Calculate daily active users over the last 30 days."""
    print(f"\n{'=' * 60}")
    print("Daily Active Users (Last 30 Days)")
    print('=' * 60)

    query = """
        SELECT
            toDate(timestamp) as date,
            count(DISTINCT distinct_id) as dau
        FROM events
        WHERE timestamp > now() - INTERVAL 30 DAY
        GROUP BY date
        ORDER BY date DESC
    """

    results = driver.read(query)
    print(f"\nDate          DAU")
    print("-" * 25)
    for row in results:
        print(f"{row['date']}    {row['dau']:>6,d}")

    if results:
        avg_dau = sum(r['dau'] for r in results) / len(results)
        print(f"\nAverage DAU: {avg_dau:,.1f}")


def event_frequency(driver: PostHogDriver):
    """Analyze event frequency and distribution."""
    print(f"\n{'=' * 60}")
    print("Event Frequency Analysis")
    print('=' * 60)

    query = """
        SELECT
            event,
            count() as total_events,
            count(DISTINCT distinct_id) as unique_users,
            round(count() / count(DISTINCT distinct_id), 2) as avg_per_user
        FROM events
        WHERE timestamp > now() - INTERVAL 7 DAY
        GROUP BY event
        ORDER BY total_events DESC
        LIMIT 20
    """

    results = driver.read(query)
    print(f"\n{'Event':<30s} {'Total':>8s} {'Users':>8s} {'Avg/User':>10s}")
    print("-" * 60)
    for row in results:
        print(f"{row['event']:<30s} {row['total_events']:>8,d} {row['unique_users']:>8,d} {row['avg_per_user']:>10.2f}")


def hourly_activity(driver: PostHogDriver):
    """Analyze activity by hour of day."""
    print(f"\n{'=' * 60}")
    print("Activity by Hour of Day (Last 7 Days)")
    print('=' * 60)

    query = """
        SELECT
            toHour(timestamp) as hour,
            count() as event_count,
            count(DISTINCT distinct_id) as unique_users
        FROM events
        WHERE timestamp > now() - INTERVAL 7 DAY
        GROUP BY hour
        ORDER BY hour
    """

    results = driver.read(query)
    print(f"\n{'Hour':>4s}  {'Events':>8s}  {'Users':>8s}  Activity")
    print("-" * 50)

    max_events = max(r['event_count'] for r in results) if results else 1

    for row in results:
        hour = row['hour']
        events = row['event_count']
        users = row['unique_users']
        bar_length = int((events / max_events) * 30)
        bar = '█' * bar_length

        print(f"{hour:>4d}  {events:>8,d}  {users:>8,d}  {bar}")


def conversion_funnel(driver: PostHogDriver):
    """Analyze conversion funnel for key events."""
    print(f"\n{'=' * 60}")
    print("Conversion Funnel Analysis")
    print('=' * 60)

    query = """
        SELECT
            countIf(event = 'pageview') as pageviews,
            countIf(event = 'signup_viewed') as signup_views,
            countIf(event = 'signup_started') as signup_started,
            countIf(event = 'signup_completed') as signup_completed,
            count(DISTINCT if(event = 'pageview', distinct_id, NULL)) as total_visitors,
            count(DISTINCT if(event = 'signup_completed', distinct_id, NULL)) as converted_users
        FROM events
        WHERE timestamp > now() - INTERVAL 30 DAY
    """

    results = driver.read(query)
    if not results:
        print("No funnel data available")
        return

    data = results[0]

    # Calculate conversion rates
    funnel_steps = [
        ('Total Visitors', data['total_visitors'], 100.0),
        ('Pageviews', data['pageviews'], None),
        ('Signup Page Views', data['signup_views'], None),
        ('Signup Started', data['signup_started'], None),
        ('Signup Completed', data['signup_completed'], None),
        ('Converted Users', data['converted_users'], None),
    ]

    print(f"\n{'Step':<25s} {'Count':>10s}  {'Rate':>8s}  Dropoff")
    print("-" * 60)

    total_visitors = data['total_visitors']
    for step_name, count, rate in funnel_steps:
        if rate is None:
            rate = (count / total_visitors * 100) if total_visitors > 0 else 0

        bar_length = int(rate / 100 * 20)
        bar = '█' * bar_length + '░' * (20 - bar_length)

        print(f"{step_name:<25s} {count:>10,d}  {rate:>7.1f}%  {bar}")

    # Overall conversion rate
    if total_visitors > 0:
        conversion_rate = (data['converted_users'] / total_visitors) * 100
        print(f"\nOverall Conversion Rate: {conversion_rate:.2f}%")


def property_distribution(driver: PostHogDriver):
    """Analyze distribution of event properties."""
    print(f"\n{'=' * 60}")
    print("Property Distribution Analysis")
    print('=' * 60)

    # Browser distribution
    query = """
        SELECT
            properties.browser as browser,
            count() as event_count,
            count(DISTINCT distinct_id) as unique_users
        FROM events
        WHERE timestamp > now() - INTERVAL 7 DAY
          AND properties.browser IS NOT NULL
        GROUP BY browser
        ORDER BY event_count DESC
        LIMIT 10
    """

    results = driver.read(query)
    if results:
        print(f"\nBrowser Distribution:")
        print(f"{'Browser':<20s} {'Events':>10s} {'Users':>10s}")
        print("-" * 42)
        for row in results:
            browser = row['browser'] or 'Unknown'
            print(f"{browser:<20s} {row['event_count']:>10,d} {row['unique_users']:>10,d}")


def cohort_retention(driver: PostHogDriver):
    """Calculate user retention by cohort."""
    print(f"\n{'=' * 60}")
    print("Weekly Cohort Retention")
    print('=' * 60)

    query = """
        SELECT
            toMonday(min(timestamp)) as cohort_week,
            count(DISTINCT distinct_id) as cohort_size
        FROM events
        WHERE timestamp > now() - INTERVAL 60 DAY
        GROUP BY distinct_id
        HAVING cohort_week IS NOT NULL
        GROUP BY cohort_week
        ORDER BY cohort_week DESC
        LIMIT 8
    """

    results = driver.read(query)
    if results:
        print(f"\n{'Cohort Week':<15s} {'Size':>8s}")
        print("-" * 25)
        for row in results:
            print(f"{row['cohort_week']:<15s} {row['cohort_size']:>8,d}")


def main():
    """Run aggregation and analytics examples."""
    try:
        print("Connecting to PostHog...")
        driver = PostHogDriver.from_env()
        print("✓ Connected successfully")

        # Run all analysis examples
        daily_active_users(driver)
        event_frequency(driver)
        hourly_activity(driver)
        conversion_funnel(driver)
        property_distribution(driver)
        cohort_retention(driver)

        print("\n" + "=" * 60)
        print("Analysis Complete")
        print("=" * 60)

    except PostHogError as e:
        print(f"\n❌ PostHog error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
