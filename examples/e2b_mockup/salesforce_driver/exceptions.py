"""
Custom exceptions for Salesforce client operations.

This module defines specific exception types for different error scenarios
when interacting with the Salesforce API.
"""


class SalesforceError(Exception):
    """
    Base exception for all Salesforce client errors.

    All other exceptions inherit from this base class, allowing you to catch
    all Salesforce-related errors with a single except clause.

    Example:
        try:
            client.query("SELECT Id FROM Lead")
        except SalesforceError as e:
            print(f"Salesforce error occurred: {e}")
    """
    pass


class ConnectionError(SalesforceError):
    """
    Raised when unable to connect to the Salesforce API.

    This exception is raised when:
    - The API server is not reachable
    - Network connectivity issues occur
    - Request timeout is exceeded
    - DNS resolution fails

    Example:
        try:
            client = SalesforceClient(api_url="http://invalid-host:8000")
            client.list_objects()
        except ConnectionError as e:
            print(f"Cannot connect to API: {e}")
            print("Check if the API server is running")
    """
    pass


class AuthError(SalesforceError):
    """
    Raised when authentication fails.

    This exception is raised when:
    - No API key is provided
    - API key is invalid or expired
    - Authentication request returns 401 Unauthorized

    Example:
        try:
            client = SalesforceClient(api_key="invalid-key")
            client.list_objects()
        except AuthError as e:
            print(f"Authentication failed: {e}")
            print("Check your SF_API_KEY environment variable")
    """
    pass


class ObjectNotFoundError(SalesforceError):
    """
    Raised when a requested Salesforce object is not found.

    This exception is raised when:
    - Querying or describing a non-existent object
    - Object name is misspelled
    - Object is not available in the current instance

    Example:
        try:
            fields = client.get_fields('InvalidObject')
        except ObjectNotFoundError as e:
            print(f"Object not found: {e}")
            available = client.list_objects()
            print(f"Available objects: {available}")
    """
    pass


class QueryError(SalesforceError):
    """
    Raised when a SOQL query fails to execute.

    This exception is raised when:
    - SOQL syntax is invalid
    - Referenced fields don't exist
    - Query timeout occurs
    - Query is too complex

    Example:
        try:
            leads = client.query("INVALID QUERY SYNTAX")
        except QueryError as e:
            print(f"Query failed: {e}")
            print("Check your SOQL syntax")
    """
    pass
