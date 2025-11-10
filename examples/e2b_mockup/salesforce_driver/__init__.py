"""
Salesforce Mock Driver

A Python client library for interacting with the Salesforce Mock API.
Provides object discovery, field schema retrieval, and SOQL query execution.

Example:
    from salesforce_driver import SalesforceClient

    client = SalesforceClient(
        api_url="http://localhost:8000",
        api_key="your-api-key"
    )

    # List available objects
    objects = client.list_objects()

    # Get field schema
    fields = client.get_fields('Lead')

    # Execute SOQL query
    leads = client.query("SELECT Id, Name, Email FROM Lead")
"""

from .client import SalesforceClient
from .exceptions import (
    SalesforceError,
    ConnectionError,
    AuthError,
    ObjectNotFoundError,
    QueryError,
)

__version__ = "0.1.0"

__all__ = [
    'SalesforceClient',
    'SalesforceError',
    'ConnectionError',
    'AuthError',
    'ObjectNotFoundError',
    'QueryError'
]
