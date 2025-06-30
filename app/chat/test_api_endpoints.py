"""
API endpoint tests with proper mocking to avoid database dependencies.

These tests verify that your FastAPI endpoints work correctly without
requiring actual database or AI service connections.
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# We'll create a test app that doesn't have the lifespan events that connect to MongoDB
from app.chat.router import router as chat_router
from app.example.router import router as example_router
from app.health.router import router as health_router


def create_test_app():
    """Create a FastAPI app for testing without database connections"""
    app = FastAPI()
    app.include_router(health_router)
    app.include_router(example_router)
    app.include_router(chat_router)
    return app


# Create test client with our test app
test_app = create_test_app()
client = TestClient(test_app)


class TestHealthEndpoint:
    """Test the health check endpoint"""

    def test_health_endpoint(self):
        """Test that health endpoint returns ok status"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestQueryEndpoint:
    """Test the /query/ endpoint"""

    @patch("app.chat.router.get_agent_final_response")
    def test_query_endpoint_success(self, mock_get_response):
        """Test successful query with mocked agent response"""
        # Mock the agent to return a specific response
        mock_get_response.return_value = "This is a test response from the agent."

        # Make the request
        request_data = {
            "query": "What are farming grants available?",
            "user_id": "test_user_123",
        }
        response = client.post("/query/", json=request_data)

        # Verify the response
        assert response.status_code == 200
        response_json = response.json()
        assert "answer" in response_json
        assert response_json["answer"] == "This is a test response from the agent."

        # Verify the mock was called with correct arguments
        mock_get_response.assert_called_once_with(
            "What are farming grants available?", user_id="test_user_123"
        )

    @patch("app.chat.router.get_agent_final_response")
    def test_query_endpoint_with_default_user_id(self, mock_get_response):
        """Test query endpoint when user_id is not provided"""
        mock_get_response.return_value = "Default user response"

        request_data = {"query": "Test query without user_id"}
        response = client.post("/query/", json=request_data)

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["answer"] == "Default user response"

        # Verify it was called with default user_id
        mock_get_response.assert_called_once_with(
            "Test query without user_id", user_id="default_user"
        )

    def test_query_endpoint_missing_query_field(self):
        """Test that missing query field returns validation error"""
        request_data = {
            "user_id": "test_user"
            # Missing required 'query' field
        }
        response = client.post("/query/", json=request_data)

        assert response.status_code == 422  # Unprocessable Entity
        error_data = response.json()
        assert "detail" in error_data

        # Check that the error mentions the missing 'query' field
        errors = error_data["detail"]
        assert any(error["loc"] == ["body", "query"] for error in errors)

    def test_query_endpoint_invalid_json(self):
        """Test that invalid JSON returns appropriate error"""
        response = client.post(
            "/query/",
            data="invalid json content",  # Not JSON
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @patch("app.chat.router.get_agent_final_response")
    def test_query_endpoint_empty_query(self, mock_get_response):
        """Test behavior with empty query string"""
        mock_get_response.return_value = "I need more information to help you."

        request_data = {"query": "", "user_id": "test_user"}
        response = client.post("/query/", json=request_data)

        assert response.status_code == 200
        mock_get_response.assert_called_once_with("", user_id="test_user")

    @patch("app.chat.router.get_agent_final_response")
    def test_query_endpoint_agent_error_handling(self, mock_get_response):
        """Test that agent errors are properly handled"""
        # Mock the agent to raise an exception
        from fastapi import HTTPException

        mock_get_response.side_effect = HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your query.",
        )

        request_data = {"query": "This will cause an error", "user_id": "test_user"}
        response = client.post("/query/", json=request_data)

        assert response.status_code == 500
        error_data = response.json()
        assert "detail" in error_data
        assert "internal error" in error_data["detail"].lower()


