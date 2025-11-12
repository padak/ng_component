#!/usr/bin/env python3
"""
Pagination and Batching Example

Demonstrates:
- Using read_batched() for large datasets
- Manual pagination with LIMIT/OFFSET
- Processing data in chunks
- Memory-efficient data processing
"""

from posthog_driver import PostHogDriver, PostHogError
import time


def batch_processing_example(driver: PostHogDriver):
    """Process large dataset using read_batched()."""
    print(f"\n{'=' * 60}")
    print("Batch Processing with read_batched()")
    print('=' * 60)

    query = """
        SELECT
            event,
            timestamp,
            distinct_id,
            properties
        FROM events
        WHERE timestamp > now() - INTERVAL 7 DAY
    """

    print("\nProcessing events in batches of 1000...")
    print("Batch | Events | Time (s)")
    print("-" * 30)

    total_events = 0
    batch_count = 0
    start_time = time.time()

    try:
        for batch in driver.read_batched(query, batch_size=1000):
            batch_count += 1
            total_events += len(batch)
            elapsed = time.time() - start_time

            print(f"{batch_count:>5d} | {len(batch):>6,d} | {elapsed:>7.2f}")

            # Simulate processing
            # In real use case, you would process each event here
            # Example: save to database, aggregate metrics, etc.
            time.sleep(0.1)  # Simulate processing time

            # Optional: Check rate limits periodically
            if batch_count % 10 == 0:
                status = driver.get_rate_limit_status()
                if status['remaining'] < 50:
                    print(f"  ⚠ Rate limit warning: {status['remaining']} requests remaining")
                    time.sleep(2)  # Back off if approaching limit

    except PostHogError as e:
        print(f"\n❌ Error during batch processing: {e.message}")
        return

    total_time = time.time() - start_time
    print(f"\n✓ Processed {total_events:,} events in {batch_count} batches")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Events/sec: {total_events / total_time:,.0f}")


def manual_pagination_example(driver: PostHogDriver):
    """Demonstrate manual pagination with LIMIT/OFFSET."""
    print(f"\n{'=' * 60}")
    print("Manual Pagination with LIMIT/OFFSET")
    print('=' * 60)

    base_query = """
        SELECT
            event,
            timestamp,
            distinct_id
        FROM events
        WHERE timestamp > now() - INTERVAL 24 HOUR
    """

    page_size = 500
    offset = 0
    page = 1
    total_events = 0

    print(f"\nFetching {page_size} events per page...")
    print("Page | Events | Offset")
    print("-" * 30)

    while True:
        # Add LIMIT and OFFSET to query
        paginated_query = f"{base_query} LIMIT {page_size} OFFSET {offset}"

        try:
            results = driver.read(paginated_query)
        except PostHogError as e:
            print(f"\n❌ Error: {e.message}")
            break

        if not results:
            break  # No more results

        total_events += len(results)
        print(f"{page:>4d} | {len(results):>6,d} | {offset:>6,d}")

        # Process page
        # In real use case, process results here

        # Move to next page
        offset += page_size
        page += 1

        # Stop if we got fewer results than page_size (last page)
        if len(results) < page_size:
            break

    print(f"\n✓ Fetched {total_events:,} events across {page} pages")


