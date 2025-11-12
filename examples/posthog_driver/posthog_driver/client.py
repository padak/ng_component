"""PostHog driver implementation following ng_component BaseDriver contract."""

from typing import List, Dict, Any, Optional, Iterator
import requests
import os
import time
import difflib

from .exceptions import (
    PostHogError,
    AuthenticationError,
    ConnectionError,
    ObjectNotFoundError,
    QuerySyntaxError,
    RateLimitError,
    TimeoutError
)


class DriverCapabilities:
    """Driver capabilities dataclass."""
    def __init__(
        self,
        read: bool = True,
        write: bool = False,
        update: bool = False,
        delete: bool = False,
        batch_operations: bool = False,
        streaming: bool = False,
        pagination_style: str = "OFFSET",
        query_language: Optional[str] = None,
        max_page_size: Optional[int] = None,
        supports_transactions: bool = False,
        supports_relationships: bool = False
    ):
        self.read = read
        self.write = write
        self.update = update
        self.delete = delete
        self.batch_operations = batch_operations
        self.streaming = streaming
        self.pagination_style = pagination_style
        self.query_language = query_language
        self.max_page_size = max_page_size
        self.supports_transactions = supports_transactions
        self.supports_relationships = supports_relationships


class PostHogDriver:
    """
    PostHog analytics driver using HogQL query language.

    PostHog is a product analytics platform that tracks user behavior
    through events (actions users take) and persons (user profiles).

    Features:
    - HogQL query execution (SQL-like analytics queries)
    - Event and person discovery
    - Automatic rate limiting and retry
    - Region-aware (US/EU endpoints)

    Example:
        >>> client = PostHogDriver.from_env()
        >>>
        >>> # Discover what data exists
        >>> resources = client.list_objects()
        >>> # Returns: ["events", "persons", "cohorts", "insights", ...]
        >>>
        >>> # Get event schema
        >>> fields = client.get_fields("events")
        >>>
        >>> # Query events
        >>> results = client.read('''
        ...     SELECT event, count() as total
        ...     FROM events
        ...     WHERE timestamp >= now() - INTERVAL 7 DAY
        ...     GROUP BY event
        ...     ORDER BY total DESC
        ...     LIMIT 10
        ... ''')
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        project_id: str,
        timeout: int = 30,
        max_retries: int = 3,
        debug: bool = False,
        **kwargs
    ):
        """
        Initialize PostHog driver.

        Args:
            api_url: PostHog API base URL (e.g., https://us.posthog.com)
            api_key: Personal API key (starts with phx_ or pheu_)
            project_id: PostHog project ID (numeric)
            timeout: Request timeout in seconds
            max_retries: Retry attempts for rate limiting
            debug: Enable debug logging

        Raises:
            AuthenticationError: If credentials are invalid
            ConnectionError: If cannot connect to PostHog
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.project_id = project_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.debug = debug

        # Create HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })

        # Store rate limit info
        self._last_rate_limit = {}

        # Validate connection at init time (fail fast!)
        self._validate_connection()

    @classmethod
    def from_env(cls, **kwargs) -> 'PostHogDriver':
        """
        Create driver from environment variables.

        Required env vars:
        - POSTHOG_API_KEY: Personal API key (phx_ or pheu_ prefix)
        - POSTHOG_PROJECT_ID: Project ID (numeric)
        - POSTHOG_REGION: 'US' or 'EU' (or use POSTHOG_API_URL)

        Alternative:
        - POSTHOG_API_URL: Full API URL (instead of region)

        Example:
            >>> # Set in .env:
            >>> # POSTHOG_REGION=US
            >>> # POSTHOG_API_KEY=phx_abc123...
            >>> # POSTHOG_PROJECT_ID=12345
            >>>
            >>> client = PostHogDriver.from_env()

        Returns:
            PostHogDriver instance

        Raises:
            AuthenticationError: If required env vars missing or invalid
        """
        api_key = os.environ.get("POSTHOG_API_KEY")
        project_id = os.environ.get("POSTHOG_PROJECT_ID")

        # Get URL from region or explicit URL
        region = os.environ.get("POSTHOG_REGION", "US").upper()
        api_url = os.environ.get("POSTHOG_API_URL")

        if not api_url:
            if region == "US":
                api_url = "https://us.posthog.com"
            elif region == "EU":
                api_url = "https://eu.posthog.com"
            else:
                raise AuthenticationError(
                    f"Invalid region '{region}'. Must be 'US' or 'EU'",
                    details={"valid_regions": ["US", "EU"]}
                )

        if not api_key or not project_id:
            raise AuthenticationError(
                "Missing PostHog credentials. Set POSTHOG_API_KEY and POSTHOG_PROJECT_ID environment variables.",
                details={
                    "required_env_vars": ["POSTHOG_API_KEY", "POSTHOG_PROJECT_ID"],
                    "optional_env_vars": ["POSTHOG_REGION or POSTHOG_API_URL"]
                }
            )

        return cls(
            api_url=api_url,
            api_key=api_key,
            project_id=project_id,
            **kwargs
        )

    def get_capabilities(self) -> DriverCapabilities:
        """
        Return PostHog driver capabilities.

        Returns:
            DriverCapabilities with feature flags

        Example:
            >>> caps = client.get_capabilities()
            >>> if caps.read:
            ...     print("Can query data")
            >>> if caps.query_language:
            ...     print(f"Query language: {caps.query_language}")
        """
        return DriverCapabilities(
            read=True,                          # Can query analytics data
            write=False,                        # No write through analytics API
            update=False,
            delete=False,
            batch_operations=False,
            streaming=False,
            pagination_style="OFFSET",          # HogQL supports LIMIT/OFFSET
            query_language="HogQL",             # SQL-like query language
            max_page_size=10000,                # PostHog recommendation
            supports_transactions=False,
            supports_relationships=True         # Can JOIN events, persons, etc.
        )

    # ===== DISCOVERY METHODS (REQUIRED) =====

    def list_objects(self) -> List[str]:
        """
        Discover available PostHog resources.

        Returns:
            List of resource types that can be queried:
            - "events": User action events ($pageview, custom events)
            - "persons": User profiles with properties
            - "cohorts": User segments
            - "insights": Saved analytics queries
            - "event_definitions": Event metadata (descriptions, tags)
            - "property_definitions": Property metadata

        Example:
            >>> resources = client.list_objects()
            >>> print(resources)
            ['events', 'persons', 'cohorts', 'insights', 'event_definitions', 'property_definitions']
        """
        return [
            "events",
            "persons",
            "cohorts",
            "insights",
            "event_definitions",
            "property_definitions"
        ]

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """
        Get schema for a PostHog resource.

        Args:
            object_name: Resource type (e.g., "events", "persons")

        Returns:
            Dictionary with field definitions:
            {
                "field_name": {
                    "type": "string|integer|datetime|json|...",
                    "label": "Human Readable Name",
                    "description": "Field description",
                    "required": bool,
                    "nullable": bool
                }
            }

        Raises:
            ObjectNotFoundError: If resource type doesn't exist

        Example:
            >>> fields = client.get_fields("events")
            >>> print(fields.keys())
            dict_keys(['event', 'distinct_id', 'timestamp', 'properties', 'person'])
            >>>
            >>> print(fields['event'])
            {
                'type': 'string',
                'label': 'Event Name',
                'description': 'Name of the event (e.g., $pageview, signup_completed)',
                'required': True,
                'nullable': False
            }
        """
        schemas = {
            "events": {
                "event": {
                    "type": "string",
                    "label": "Event Name",
                    "description": "Name of the event (e.g., $pageview, signup_completed)",
                    "required": True,
                    "nullable": False
                },
                "distinct_id": {
                    "type": "string",
                    "label": "Distinct ID",
                    "description": "Unique identifier for the user who triggered the event",
                    "required": True,
                    "nullable": False
                },
                "timestamp": {
                    "type": "datetime",
                    "label": "Timestamp",
                    "description": "When the event occurred (ISO 8601 format)",
                    "required": True,
                    "nullable": False
                },
                "properties": {
                    "type": "json",
                    "label": "Event Properties",
                    "description": "JSON object with event properties (access via properties.$browser, properties.$current_url)",
                    "required": False,
                    "nullable": True
                },
                "person": {
                    "type": "reference",
                    "label": "Person",
                    "description": "Link to person who triggered event (JOIN via person.properties.$email)",
                    "references": "persons",
                    "required": False,
                    "nullable": True
                }
            },
            "persons": {
                "id": {
                    "type": "string",
                    "label": "Person ID",
                    "description": "Unique identifier for this person",
                    "required": True,
                    "nullable": False
                },
                "distinct_ids": {
                    "type": "array",
                    "label": "Distinct IDs",
                    "description": "List of distinct_ids associated with this person",
                    "required": True,
                    "nullable": False
                },
                "properties": {
                    "type": "json",
                    "label": "Person Properties",
                    "description": "JSON object with person properties (access via properties.$email, properties.$name)",
                    "required": False,
                    "nullable": True
                },
                "created_at": {
                    "type": "datetime",
                    "label": "Created At",
                    "description": "When this person was first seen",
                    "required": True,
                    "nullable": False
                }
            },
            "cohorts": {
                "id": {
                    "type": "integer",
                    "label": "Cohort ID",
                    "description": "Unique identifier for this cohort",
                    "required": True,
                    "nullable": False
                },
                "name": {
                    "type": "string",
                    "label": "Cohort Name",
                    "description": "Human-readable cohort name",
                    "required": True,
                    "nullable": False
                },
                "description": {
                    "type": "string",
                    "label": "Description",
                    "description": "Cohort description",
                    "required": False,
                    "nullable": True
                },
                "filters": {
                    "type": "json",
                    "label": "Cohort Filters",
                    "description": "Filter definition for cohort membership",
                    "required": True,
                    "nullable": False
                }
            },
            "insights": {
                "id": {
                    "type": "integer",
                    "label": "Insight ID",
                    "description": "Unique identifier for this insight",
                    "required": True,
                    "nullable": False
                },
                "name": {
                    "type": "string",
                    "label": "Insight Name",
                    "description": "Human-readable insight name",
                    "required": True,
                    "nullable": False
                },
                "query": {
                    "type": "json",
                    "label": "Query Definition",
                    "description": "HogQL or insight query definition",
                    "required": True,
                    "nullable": False
                },
                "result": {
                    "type": "json",
                    "label": "Cached Results",
                    "description": "Cached query results",
                    "required": False,
                    "nullable": True
                }
            },
            "event_definitions": {
                "name": {
                    "type": "string",
                    "label": "Event Name",
                    "description": "Name of the event",
                    "required": True,
                    "nullable": False
                },
                "description": {
                    "type": "string",
                    "label": "Description",
                    "description": "Event description for documentation",
                    "required": False,
                    "nullable": True
                },
                "tags": {
                    "type": "array",
                    "label": "Tags",
                    "description": "Tags for categorization",
                    "required": False,
                    "nullable": True
                },
                "volume_30_day": {
                    "type": "integer",
                    "label": "30-Day Volume",
                    "description": "Event count in last 30 days",
                    "required": False,
                    "nullable": True
                }
            },
            "property_definitions": {
                "name": {
                    "type": "string",
                    "label": "Property Name",
                    "description": "Name of the property (e.g., $browser, $current_url)",
                    "required": True,
                    "nullable": False
                },
                "type": {
                    "type": "string",
                    "label": "Property Type",
                    "description": "Type: 'event' or 'person' property",
                    "required": True,
                    "nullable": False
                },
                "description": {
                    "type": "string",
                    "label": "Description",
                    "description": "Property description for documentation",
                    "required": False,
                    "nullable": True
                }
            }
        }

        if object_name not in schemas:
            available = list(schemas.keys())
            suggestions = self._fuzzy_match(object_name, available)

            raise ObjectNotFoundError(
                f"Resource '{object_name}' not found. Available: {', '.join(available)}",
                details={
                    "requested": object_name,
                    "available": available,
                    "suggestions": suggestions
                }
            )

        return schemas[object_name]

    # ===== READ OPERATIONS (REQUIRED) =====

    def read(
        self,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute HogQL query against PostHog data.

        HogQL is SQL-like with analytics functions:
        - SELECT, FROM, WHERE, GROUP BY, ORDER BY, LIMIT
        - Functions: count(), count(DISTINCT x), sum(), avg(), min(), max()
        - Time: now(), INTERVAL, toDate(), toHour(), toDayOfWeek()
        - Properties: properties.$browser, person.properties.$email
        - Joins: events JOIN persons ON events.person_id = persons.id

        Args:
            query: HogQL query string
            limit: Max records (appended as LIMIT clause if not in query)
            offset: Skip records (appended as OFFSET clause if not in query)

        Returns:
            List of result rows as dictionaries

        Raises:
            QuerySyntaxError: Invalid HogQL syntax
            RateLimitError: API rate limit exceeded (240 req/min analytics)
            TimeoutError: Query timed out

        Example:
            >>> # Simple query
            >>> results = client.read('''
            ...     SELECT event, count() as total
            ...     FROM events
            ...     WHERE timestamp >= now() - INTERVAL 7 DAY
            ...     GROUP BY event
            ...     ORDER BY total DESC
            ...     LIMIT 10
            ... ''')
            >>> print(results[0])
            {'event': '$pageview', 'total': 1523}
            >>>
            >>> # Query with person properties
            >>> results = client.read('''
            ...     SELECT
            ...         person.properties.$email as email,
            ...         count() as event_count
            ...     FROM events
            ...     WHERE event = 'signup_completed'
            ...     AND timestamp >= now() - INTERVAL 30 DAY
            ...     GROUP BY email
            ...     LIMIT 100
            ... ''')
        """
        # Add LIMIT/OFFSET if provided and not already in query
        query_upper = query.upper()
        if limit and 'LIMIT' not in query_upper:
            query = f"{query.rstrip(';')} LIMIT {limit}"
        if offset and 'OFFSET' not in query_upper:
            query = f"{query.rstrip(';')} OFFSET {offset}"

        # Execute query via PostHog /query endpoint
        try:
            response = self._api_call(
                f"/api/projects/{self.project_id}/query/",
                method="POST",
                json={"query": {"kind": "HogQLQuery", "query": query}}
            )
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                error_detail = e.response.json()
                raise QuerySyntaxError(
                    f"HogQL syntax error: {error_detail.get('detail', 'Unknown error')}",
                    details={"query": query, "error": error_detail}
                )
            raise

        # Parse results
        return self._parse_query_results(response)

    def read_batched(
        self,
        query: str,
        batch_size: int = 1000
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Execute HogQL query and yield results in batches (memory-efficient).

        Uses LIMIT/OFFSET pagination for large result sets.

        Args:
            query: HogQL query string
            batch_size: Records per batch (default 1000)

        Yields:
            Batches of records as lists of dictionaries

        Example:
            >>> total = 0
            >>> for batch in client.read_batched("SELECT * FROM events WHERE timestamp >= now() - INTERVAL 30 DAY", batch_size=1000):
            ...     process_batch(batch)
            ...     total += len(batch)
            ...     print(f"Processed {total} events...")
            >>>
            >>> print(f"Done! Total: {total} events")
        """
        offset = 0
        while True:
            batch = self.read(query, limit=batch_size, offset=offset)
            if not batch:
                break

            yield batch
            offset += batch_size

            if len(batch) < batch_size:
                break  # Last batch (fewer records than batch_size)

    # ===== UTILITY METHODS =====

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current API rate limit status from last response.

        PostHog rate limits:
        - Analytics queries: 240 req/min, 1,200 req/hour
        - CRUD operations: 480 req/min, 4,800 req/hour

        Returns:
            {
                "remaining": int or None,
                "limit": int or None,
                "reset_at": str or None (Unix timestamp)
            }

        Example:
            >>> status = client.get_rate_limit_status()
            >>> if status["remaining"] and int(status["remaining"]) < 10:
            ...     print("Warning: Approaching rate limit!")
            ...     print(f"Limit resets at: {status['reset_at']}")
        """
        return self._last_rate_limit or {
            "remaining": None,
            "limit": None,
            "reset_at": None
        }

    def close(self):
        """
        Close HTTP session and cleanup resources.

        Example:
            >>> client = PostHogDriver.from_env()
            >>> try:
            ...     results = client.read("SELECT * FROM events LIMIT 10")
            ... finally:
            ...     client.close()
        """
        if self.session:
            self.session.close()

    # ===== INTERNAL HELPERS =====

    def _validate_connection(self):
        """
        Validate credentials at initialization (fail fast).

        Makes a test API call to verify:
        - API key is valid
        - Project ID exists and user has access
        - Network connectivity

        Raises:
            AuthenticationError: Invalid credentials or no project access
            ConnectionError: Cannot reach PostHog API
        """
        try:
            # Test connection with project info endpoint
            self._api_call(f"/api/projects/{self.project_id}/")
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(
                    "Invalid PostHog API key. Check your credentials.",
                    details={"api_url": self.api_url}
                )
            elif e.response.status_code == 404:
                raise AuthenticationError(
                    f"Project ID '{self.project_id}' not found or no access. Check POSTHOG_PROJECT_ID.",
                    details={"project_id": self.project_id}
                )
            raise
        except requests.RequestException as e:
            raise ConnectionError(
                f"Cannot connect to PostHog at {self.api_url}: {e}"
            )

    def _api_call(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make API call with automatic retry on rate limits.

        Implements exponential backoff for 429 errors.

        Args:
            endpoint: API endpoint path (e.g., "/api/projects/123/query/")
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments for requests.request()

        Returns:
            Response JSON as dictionary

        Raises:
            RateLimitError: Rate limit exceeded after max retries
            HTTPError: Other HTTP errors
        """
        url = f"{self.api_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                if self.debug:
                    print(f"[DEBUG] {method} {url}")

                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs
                )

                # Store rate limit headers for get_rate_limit_status()
                self._last_rate_limit = {
                    "remaining": response.headers.get("X-RateLimit-Remaining"),
                    "limit": response.headers.get("X-RateLimit-Limit"),
                    "reset_at": response.headers.get("X-RateLimit-Reset")
                }

                response.raise_for_status()
                return response.json()

            except requests.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limited - retry with exponential backoff
                    retry_after = int(e.response.headers.get("Retry-After", 2 ** attempt))

                    if attempt < self.max_retries - 1:
                        if self.debug:
                            print(f"[DEBUG] Rate limited. Retrying in {retry_after}s (attempt {attempt + 1}/{self.max_retries})...")
                        time.sleep(retry_after)
                        continue
                    else:
                        # Exhausted retries
                        raise RateLimitError(
                            f"API rate limit exceeded after {self.max_retries} attempts. Retry after {retry_after} seconds.",
                            details={
                                "retry_after": retry_after,
                                "limit": self._last_rate_limit.get("limit"),
                                "reset_at": self._last_rate_limit.get("reset_at"),
                                "attempts": self.max_retries
                            }
                        )

                # Other HTTP errors - don't retry
                raise

            except requests.Timeout:
                raise TimeoutError(
                    f"Request timed out after {self.timeout} seconds",
                    details={"timeout": self.timeout}
                )

    def _parse_query_results(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse PostHog query API response into list of dicts.

        PostHog returns:
        {
            "results": [[val1, val2], [val1, val2], ...],
            "columns": ["col1", "col2"],
            "types": ["String", "UInt64"]
        }

        We convert to:
        [
            {"col1": val1, "col2": val2},
            {"col1": val1, "col2": val2}
        ]

        Args:
            response: Raw API response dictionary

        Returns:
            List of dictionaries (one per row)
        """
        results = response.get("results", [])
        columns = response.get("columns", [])

        # Convert array format to dict format
        return [
            dict(zip(columns, row))
            for row in results
        ]

    def _fuzzy_match(self, query: str, options: List[str], n: int = 3) -> List[str]:
        """
        Fuzzy match query against options for suggestions.

        Args:
            query: User's input
            options: Valid options
            n: Number of suggestions to return

        Returns:
            List of close matches
        """
        return difflib.get_close_matches(query, options, n=n, cutoff=0.6)
