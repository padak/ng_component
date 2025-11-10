"""Pydantic models for Salesforce API responses."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    """Represents a Salesforce field definition."""
    name: str
    type: str
    label: str
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    nullable: bool = True
    createable: bool = True
    updateable: bool = True
    unique: bool = False
    defaultValue: Optional[Any] = None
    picklistValues: List[str] = Field(default_factory=list)
    referenceTo: Optional[List[str]] = None


class SObjectMetadata(BaseModel):
    """Represents a Salesforce SObject metadata."""
    name: str
    label: str
    labelPlural: str
    keyPrefix: Optional[str] = None
    custom: bool = False
    createable: bool = True
    updateable: bool = True
    deletable: bool = True
    queryable: bool = True
    fields: List[FieldDefinition] = Field(default_factory=list)


class SObjectBasic(BaseModel):
    """Basic SObject information for listing."""
    name: str
    label: str
    labelPlural: str
    custom: bool = False
    keyPrefix: Optional[str] = None


class SObjectsResponse(BaseModel):
    """Response for /sobjects endpoint."""
    encoding: str = "UTF-8"
    maxBatchSize: int = 200
    sobjects: List[SObjectBasic]


class QueryResult(BaseModel):
    """Response for SOQL query execution."""
    totalSize: int
    done: bool
    records: List[Dict[str, Any]]


class CreateRecordResponse(BaseModel):
    """Response for creating a record."""
    id: str
    success: bool
    errors: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Error response model."""
    message: str
    errorCode: str