def chunked_export_example(driver: PostHogDriver):
    """Export data in chunks with progress tracking."""
    print(f"\n{'=' * 60}")
    print("Chunked Data Export")
    print('=' * 60)

    query = """
        SELECT
            distinct_id,
            event,
            timestamp,
            properties.browser as browser,
            properties.$current_url as url
        FROM events
        WHERE timestamp > now() - INTERVAL 3 DAY
    """

    print("\nExporting events to CSV format...")

    # CSV header
    csv_lines = ["distinct_id,event,timestamp,browser,url"]

    chunk_size = 500
    total_exported = 0
    start_time = time.time()

    try:
        for batch in driver.read_batched(query, batch_size=chunk_size):
            # Convert batch to CSV lines
            for event in batch:
                # Escape commas and quotes in values
                distinct_id = str(event.get('distinct_id', '')).replace(',', ';')
                event_name = str(event.get('event', '')).replace(',', ';')
                timestamp = str(event.get('timestamp', ''))
                browser = str(event.get('browser', '')).replace(',', ';')
                url = str(event.get('url', '')).replace(',', ';')

                csv_line = f"{distinct_id},{event_name},{timestamp},{browser},{url}"
                csv_lines.append(csv_line)

            total_exported += len(batch)

            # Progress update every 5000 events
            if total_exported % 5000 == 0:
                elapsed = time.time() - start_time
                rate = total_exported / elapsed if elapsed > 0 else 0
                print(f"  Exported {total_exported:>6,d} events ({rate:>6,.0f} events/sec)")

    except PostHogError as e:
        print(f"\n❌ Export error: {e.message}")
        return

    # Save to file (in real use case)
    # with open('events_export.csv', 'w') as f:
    #     f.write('\n'.join(csv_lines))

    total_time = time.time() - start_time
    print(f"\n✓ Export complete:")
    print(f"  Total events: {total_exported:,}")
    print(f"  CSV lines: {len(csv_lines):,}")
    print(f"  Time: {total_time:.2f}s")
    print(f"  (File write skipped in demo)")


def streaming_aggregation_example(driver: PostHogDriver):
    """Aggregate data while streaming through batches."""
    print(f"\n{'=' * 60}")
    print("Streaming Aggregation")
    print('=' * 60)

    query = """
        SELECT
            event,
            distinct_id,
            properties.browser as browser
        FROM events
        WHERE timestamp > now() - INTERVAL 7 DAY
    """

    print("\nAggregating data while streaming...")

    # Aggregation state
    event_counts = {}
    user_counts = {}
    browser_counts = {}
    unique_users = set()

    batch_count = 0

    try:
        for batch in driver.read_batched(query, batch_size=1000):
            batch_count += 1

            # Aggregate as we stream
            for event in batch:
                # Count events
                event_name = event.get('event', 'unknown')
                event_counts[event_name] = event_counts.get(event_name, 0) + 1

                # Count unique users
                user_id = event.get('distinct_id')
                if user_id:
                    unique_users.add(user_id)
                    user_counts[user_id] = user_counts.get(user_id, 0) + 1

                # Count browsers
                browser = event.get('browser', 'unknown')
                browser_counts[browser] = browser_counts.get(browser, 0) + 1

            # Progress update
            if batch_count % 5 == 0:
                print(f"  Processed {batch_count} batches, {len(unique_users):,} unique users...")

    except PostHogError as e:
        print(f"\n❌ Aggregation error: {e.message}")
        return

    # Display results
    print(f"\n✓ Streaming aggregation complete:")
    print(f"  Batches processed: {batch_count}")
    print(f"  Total events: {sum(event_counts.values()):,}")
    print(f"  Unique users: {len(unique_users):,}")

    print(f"\nTop 10 Events:")
    for event, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {event:30s} {count:>6,d}")

    print(f"\nTop 5 Most Active Users:")
    for user, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {user:30s} {count:>6,d} events")

    print(f"\nBrowser Distribution:")
    for browser, count in sorted(browser_counts.items(), key=lambda x: x[1], reverse=True):
        if browser != 'unknown':
            print(f"  {browser:20s} {count:>6,d}")


def main():
    """Run pagination and batching examples."""
    try:
        print("Connecting to PostHog...")
        driver = PostHogDriver.from_env()
        print("✓ Connected successfully")

        # Run examples
        batch_processing_example(driver)
        manual_pagination_example(driver)
        chunked_export_example(driver)
        streaming_aggregation_example(driver)

        print("\n" + "=" * 60)
        print("All pagination examples complete")
        print("=" * 60)

    except PostHogError as e:
        print(f"\n❌ PostHog error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
