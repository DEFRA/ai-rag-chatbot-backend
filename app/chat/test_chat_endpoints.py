"""
Tests for chat endpoints.

This file tests the /query endpoints to ensure they:
1. Accept valid requests
2. Return proper responses
3. Handle errors correctly
4. Validate input data
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.chat.models import QueryRequest, QueryResponse, ResetRequest
from app.main import app

# Create a test client - this simulates HTTP requests to your API
client = TestClient(app)


class TestQueryEndpoint:
    """Test the POST /query/ endpoint"""

    def test_query_endpoint_exists(self):
        """Test that the query endpoint exists and accepts POST requests"""
        # This is a basic test to ensure the endpoint is accessible
        response = client.post("/query/", json={"query": "test"})
        # We expect either 200 (success) or 500 (error), but not 404 (not found)
        assert response.status_code != 404

    @patch("app.chat.router.get_agent_final_response")
    async def test_query_with_valid_input(self, mock_agent_response):
        """Test query endpoint with valid input data"""
        # Mock the agent response so we don't call the actual AI
        mock_agent_response.return_value = "This is a test response"

        # Test data - this is what a real request would look like
        test_request = {
            "query": "What are farming grants available?",
            "user_id": "test_user_123",
        }

        # Make the request
        response = client.post("/query/", json=test_request)

        # Verify the response
        assert response.status_code == 200
        response_data = response.json()
        assert "answer" in response_data
        assert isinstance(response_data["answer"], str)

    def test_query_with_missing_query_field(self):
        """Test that missing 'query' field returns validation error"""
        # This tests Pydantic validation
        test_request = {
            "user_id": "test_user"
            # Missing required 'query' field
        }

        response = client.post("/query/", json=test_request)

        # Should return 422 (Unprocessable Entity) for validation error
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_query_with_empty_query(self):
        """Test behavior with empty query string"""
        test_request = {
            "query": "",  # Empty query
            "user_id": "test_user",
        }

        response = client.post("/query/", json=test_request)

        # Should still accept empty query (up to business logic to handle)
        # We expect either success or specific error, but not validation error
        assert response.status_code != 422

    def test_query_with_default_user_id(self):
        """Test that user_id defaults to 'default_user' when not provided"""
        test_request = {
            "query": "Test query without user_id"
            # user_id not provided - should default
        }

        response = client.post("/query/", json=test_request)

        # Should work fine with default user_id
        assert response.status_code != 422

    def test_query_with_long_query(self):
        """Test behavior with very long query"""
        long_query = "What is " + "very " * 1000 + "long query?"

        test_request = {"query": long_query, "user_id": "test_user"}

        response = client.post("/query/", json=test_request)

        # Should handle long queries (may succeed or fail gracefully)
        assert response.status_code in [200, 400, 500]  # Acceptable responses


class TestResetEndpoint:
    """Test the POST /query/reset endpoint"""

    def test_reset_endpoint_exists(self):
        """Test that the reset endpoint exists"""
        response = client.post("/query/reset", json={"user_id": "test"})
        assert response.status_code != 404

    @patch("app.chat.router.reset_user_memory")
    def test_reset_with_valid_user_id(self, mock_reset_memory):
        """Test reset endpoint with valid user_id"""
        # Mock the reset function to return success
        mock_reset_memory.return_value = True

        test_request = {"user_id": "test_user_123"}

        response = client.post("/query/reset", json=test_request)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert "message" in response_data
        assert "test_user_123" in response_data["message"]

    @patch("app.chat.router.reset_user_memory")
    def test_reset_failure(self, mock_reset_memory):
        """Test reset endpoint when memory reset fails"""
        # Mock the reset function to return failure
        mock_reset_memory.return_value = False

        test_request = {"user_id": "test_user"}

        response = client.post("/query/reset", json=test_request)

        # Should return 500 error when reset fails
        assert response.status_code == 500
        error_data = response.json()
        assert "detail" in error_data

    def test_reset_with_default_user_id(self):
        """Test reset with default user_id"""
        test_request = {}  # No user_id provided

        response = client.post("/query/reset", json=test_request)

        # Should work with default user_id
        assert response.status_code != 422


class TestRequestModels:
    """Test the Pydantic models used for requests"""

    def test_query_request_model_valid(self):
        """Test QueryRequest model with valid data"""
        # Test creating the model directly
        request = QueryRequest(query="test query", user_id="user123")
        assert request.query == "test query"
        assert request.user_id == "user123"

    def test_query_request_model_defaults(self):
        """Test QueryRequest model with default user_id"""
        request = QueryRequest(query="test query")
        assert request.query == "test query"
        assert request.user_id == "default_user"

    def test_reset_request_model_valid(self):
        """Test ResetRequest model"""
        request = ResetRequest(user_id="user123")
        assert request.user_id == "user123"

    def test_reset_request_model_defaults(self):
        """Test ResetRequest model with defaults"""
        request = ResetRequest()
        assert request.user_id == "default_user"

    def test_query_response_model(self):
        """Test QueryResponse model"""
        response = QueryResponse(answer="test answer")
        assert response.answer == "test answer"


# Integration test example
class TestFullWorkflow:
    """Test complete workflows end-to-end"""

    @patch("app.chat.router.get_agent_final_response")
    @patch("app.chat.router.reset_user_memory")
    async def test_query_then_reset_workflow(self, mock_reset, mock_agent):
        """Test a complete workflow: query -> reset -> query again"""
        mock_agent.return_value = "Test response"
        mock_reset.return_value = True

        user_id = "workflow_test_user"

        # Step 1: Make a query
        query_request = {"query": "First query", "user_id": user_id}
        response1 = client.post("/query/", json=query_request)
        assert response1.status_code == 200

        # Step 2: Reset memory
        reset_request = {"user_id": user_id}
        reset_response = client.post("/query/reset", json=reset_request)
        assert reset_response.status_code == 200

        # Step 3: Make another query
        query_request2 = {"query": "Second query", "user_id": user_id}
        response2 = client.post("/query/", json=query_request2)
        assert response2.status_code == 200
