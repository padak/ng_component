"""Salesforce REST API Mock Server.

A FastAPI-based mock server that simulates the Salesforce REST API,
backed by DuckDB for data storage.

Modules:
    main: FastAPI application and API endpoints
    db: DuckDB connection and query helpers
    models: Pydantic models for request/response validation
    soql_parser: Simple SOQL to SQL converter

Usage:
    Start the server with:
        uvicorn main:app --reload --port 8000

    Or import and use programmatically:
        from mock_api.main import app
"""

__version__ = "1.0.0"
__author__ = "Salesforce Mock API"

from .main import app
from .db import get_db, close_db
from .soql_parser import parse_soql, SOQLParseError

__all__ = ["app", "get_db", "close_db", "parse_soql", "SOQLParseError"]