class TestResetEndpoint:
    """Test the /query/reset endpoint"""

    @patch("app.chat.router.reset_user_memory")
    def test_reset_endpoint_success(self, mock_reset_memory):
        """Test successful memory reset"""
        # Mock successful reset
        mock_reset_memory.return_value = True

        request_data = {"user_id": "test_user_123"}
        response = client.post("/query/reset", json=request_data)

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        assert "message" in response_json
        assert "test_user_123" in response_json["message"]

        # Verify the mock was called correctly
        mock_reset_memory.assert_called_once_with("test_user_123")

    @patch("app.chat.router.reset_user_memory")
    def test_reset_endpoint_with_default_user_id(self, mock_reset_memory):
        """Test reset endpoint with default user_id"""
        mock_reset_memory.return_value = True

        request_data = {}  # No user_id provided
        response = client.post("/query/reset", json=request_data)

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        assert "default_user" in response_json["message"]

        # Verify it used the default user_id
        mock_reset_memory.assert_called_once_with("default_user")

    @patch("app.chat.router.reset_user_memory")
    def test_reset_endpoint_failure(self, mock_reset_memory):
        """Test reset endpoint when memory reset fails"""
        # Mock failed reset
        mock_reset_memory.return_value = False

        request_data = {"user_id": "test_user"}
        response = client.post("/query/reset", json=request_data)

        assert response.status_code == 500
        error_data = response.json()
        assert "detail" in error_data
        assert "Failed to reset chat memory" in error_data["detail"]

    def test_reset_endpoint_invalid_json(self):
        """Test reset endpoint with invalid JSON"""
        response = client.post(
            "/query/reset",
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


class TestEndpointIntegration:
    """Test workflows that use multiple endpoints"""

    @patch("app.chat.router.get_agent_final_response")
    @patch("app.chat.router.reset_user_memory")
    def test_query_reset_query_workflow(self, mock_reset, mock_query):
        """Test a complete workflow: query -> reset -> query"""
        # Setup mocks
        mock_query.return_value = "Agent response"
        mock_reset.return_value = True

        user_id = "workflow_test_user"

        # Step 1: Initial query
        query1_data = {"query": "First question", "user_id": user_id}
        response1 = client.post("/query/", json=query1_data)
        assert response1.status_code == 200

        # Step 2: Reset memory
        reset_data = {"user_id": user_id}
        reset_response = client.post("/query/reset", json=reset_data)
        assert reset_response.status_code == 200

        # Step 3: Second query (after reset)
        query2_data = {"query": "Second question", "user_id": user_id}
        response2 = client.post("/query/", json=query2_data)
        assert response2.status_code == 200

        # Verify all calls were made
        assert mock_query.call_count == 2
        mock_reset.assert_called_once_with(user_id)

    def test_multiple_users_separate_sessions(self):
        """Test that different user_ids are handled separately"""
        with patch("app.chat.router.get_agent_final_response") as mock_query:
            mock_query.return_value = "Response"

            # Two different users make queries
            user1_data = {"query": "User 1 question", "user_id": "user_1"}
            user2_data = {"query": "User 2 question", "user_id": "user_2"}

            response1 = client.post("/query/", json=user1_data)
            response2 = client.post("/query/", json=user2_data)

            assert response1.status_code == 200
            assert response2.status_code == 200

            # Verify both calls were made with correct user_ids
            assert mock_query.call_count == 2
            mock_query.assert_any_call("User 1 question", user_id="user_1")
            mock_query.assert_any_call("User 2 question", user_id="user_2")


class TestErrorHandling:
    """Test various error scenarios"""

    def test_unsupported_http_method_on_query(self):
        """Test that GET request to query endpoint returns method not allowed"""
        response = client.get("/query/")
        assert response.status_code == 405  # Method Not Allowed

    def test_unsupported_http_method_on_reset(self):
        """Test that GET request to reset endpoint returns method not allowed"""
        response = client.get("/query/reset")
        assert response.status_code == 405  # Method Not Allowed

    def test_nonexistent_endpoint(self):
        """Test that nonexistent endpoints return 404"""
        response = client.post("/nonexistent/")
        assert response.status_code == 404

    @patch("app.chat.router.get_agent_final_response")
    def test_query_with_very_long_input(self, mock_get_response):
        """Test query endpoint with extremely long input"""
        mock_get_response.return_value = "Handled long query"

        # Create a very long query
        long_query = "What about " + "very " * 5000 + "long query?"

        request_data = {"query": long_query, "user_id": "test_user"}

        response = client.post("/query/", json=request_data)

        # Should handle gracefully (either succeed or fail with appropriate error)
        assert response.status_code in [200, 400, 413, 500]  # Acceptable responses
