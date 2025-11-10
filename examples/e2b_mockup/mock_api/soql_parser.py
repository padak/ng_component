"""Simple SOQL to SQL converter for basic Salesforce queries.

This module provides a simplified SOQL parser that converts basic Salesforce
SOQL queries to DuckDB-compatible SQL queries. It supports common clauses but
doesn't implement the full SOQL specification.

Supported Features:
- SELECT clause (including * for all fields)
- FROM clause (single object only)
- WHERE clause with AND operator
- ORDER BY clause
- LIMIT clause
- Comparison operators: =, >, <, >=, <=, !=

Limitations:
- No support for OR operator
- No support for relationship queries (e.g., Account.Name)
- No support for aggregate functions (COUNT, SUM, etc.)
- No support for GROUP BY
- No support for HAVING
- No support for subqueries
- No support for date literals (TODAY, LAST_WEEK, etc.)
"""

import re
from typing import Optional
from db import get_db


class SOQLParseError(ValueError):
    """Raised when SOQL query cannot be parsed."""
    pass


class SOQLParser:
    """Parser for converting simple SOQL queries to SQL."""

    def __init__(self):
        """Initialize the SOQL parser."""
        self.db = get_db()

    def parse(self, soql: str) -> str:
        """
        Parse a SOQL query and convert it to SQL.

        Supports basic patterns like:
        - SELECT * FROM Lead
        - SELECT Id, Name FROM Lead WHERE Status='Open'
        - SELECT * FROM Lead WHERE CreatedDate > '2024-01-01'
        - SELECT * FROM Lead WHERE Status='Open' AND CreatedDate > '2024-01-01'
        - SELECT * FROM Lead ORDER BY CreatedDate DESC
        - SELECT * FROM Lead LIMIT 100

        Args:
            soql: SOQL query string

        Returns:
            SQL query string for DuckDB

        Raises:
            SOQLParseError: If the query cannot be parsed
        """
        try:
            # Clean up the query
            soql = soql.strip()

            # Parse each clause
            select_clause = self._parse_select(soql)
            from_clause = self._parse_from(soql)
            where_clause = self._parse_where(soql)
            order_clause = self._parse_order(soql)
            limit_clause = self._parse_limit(soql)

            # Build SQL query
            sql_parts = [
                f"SELECT {select_clause}",
                f"FROM {from_clause}"
            ]

            if where_clause:
                sql_parts.append(f"WHERE {where_clause}")

            if order_clause:
                sql_parts.append(f"ORDER BY {order_clause}")

            if limit_clause:
                sql_parts.append(f"LIMIT {limit_clause}")

            return " ".join(sql_parts)

        except Exception as e:
            raise SOQLParseError(f"Failed to parse SOQL query: {str(e)}")

    def _parse_select(self, soql: str) -> str:
        """
        Extract and validate SELECT clause.

        Args:
            soql: SOQL query string

        Returns:
            SELECT clause content (field list)

        Raises:
            SOQLParseError: If SELECT clause is invalid or missing
        """
        match = re.search(r"SELECT\s+(.*?)\s+FROM", soql, re.IGNORECASE | re.DOTALL)
        if not match:
            raise SOQLParseError("Missing or invalid SELECT clause")

        select_fields = match.group(1).strip()

        if not select_fields:
            raise SOQLParseError("SELECT clause cannot be empty")

        # Replace SOQL-specific field references if needed
        # For now, pass through as-is since we're doing simple mapping
        return select_fields

    def _parse_from(self, soql: str) -> str:
        """
        Extract and convert FROM clause.

        Args:
            soql: SOQL query string

        Returns:
            Table name for SQL query

        Raises:
            SOQLParseError: If FROM clause is invalid or object not found
        """
        match = re.search(r"FROM\s+(\w+)", soql, re.IGNORECASE)
        if not match:
            raise SOQLParseError("Missing or invalid FROM clause")

        sobject = match.group(1)
        table_name = self.db.get_table_name(sobject)

        if not table_name:
            raise SOQLParseError(f"Unknown SObject: {sobject}")

        return table_name

    def _parse_where(self, soql: str) -> Optional[str]:
        """
        Extract and convert WHERE clause.

        Supports:
        - Simple comparisons: field = 'value', field > 100
        - AND operator for multiple conditions
        - String literals in single quotes
        - Date literals in single quotes
        - Numeric values

        Args:
            soql: SOQL query string

        Returns:
            WHERE clause content or None if not present
        """
        match = re.search(
            r"WHERE\s+(.*?)(?:ORDER\s+BY|LIMIT|$)",
            soql,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            return None

        where_clause = match.group(1).strip()

        if not where_clause:
            return None

        # Convert SOQL-specific operators if needed
        # For now, most operators are compatible with SQL
        # Handle common cases:

        # Replace != with <>
        where_clause = re.sub(r"!=", "<>", where_clause)

        return where_clause

    def _parse_order(self, soql: str) -> Optional[str]:
        """
        Extract ORDER BY clause.

        Supports:
        - Single field: ORDER BY CreatedDate
        - Direction: ORDER BY CreatedDate DESC
        - Multiple fields: ORDER BY CreatedDate DESC, Name ASC

        Args:
            soql: SOQL query string

        Returns:
            ORDER BY clause content or None if not present
        """
        match = re.search(
            r"ORDER\s+BY\s+(.*?)(?:LIMIT|$)",
            soql,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            return None

        order_clause = match.group(1).strip()

        if not order_clause:
            return None

        return order_clause

    def _parse_limit(self, soql: str) -> Optional[str]:
        """
        Extract LIMIT clause.

        Args:
            soql: SOQL query string

        Returns:
            LIMIT value or None if not present
        """
        match = re.search(r"LIMIT\s+(\d+)", soql, re.IGNORECASE)

        if not match:
            return None

        return match.group(1)


# Convenience function for direct use
def parse_soql(soql: str) -> str:
    """
    Parse a SOQL query and convert it to SQL.

    This is a convenience function that creates a parser instance
    and parses the query in one call.

    Args:
        soql: SOQL query string

    Returns:
        SQL query string for DuckDB

    Raises:
        SOQLParseError: If the query cannot be parsed

    Examples:
        >>> parse_soql("SELECT * FROM Lead")
        'SELECT * FROM leads'

        >>> parse_soql("SELECT Id, Name FROM Lead WHERE Status='Open'")
        "SELECT Id, Name FROM leads WHERE Status='Open'"

        >>> parse_soql("SELECT * FROM Lead WHERE CreatedDate > '2024-01-01' LIMIT 10")
        "SELECT * FROM leads WHERE CreatedDate > '2024-01-01' LIMIT 10"
    """
    parser = SOQLParser()
    return parser.parse(soql)
