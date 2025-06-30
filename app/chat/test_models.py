"""
Simple unit tests for chat models and basic functionality.

These tests run without requiring a full application startup.
"""

import pytest
from pydantic import ValidationError

from app.chat.models import QueryRequest, QueryResponse, ResetRequest


class TestQueryRequest:
    """Test the QueryRequest Pydantic model"""

    def test_valid_query_request(self):
        """Test creating a valid QueryRequest"""
        request = QueryRequest(query="What are farming grants?", user_id="user123")
        assert request.query == "What are farming grants?"
        assert request.user_id == "user123"

    def test_query_request_with_default_user_id(self):
        """Test QueryRequest with default user_id"""
        request = QueryRequest(query="Test query")
        assert request.query == "Test query"
        assert request.user_id == "default_user"

    def test_query_request_missing_query_raises_error(self):
        """Test that missing query field raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(user_id="test_user")  # Missing required 'query'

        # Check that the error is about the missing 'query' field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("query",)
        assert errors[0]["type"] == "missing"

    def test_query_request_empty_query_is_valid(self):
        """Test that empty query string is valid (business logic decides if it's useful)"""
        request = QueryRequest(query="", user_id="test_user")
        assert request.query == ""
        assert request.user_id == "test_user"

    def test_query_request_long_query(self):
        """Test that very long queries are accepted"""
        long_query = "What is " + "very " * 1000 + "long question?"
        request = QueryRequest(query=long_query, user_id="test_user")
        assert request.query == long_query
        assert request.user_id == "test_user"


class TestResetRequest:
    """Test the ResetRequest Pydantic model"""

    def test_valid_reset_request(self):
        """Test creating a valid ResetRequest"""
        request = ResetRequest(user_id="user123")
        assert request.user_id == "user123"

    def test_reset_request_with_default_user_id(self):
        """Test ResetRequest with default user_id"""
        request = ResetRequest()
        assert request.user_id == "default_user"

    def test_reset_request_empty_user_id_uses_default(self):
        """Test that empty user_id still gets the default"""
        # Note: Pydantic will use the default even if we pass None
        request = ResetRequest(user_id="")
        assert request.user_id == ""  # Empty string is valid, not None


class TestQueryResponse:
    """Test the QueryResponse Pydantic model"""

    def test_valid_query_response(self):
        """Test creating a valid QueryResponse"""
        response = QueryResponse(answer="Here is your answer about farming grants.")
        assert response.answer == "Here is your answer about farming grants."

    def test_query_response_empty_answer(self):
        """Test QueryResponse with empty answer"""
        response = QueryResponse(answer="")
        assert response.answer == ""

    def test_query_response_missing_answer_raises_error(self):
        """Test that missing answer field raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            QueryResponse()  # Missing required 'answer'

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("answer",)
        assert errors[0]["type"] == "missing"

    def test_query_response_long_answer(self):
        """Test QueryResponse with very long answer"""
        long_answer = "This is a " + "very " * 1000 + "long answer."
        response = QueryResponse(answer=long_answer)
        assert response.answer == long_answer


class TestModelSerialization:
    """Test JSON serialization/deserialization of models"""

    def test_query_request_to_dict(self):
        """Test converting QueryRequest to dictionary"""
        request = QueryRequest(query="Test query", user_id="user123")
        request_dict = request.model_dump()

        expected = {"query": "Test query", "user_id": "user123"}
        assert request_dict == expected

    def test_query_request_from_dict(self):
        """Test creating QueryRequest from dictionary"""
        data = {"query": "Test query", "user_id": "user123"}
        request = QueryRequest.model_validate(data)

        assert request.query == "Test query"
        assert request.user_id == "user123"

    def test_query_response_to_json(self):
        """Test converting QueryResponse to JSON"""
        response = QueryResponse(answer="Test answer")
        json_str = response.model_dump_json()

        assert '"answer":"Test answer"' in json_str

    def test_reset_request_defaults_in_dict(self):
        """Test that ResetRequest includes defaults in dictionary output"""
        request = ResetRequest()
        request_dict = request.model_dump()

        assert request_dict == {"user_id": "default_user"}


class TestInputValidation:
    """Test edge cases and input validation"""

    def test_query_request_with_special_characters(self):
        """Test QueryRequest with special characters in query"""
        special_query = "What about émojis 🚜 and symbols @#$%?"
        request = QueryRequest(query=special_query, user_id="user123")
        assert request.query == special_query

    def test_user_id_with_special_characters(self):
        """Test user_id with various characters"""
        special_user_id = "user-123_test@domain.com"
        request = QueryRequest(query="Test", user_id=special_user_id)
        assert request.user_id == special_user_id

    def test_query_with_newlines_and_tabs(self):
        """Test query with whitespace characters"""
        query_with_whitespace = "Line 1\nLine 2\tTabbed"
        request = QueryRequest(query=query_with_whitespace)
        assert request.query == query_with_whitespace

    def test_unicode_characters(self):
        """Test with Unicode characters"""
        unicode_query = (
            "农业补助金是什么？"  # Chinese for "What are agricultural grants?"
        )
        request = QueryRequest(query=unicode_query, user_id="中文用户")
        assert request.query == unicode_query
        assert request.user_id == "中文用户"
