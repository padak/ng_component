"""DuckDB connection and query helpers."""

import duckdb
import os
from typing import List, Dict, Any, Optional
from pathlib import Path


# Map Salesforce object names to DuckDB table names
OBJECT_TABLE_MAP = {
    "Lead": "leads",
    "Opportunity": "opportunities",
    "Account": "accounts",
    "Contact": "contacts",
    "Case": "cases",
    "Task": "tasks",
    "Event": "events",
}

# Reverse mapping
TABLE_OBJECT_MAP = {v: k for k, v in OBJECT_TABLE_MAP.items()}


class DuckDBConnection:
    """Manages DuckDB connection and queries."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize connection to DuckDB."""
        if db_path is None:
            # Default path relative to this file
            current_dir = Path(__file__).parent
            db_path = str(current_dir.parent / "test_data" / "salesforce.duckdb")

        self.db_path = db_path
        self._conn = None

    @property
    def conn(self):
        """Get or create database connection."""
        if self._conn is None:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database not found at {self.db_path}")
            self._conn = duckdb.connect(self.db_path, read_only=True)
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_table_name(self, sobject: str) -> Optional[str]:
        """Convert Salesforce object name to DuckDB table name."""
        return OBJECT_TABLE_MAP.get(sobject)

    def get_sobject_name(self, table: str) -> Optional[str]:
        """Convert DuckDB table name to Salesforce object name."""
        return TABLE_OBJECT_MAP.get(table)

    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        result = self.conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        return [row[0] for row in result]

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a table."""
        result = self.conn.execute(
            f"DESCRIBE {table_name}"
        ).fetchall()

        columns = []
        for row in result:
            columns.append({
                "name": row[0],
                "type": row[1],
                "null": row[2] == "YES",
                "key": row[3] if len(row) > 3 else None,
                "default": row[4] if len(row) > 4 else None,
            })
        return columns

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as list of dicts."""
        try:
            result = self.conn.execute(query)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise ValueError(f"Query execution failed: {str(e)}")

    def get_record_count(self, table_name: str) -> int:
        """Get total record count for a table."""
        result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0

    def insert_record(self, table_name: str, data: Dict[str, Any]) -> str:
        """
        Insert a record into a table.
        Returns the generated ID.
        Note: This is a simplified implementation.
        """
        # For mock purposes, we'll just return a fake ID
        # In a real implementation, you'd execute an INSERT
        import uuid
        return f"a{uuid.uuid4().hex[:17]}"


# Global connection instance
_db = None


def get_db() -> DuckDBConnection:
    """Get the global database connection."""
    global _db
    if _db is None:
        _db = DuckDBConnection()
    return _db


def close_db():
    """Close the global database connection."""
    global _db
    if _db:
        _db.close()
        _db = None
