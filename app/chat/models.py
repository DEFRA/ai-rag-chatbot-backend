from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Request model for the query endpoint."""

    query: str  # Changed from 'question' to 'query' as per endpoint name


class QueryResponse(BaseModel):
    """Response model for the query endpoint."""

    answer: str
