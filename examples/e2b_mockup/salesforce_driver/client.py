"""
Salesforce Mock API Client

This module provides a Python client for interacting with the Salesforce Mock API.
It supports object discovery, field schema retrieval, and SOQL query execution.
"""

import os
from typing import List, Dict, Any, Optional
import requests
from requests.exceptions import RequestException, Timeout
from requests.exceptions import ConnectionError as RequestsConnectionError

from .exceptions import (
    SalesforceError,
    ConnectionError,
    AuthError,
    ObjectNotFoundError,
    QueryError,
)


class SalesforceClient:
    """
    Client for interacting with Salesforce Mock API.

    This client provides methods to discover objects, retrieve field schemas,
    and execute SOQL queries against a mock Salesforce API.

    Example:
        client = SalesforceClient()
        objects = client.list_objects()
        leads = client.query("SELECT Id, Name, Email FROM Lead LIMIT 10")
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the Salesforce client.

        Args:
            api_url: Base URL for the Salesforce API. Defaults to http://localhost:8000
            api_key: API key for authentication. Defaults to SF_API_KEY env variable
            timeout: Request timeout in seconds. Defaults to 30

        Raises:
            AuthError: If no API key is provided
        """
        self.api_url = api_url or os.getenv("SF_API_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("SF_API_KEY")
        self.timeout = timeout

        if not self.api_key:
            raise AuthError(
                "API key is required. Set SF_API_KEY environment variable or pass api_key parameter."
            )

        # Remove trailing slash from API URL
        self.api_url = self.api_url.rstrip('/')

        # Setup session with default headers
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the Salesforce API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/objects')
            **kwargs: Additional arguments to pass to requests

        Returns:
            JSON response as a dictionary

        Raises:
            ConnectionError: If unable to connect to the API
            AuthError: If authentication fails (401)
            SalesforceError: For other API errors
        """
        url = f"{self.api_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )

            # Handle authentication errors
            if response.status_code == 401:
                raise AuthError(
                    f"Authentication failed. Check your API key. Response: {response.text}"
                )

            # Handle not found errors
            if response.status_code == 404:
                raise ObjectNotFoundError(
                    f"Resource not found: {endpoint}. Response: {response.text}"
                )

            # Handle other errors
            if not response.ok:
                raise SalesforceError(
                    f"API request failed with status {response.status_code}: {response.text}"
                )

            return response.json()

        except RequestsConnectionError as e:
            raise ConnectionError(
                f"Failed to connect to Salesforce API at {url}. "
                f"Ensure the API server is running. Error: {str(e)}"
            )
        except Timeout as e:
            raise ConnectionError(
                f"Request to {url} timed out after {self.timeout} seconds. Error: {str(e)}"
            )
        except RequestException as e:
            raise ConnectionError(
                f"Network error while connecting to {url}: {str(e)}"
            )
        except ValueError as e:
            # JSON decode error
            raise SalesforceError(
                f"Failed to parse API response as JSON: {str(e)}"
            )

    def list_objects(self) -> List[str]:
        """
        Get a list of all available Salesforce objects.

        Returns:
            List of object names (e.g., ['Lead', 'Campaign', 'Account'])

        Raises:
            ConnectionError: If unable to connect to the API
            AuthError: If authentication fails
            SalesforceError: For other API errors

        Example:
            objects = client.list_objects()
            print(f"Available objects: {', '.join(objects)}")
        """
        response = self._make_request('GET', '/sobjects')

        # Handle response format from Salesforce API
        if isinstance(response, dict) and 'sobjects' in response:
            # Extract object names from sobjects array
            return [obj['name'] for obj in response['sobjects']]
        elif isinstance(response, dict) and 'objects' in response:
            return response['objects']
        elif isinstance(response, list):
            return response
        else:
            raise SalesforceError(
                f"Unexpected response format from /sobjects endpoint: {response}"
            )

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """
        Get field schema for a specific Salesforce object.

        Args:
            object_name: Name of the Salesforce object (e.g., 'Lead', 'Campaign')

        Returns:
            Dictionary containing field definitions with types and metadata.
            The response includes:
            - name: Object name
            - fields: List of field definitions with name, type, label, etc.

        Raises:
            ObjectNotFoundError: If the object doesn't exist
            ConnectionError: If unable to connect to the API
            AuthError: If authentication fails
            SalesforceError: For other API errors

        Example:
            schema = client.get_fields('Lead')
            for field in schema['fields']:
                print(f"{field['name']}: {field['type']}")
        """
        if not object_name:
            raise ValueError("object_name cannot be empty")

        endpoint = f'/sobjects/{object_name}/describe'

        try:
            response = self._make_request('GET', endpoint)
            return response
        except ObjectNotFoundError:
            # Re-raise with more helpful message
            available = self.list_objects()
            raise ObjectNotFoundError(
                f"Object '{object_name}' not found. "
                f"Available objects: {', '.join(available)}"
            )

    def query(self, soql: str) -> List[Dict[str, Any]]:
        """
        Execute a SOQL query against the Salesforce API.

        Args:
            soql: SOQL query string (e.g., "SELECT Id, Name FROM Lead WHERE Email != null")

        Returns:
            List of records matching the query. Each record is a dictionary.

        Raises:
            QueryError: If the query is invalid or fails
            ConnectionError: If unable to connect to the API
            AuthError: If authentication fails
            SalesforceError: For other API errors

        Example:
            leads = client.query("SELECT Id, Name, Email FROM Lead LIMIT 5")
            for lead in leads:
                print(f"Lead: {lead['Name']} ({lead['Email']})")
        """
        if not soql or not soql.strip():
            raise QueryError("SOQL query cannot be empty")

        # Basic validation
        if not soql.strip().upper().startswith('SELECT'):
            raise QueryError(
                "Invalid SOQL query. Query must start with SELECT. "
                f"Got: {soql[:50]}..."
            )

        try:
            response = self._make_request(
                'GET',
                '/query',
                params={'q': soql}
            )

            # Handle both possible response formats
            if isinstance(response, dict) and 'records' in response:
                return response['records']
            elif isinstance(response, list):
                return response
            else:
                # If response is a dict but not in expected format, return it as-is
                return [response] if isinstance(response, dict) else []

        except SalesforceError as e:
            # Re-raise as QueryError for better error handling
            if "404" in str(e) or "not found" in str(e).lower():
                raise QueryError(
                    f"Query failed - object or field not found. Query: {soql}. Error: {str(e)}"
                )
            raise QueryError(
                f"Query execution failed. Query: {soql}. Error: {str(e)}"
            )

    def get_object_count(self, object_name: str) -> int:
        """
        Get the total count of records for a specific object.

        Args:
            object_name: Name of the Salesforce object

        Returns:
            Total number of records

        Example:
            count = client.get_object_count('Lead')
            print(f"Total leads: {count}")
        """
        result = self.query(f"SELECT COUNT() FROM {object_name}")
        if result and len(result) > 0:
            # Handle different response formats
            if 'count' in result[0]:
                return result[0]['count']
            elif 'expr0' in result[0]:  # Some APIs return COUNT() as expr0
                return result[0]['expr0']
        return 0

    def close(self):
        """Close the underlying HTTP session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False
