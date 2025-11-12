"""PostHog Driver for ng_component."""

__version__ = "1.0.0"

from .client import PostHogDriver
from .exceptions import (
    PostHogError,
    AuthenticationError,
    ConnectionError,
    ObjectNotFoundError,
    QuerySyntaxError,
    RateLimitError,
    TimeoutError
)

__all__ = [
    "PostHogDriver",
    "PostHogError",
    "AuthenticationError",
    "ConnectionError",
    "ObjectNotFoundError",
    "QuerySyntaxError",
    "RateLimitError",
    "TimeoutError"
]
