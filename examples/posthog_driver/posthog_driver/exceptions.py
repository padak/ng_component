"""Exception hierarchy for PostHog driver."""

from typing import Optional, Dict, Any


class PostHogError(Exception):
    """Base exception for all PostHog driver errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"


class AuthenticationError(PostHogError):
    """
    Invalid API key or project ID.

    Agent should:
    - Check .env file has POSTHOG_API_KEY and POSTHOG_PROJECT_ID
    - Verify API key format (starts with phx_ or pheu_)
    - Confirm project ID is numeric
    """
    pass


class ConnectionError(PostHogError):
    """
    Cannot reach PostHog API.

    Agent should:
    - Check POSTHOG_API_URL or POSTHOG_REGION is correct
    - Verify network connectivity
    - Try again later if PostHog is down
    """
    pass


class ObjectNotFoundError(PostHogError):
    """
    Requested resource type doesn't exist.

    Agent should:
    - Call list_objects() to see available resources
    - Check spelling of resource name
    - Use suggestions from error details

    Example:
        ObjectNotFoundError(
            "Resource 'event' not found. Did you mean 'events'?",
            details={"requested": "event", "suggestions": ["events"]}
        )
    """
    pass


class QuerySyntaxError(PostHogError):
    """
    Invalid HogQL syntax.

    Agent should:
    - Check HogQL syntax in README.md
    - Verify table names (events, persons, etc.)
    - Fix query based on error message
    - Regenerate query

    Example:
        QuerySyntaxError(
            "HogQL syntax error: Expected field name after SELECT",
            details={"query": "SELECT FROM events", "position": 7}
        )
    """
    pass


class RateLimitError(PostHogError):
    """
    API rate limit exceeded (after automatic retries).

    PostHog rate limits:
    - Analytics queries: 240 requests/minute, 1,200/hour
    - CRUD operations: 480 requests/minute, 4,800/hour

    Driver automatically retries with exponential backoff.
    This exception is only raised after max_retries exhausted.

    Agent should:
    - Inform user of rate limit
    - Show retry_after seconds
    - Suggest reducing query frequency

    Example:
        RateLimitError(
            "API rate limit exceeded. Retry after 60 seconds.",
            details={
                "retry_after": 60,
                "limit": 240,
                "reset_at": "1699876543"
            }
        )
    """
    pass


class TimeoutError(PostHogError):
    """
    Request timed out.

    Agent should:
    - Inform user
    - Suggest increasing timeout parameter
    - Retry with smaller time range or LIMIT
    """
    pass
