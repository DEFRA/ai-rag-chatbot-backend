from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Request model for the query endpoint."""

    query: str
    user_id: str = "default_user"  # Optional, defaults to 'default_user'


class QueryResponse(BaseModel):
    """Response model for the query endpoint."""

    answer: str
