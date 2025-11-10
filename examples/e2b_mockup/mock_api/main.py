"""FastAPI application simulating Salesforce REST API."""

import re
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from models import (
    SObjectsResponse,
    SObjectBasic,
    SObjectMetadata,
    FieldDefinition,
    QueryResult,
    CreateRecordResponse,
    ErrorResponse,
)
from db import get_db, close_db, OBJECT_TABLE_MAP
from soql_parser import parse_soql, SOQLParseError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    yield
    # Shutdown
    close_db()


app = FastAPI(
    title="Salesforce REST API Mock",
    description="Mock Salesforce REST API backed by DuckDB",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Type mapping from DuckDB to Salesforce
DUCKDB_TO_SF_TYPE = {
    "VARCHAR": "string",
    "INTEGER": "int",
    "BIGINT": "long",
    "DOUBLE": "double",
    "DECIMAL": "currency",
    "DATE": "date",
    "TIMESTAMP": "datetime",
    "BOOLEAN": "boolean",
    "TEXT": "textarea",
}


def map_duckdb_type_to_sf(duckdb_type: str) -> str:
    """Map DuckDB type to Salesforce field type."""
    # Extract base type (e.g., "VARCHAR" from "VARCHAR(255)")
    base_type = duckdb_type.split("(")[0].upper()
    return DUCKDB_TO_SF_TYPE.get(base_type, "string")


def get_field_definition(col_name: str, col_type: str, nullable: bool) -> FieldDefinition:
    """Create a FieldDefinition from DuckDB column info."""
    sf_type = map_duckdb_type_to_sf(col_type)

    # Extract length for VARCHAR fields
    length = None
    if "VARCHAR" in col_type.upper() and "(" in col_type:
        try:
            length = int(col_type.split("(")[1].split(")")[0])
        except:
            pass

    return FieldDefinition(
        name=col_name,
        type=sf_type,
        label=col_name.replace("_", " ").title(),
        length=length,
        nullable=nullable,
        createable=col_name.lower() not in ["id", "createddate", "lastmodifieddate"],
        updateable=col_name.lower() not in ["id", "createddate"],
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Salesforce REST API Mock Server",
        "version": "1.0.0",
        "endpoints": [
            "/sobjects",
            "/sobjects/{object}/describe",
            "/query",
            "/sobjects/{object}",
        ]
    }


@app.get("/sobjects", response_model=SObjectsResponse)
async def list_sobjects():
    """
    List all available Salesforce objects.

    Returns a list of SObjects available in the mock database.
    """
    db = get_db()
    tables = db.list_tables()

    sobjects = []
    for table in tables:
        sobject_name = db.get_sobject_name(table)
        if sobject_name:
            sobjects.append(
                SObjectBasic(
                    name=sobject_name,
                    label=sobject_name,
                    labelPlural=f"{sobject_name}s",
                    custom=False,
                    keyPrefix=sobject_name[:3].upper(),
                )
            )

    return SObjectsResponse(sobjects=sobjects)


@app.get("/sobjects/{sobject}/describe", response_model=SObjectMetadata)
async def describe_sobject(sobject: str):
    """
    Get field schema for a Salesforce object.

    Args:
        sobject: The name of the SObject (e.g., Lead, Opportunity)

    Returns:
        Detailed metadata including all fields and their types.
    """
    db = get_db()
    table_name = db.get_table_name(sobject)

    if not table_name:
        raise HTTPException(
            status_code=404,
            detail=f"SObject '{sobject}' not found"
        )

    try:
        schema = db.get_table_schema(table_name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve schema: {str(e)}"
        )

    fields = [
        get_field_definition(col["name"], col["type"], col["null"])
        for col in schema
    ]

    return SObjectMetadata(
        name=sobject,
        label=sobject,
        labelPlural=f"{sobject}s",
        custom=False,
        fields=fields,
    )




@app.get("/query", response_model=QueryResult)
async def execute_query(q: str = Query(..., description="SOQL query string")):
    """
    Execute a SOQL query.

    Args:
        q: SOQL query string

    Returns:
        Query results with totalSize, done flag, and records array.

    Examples:
        - /query?q=SELECT * FROM Lead
        - /query?q=SELECT Id, Name FROM Lead WHERE Status='Open'
        - /query?q=SELECT * FROM Lead WHERE CreatedDate > '2024-01-01'
    """
    db = get_db()

    try:
        # Parse SOQL and convert to SQL using the dedicated parser
        sql = parse_soql(q)

        # Execute query
        records = db.execute_query(sql)

        # Add attributes to each record (Salesforce format)
        for record in records:
            record["attributes"] = {
                "type": re.search(r"FROM\s+(\w+)", q, re.IGNORECASE).group(1),
                "url": f"/services/data/v58.0/sobjects/{record.get('Id', 'unknown')}"
            }

        return QueryResult(
            totalSize=len(records),
            done=True,
            records=records,
        )

    except SOQLParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {str(e)}"
        )


@app.post("/sobjects/{sobject}", response_model=CreateRecordResponse)
async def create_record(sobject: str, data: Dict[str, Any]):
    """
    Create a new record in a Salesforce object.

    Args:
        sobject: The name of the SObject (e.g., Lead, Opportunity)
        data: Record data as JSON

    Returns:
        Created record ID and success status.

    Note: This is a mock implementation that generates fake IDs.
    """
    db = get_db()
    table_name = db.get_table_name(sobject)

    if not table_name:
        raise HTTPException(
            status_code=404,
            detail=f"SObject '{sobject}' not found"
        )

    try:
        # Generate a fake ID (mock implementation)
        record_id = db.insert_record(table_name, data)

        return CreateRecordResponse(
            id=record_id,
            success=True,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create record: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = get_db()
        tables = db.list_tables()
        return {
            "status": "healthy",
            "database": db.db_path,
            "tables_count": len(tables),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
