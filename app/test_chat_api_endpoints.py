"""
🧠 LEARNING: FastAPI Chat Endpoint Integration Tests

This file demonstrates comprehensive API endpoint testing for our AI RAG chatbot.
We're testing the HTTP request/response cycle, ensuring our FastAPI endpoints
behave correctly under various conditions.

Why test API endpoints?
- Verifies the complete request/response flow
- Ensures proper HTTP status codes and response formats
- Tests error handling and input validation at the API layer
- Catches integration issues between FastAPI and our business logic
- Provides confidence that clients can interact with our API reliably

🧠 LEARNING: Testing Strategy Overview

We follow a layered testing approach:
1. **Unit Tests** (models.py) - Test data validation in isolation
2. **Integration Tests** (this file) - Test API endpoints with mocked dependencies
3. **End-to-End Tests** (future) - Test complete workflows with real services

This file focuses on integration testing with strategic mocking.
"""

from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# 🧠 LEARNING: Why We Create a Test App Instead of Using the Main App
#
# Our main app has lifespan events that connect to MongoDB, which would:
# 1. Require a real database for tests (slow, unreliable)
# 2. Make tests depend on external services
# 3. Create test pollution between test runs
#
# Solution: Create a minimal test app with only the endpoints we need
from app.chat.router import router as chat_router
from app.example.router import router as example_router
from app.health.router import router as health_router


def create_test_app() -> FastAPI:
    """
    🧠 LEARNING: Test App Factory Pattern

    This creates a FastAPI app specifically for testing without:
    - Database connections (lifespan events)
    - External service dependencies
    - Complex middleware that might interfere with tests

    Benefits:
    - Fast test execution
    - Isolated test environment
    - Predictable behavior
    """
    app = FastAPI(title="Test AI RAG Chatbot API")

    # Include only the routers we want to test
    app.include_router(health_router, tags=["health"])
    app.include_router(example_router, tags=["example"])
    app.include_router(chat_router, tags=["chat"])

    return app


# Create test client with our test app
test_app = create_test_app()
client = TestClient(test_app)


class TestHealthEndpoint:
    """
    🧠 LEARNING: Health Endpoint Testing

    Health endpoints are critical for:
    - Load balancer health checks
    - Monitoring systems
    - Deployment verification

    We test that it always returns a consistent, expected response.
    """

    def test_health_endpoint_returns_ok_status(self):
        """
        🧠 LEARNING: Basic Health Check Test

        Health endpoints should be simple and fast. They verify the
        application is running and can accept requests.

        What we're testing:
        - HTTP 200 status code (success)
        - Expected JSON response format
        - Consistent response content
        """
        # Given: Application is running
        # When: We request the health status
        response = client.get("/health")

        # Then: Should return healthy status
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_endpoint_response_time_is_fast(self):
        """
        🧠 LEARNING: Performance Testing Example

        Health checks need to be fast since they're called frequently
        by monitoring systems. This test ensures reasonable response times.

        Alternative approaches:
        - Use pytest-benchmark for more sophisticated timing
        - Set up monitoring alerts based on response times
        """
        import time

        # Given: Application is running
        # When: We measure health check response time
        start_time = time.time()
        response = client.get("/health")
        duration = time.time() - start_time

        # Then: Should be fast and successful
        assert response.status_code == 200
        assert duration < 1.0  # Should respond within 1 second


class TestQueryEndpoint:
    """
    🧠 LEARNING: Chat Query Endpoint Testing

    This is our main business endpoint. We test:
    - Happy path scenarios (successful queries)
    - Error handling (validation errors, service failures)
    - Edge cases (empty queries, large inputs)
    - Input validation (required fields, data types)

    Testing approach: Mock external dependencies, test API behavior
    """

    @patch("app.chat.router.get_agent_final_response")
    def test_query_endpoint_processes_valid_request_successfully(
        self, mock_agent_response
    ):
        """
        🧠 LEARNING: Happy Path Testing with Mocking

        This tests the successful flow: valid input → successful processing → valid output

        Why we mock get_agent_final_response:
        - It depends on external AI services (slow, costly, unreliable in tests)
        - We want to test API logic, not AI logic
        - Mocking allows us to control the response and test edge cases

        Alternative approaches:
        - Integration tests with real AI (slower, more expensive)
        - Contract testing to verify AI integration separately
        """
        # Given: Mock agent returns a successful response
        expected_answer = (
            "Farming grants are available through various federal programs..."
        )
        mock_agent_response.return_value = expected_answer

        # Given: Valid request data
        request_data = {
            "query": "What farming grants are available in 2024?",
            "user_id": "test_user_123",
        }

        # When: We make a POST request to the query endpoint
        response = client.post("/query/", json=request_data)

        # Then: Should return successful response with expected format
        assert response.status_code == 200
        response_json = response.json()
        assert "answer" in response_json
        assert response_json["answer"] == expected_answer

        # Then: Should have called the agent with correct parameters
        mock_agent_response.assert_called_once_with(
            "What farming grants are available in 2024?", user_id="test_user_123"
        )

    @patch("app.chat.router.get_agent_final_response")
    def test_query_endpoint_uses_default_user_id_when_omitted(
        self, mock_agent_response
    ):
        """
        🧠 LEARNING: Default Value Integration Testing

        This tests that our Pydantic model defaults work correctly
        through the entire API request cycle.

        Why this matters:
        - Confirms default values work in real HTTP requests (not just unit tests)
        - Tests the integration between FastAPI and Pydantic
        - Ensures backward compatibility if user_id becomes required later
        """
        # Given: Mock agent response
        mock_agent_response.return_value = "Response for default user"

        # Given: Request without user_id (should use default)
        request_data = {"query": "Test query without explicit user_id"}

        # When: We make the request
        response = client.post("/query/", json=request_data)

        # Then: Should succeed and use default user_id
        assert response.status_code == 200
        mock_agent_response.assert_called_once_with(
            "Test query without explicit user_id",
            user_id="default_user",  # Should use the default
        )

    def test_query_endpoint_returns_validation_error_for_missing_query(self):
        """
        🧠 LEARNING: Input Validation Testing

        FastAPI automatically validates request bodies using Pydantic models.
        This test ensures validation errors are properly returned to clients.

        HTTP 422 (Unprocessable Entity) is the standard status code for
        validation errors in FastAPI applications.

        What we're testing:
        - Proper HTTP status code for validation errors
        - Error response includes helpful details
        - Required field validation works at the API level
        """
        # Given: Request missing required 'query' field
        invalid_request = {
            "user_id": "test_user"
            # Missing required 'query' field
        }

        # When: We make request with invalid data
        response = client.post("/query/", json=invalid_request)

        # Then: Should return validation error
        assert response.status_code == 422  # Unprocessable Entity
        error_data = response.json()
        assert "detail" in error_data

        # Then: Error should mention the missing field
        errors = error_data["detail"]
        assert any(
            error["loc"] == ["body", "query"] and error["type"] == "missing"
            for error in errors
        )

    def test_query_endpoint_handles_malformed_json(self):
        """
        🧠 LEARNING: Malformed Request Testing

        Real-world APIs receive malformed requests. Testing ensures
        our API handles them gracefully with appropriate error codes.

        Common malformed request types:
        - Invalid JSON syntax
        - Wrong Content-Type headers
        - Corrupted request bodies
        """
        # Given: Malformed JSON data
        # When: We send invalid JSON
        response = client.post(
            "/query/",
            data="{ invalid json syntax }",  # Malformed JSON
            headers={"Content-Type": "application/json"},
        )

        # Then: Should return appropriate error status
        assert response.status_code == 422

    @patch("app.chat.router.get_agent_final_response")
    def test_query_endpoint_handles_empty_query_gracefully(self, mock_agent_response):
        """
        🧠 LEARNING: Edge Case Testing - Empty Input

        Empty queries are valid at the model level but may not be useful.
        This tests how our system handles edge cases.

        Design decision: We pass empty queries to the agent and let
        it decide how to respond (rather than rejecting at API level).
        """
        # Given: Mock response for empty query
        mock_agent_response.return_value = "I need more information to help you."

        # Given: Request with empty query
        request_data = {"query": "", "user_id": "test_user"}

        # When: We make request with empty query
        response = client.post("/query/", json=request_data)

        # Then: Should accept empty query and pass to agent
        assert response.status_code == 200
        mock_agent_response.assert_called_once_with("", user_id="test_user")

    @patch("app.chat.router.get_agent_final_response")
    def test_query_endpoint_handles_agent_service_errors(self, mock_agent_response):
        """
        🧠 LEARNING: Error Handling Testing

        External services can fail. This tests that our API properly
        handles and reports service failures to clients.

        Error handling strategy:
        - Catch service exceptions
        - Return appropriate HTTP status codes
        - Provide helpful error messages without exposing internal details
        """
        # Given: Agent service raises an exception
        mock_agent_response.side_effect = HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your query.",
        )

        # Given: Valid request that will trigger service error
        request_data = {
            "query": "This query will cause an error",
            "user_id": "test_user",
        }

        # When: We make the request
        response = client.post("/query/", json=request_data)

        # Then: Should return appropriate error response
        assert response.status_code == 500
        error_data = response.json()
        assert "detail" in error_data
        assert "internal error" in error_data["detail"].lower()

    @patch("app.chat.router.get_agent_final_response")
    def test_query_endpoint_handles_very_long_input(self, mock_agent_response):
        """
        🧠 LEARNING: Boundary Testing - Large Payloads

        Tests how our API handles large inputs. Important considerations:
        - Request size limits
        - Processing time for large inputs
        - Memory usage
        - Downstream service limits (AI token limits)
        """
        # Given: Mock response for large input
        mock_agent_response.return_value = "Processed your detailed query."

        # Given: Very long query
        large_query = (
            "Please tell me about farming grants. " * 500
        )  # ~15,000 characters
        request_data = {"query": large_query, "user_id": "test_user"}

        # When: We make request with large input
        response = client.post("/query/", json=request_data)

        # Then: Should handle large input appropriately
        # (May succeed or fail with appropriate limits - both are valid)
        assert response.status_code in [200, 400, 413, 500]  # Acceptable responses


class TestResetEndpoint:
    """
    🧠 LEARNING: Memory Reset Endpoint Testing

    The reset endpoint clears chat history for a user. Testing covers:
    - Successful reset operations
    - Error handling when reset fails
    - Default user ID behavior
    - Response format consistency
    """

    @patch("app.chat.router.reset_user_memory")
    def test_reset_endpoint_successfully_clears_user_memory(self, mock_reset_memory):
        """
        🧠 LEARNING: Service Integration Testing

        This tests the integration between our API endpoint and the
        memory management service.

        What we're testing:
        - API correctly calls the reset service
        - Success responses are properly formatted
        - User ID is passed correctly to the service
        """
        # Given: Memory reset service succeeds
        mock_reset_memory.return_value = True

        # Given: Valid reset request
        request_data = {"user_id": "test_user_456"}

        # When: We request memory reset
        response = client.post("/query/reset", json=request_data)

        # Then: Should return success response
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        assert "message" in response_json
        assert "test_user_456" in response_json["message"]

        # Then: Should have called reset service correctly
        mock_reset_memory.assert_called_once_with("test_user_456")

    @patch("app.chat.router.reset_user_memory")
    def test_reset_endpoint_uses_default_user_id_when_omitted(self, mock_reset_memory):
        """
        🧠 LEARNING: Consistency Testing Across Endpoints

        Both query and reset endpoints use the same default user ID.
        This test ensures consistency in default behavior.
        """
        # Given: Memory reset succeeds
        mock_reset_memory.return_value = True

        # Given: Request without explicit user_id
        request_data = {}  # Empty request body

        # When: We request reset without user_id
        response = client.post("/query/reset", json=request_data)

        # Then: Should use default user_id
        assert response.status_code == 200
        response_json = response.json()
        assert "default_user" in response_json["message"]
        mock_reset_memory.assert_called_once_with("default_user")

    @patch("app.chat.router.reset_user_memory")
    def test_reset_endpoint_handles_service_failure_appropriately(
        self, mock_reset_memory
    ):
        """
        🧠 LEARNING: Failure Scenario Testing

        Services can fail for various reasons (database issues, network problems, etc.).
        This tests that API failures are handled gracefully.

        Error handling principles:
        - Return appropriate HTTP status codes
        - Provide helpful error messages
        - Don't expose internal implementation details
        """
        # Given: Memory reset service fails
        mock_reset_memory.return_value = False

        # Given: Valid reset request
        request_data = {"user_id": "test_user"}

        # When: We request reset (which will fail)
        response = client.post("/query/reset", json=request_data)

        # Then: Should return appropriate error
        assert response.status_code == 500
        error_data = response.json()
        assert "detail" in error_data
        assert "Failed to reset chat memory" in error_data["detail"]


class TestEndpointIntegration:
    """
    🧠 LEARNING: Workflow Integration Testing

    Real users perform workflows involving multiple API calls.
    These tests verify that our endpoints work correctly together.

    Common workflows:
    - Query → Reset → Query (fresh conversation)
    - Multiple queries from same user (conversation continuity)
    - Multiple users with separate sessions
    """

    @patch("app.chat.router.get_agent_final_response")
    @patch("app.chat.router.reset_user_memory")
    def test_complete_conversation_workflow(self, mock_reset, mock_query):
        """
        🧠 LEARNING: End-to-End Workflow Testing

        This tests a complete user workflow:
        1. User makes initial query
        2. User resets conversation
        3. User makes follow-up query

        What we're verifying:
        - All endpoints work correctly in sequence
        - User ID is handled consistently across calls
        - Each step produces expected results
        """
        # Given: Services work correctly
        mock_query.return_value = "Agent response"
        mock_reset.return_value = True

        user_id = "workflow_test_user"

        # When: Step 1 - Initial query
        query1_data = {"query": "What are organic farming grants?", "user_id": user_id}
        response1 = client.post("/query/", json=query1_data)

        # Then: First query should succeed
        assert response1.status_code == 200
        assert response1.json()["answer"] == "Agent response"

        # When: Step 2 - Reset conversation
        reset_data = {"user_id": user_id}
        reset_response = client.post("/query/reset", json=reset_data)

        # Then: Reset should succeed
        assert reset_response.status_code == 200
        assert reset_response.json()["success"] is True

        # When: Step 3 - Follow-up query after reset
        query2_data = {"query": "Tell me about equipment grants", "user_id": user_id}
        response2 = client.post("/query/", json=query2_data)

        # Then: Second query should succeed
        assert response2.status_code == 200
        assert response2.json()["answer"] == "Agent response"

        # Then: Verify all service calls were made correctly
        assert mock_query.call_count == 2
        mock_reset.assert_called_once_with(user_id)

    @patch("app.chat.router.get_agent_final_response")
    def test_multiple_users_are_handled_independently(self, mock_query):
        """
        🧠 LEARNING: Multi-User Isolation Testing

        Our system should handle multiple users independently.
        This test verifies user isolation works correctly.

        Why this matters:
        - Prevents data leakage between users
        - Ensures scalability for concurrent users
        - Validates user session management
        """
        # Given: Agent responds to queries
        mock_query.return_value = "Response"

        # When: Two different users make queries simultaneously
        user1_data = {"query": "User 1 question", "user_id": "user_1"}
        user2_data = {"query": "User 2 question", "user_id": "user_2"}

        response1 = client.post("/query/", json=user1_data)
        response2 = client.post("/query/", json=user2_data)

        # Then: Both requests should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Then: Agent should be called separately for each user
        assert mock_query.call_count == 2
        mock_query.assert_any_call("User 1 question", user_id="user_1")
        mock_query.assert_any_call("User 2 question", user_id="user_2")


class TestHTTPMethodValidation:
    """
    🧠 LEARNING: HTTP Method Security Testing

    REST APIs should only accept appropriate HTTP methods for each endpoint.
    This prevents potential security issues and ensures proper API usage.

    HTTP 405 (Method Not Allowed) is the standard response for unsupported methods.
    """

    def test_query_endpoint_rejects_get_requests(self):
        """
        🧠 LEARNING: Method Validation Testing

        The query endpoint should only accept POST requests (with request body).
        GET requests don't make sense for submitting queries.
        """
        # When: We try to GET the query endpoint
        response = client.get("/query/")

        # Then: Should reject with Method Not Allowed
        assert response.status_code == 405

    def test_reset_endpoint_rejects_get_requests(self):
        """
        🧠 LEARNING: State-Changing Operation Security

        Reset is a state-changing operation and should not be accessible via GET.
        This prevents accidental resets from browser prefetch or link crawling.
        """
        # When: We try to GET the reset endpoint
        response = client.get("/query/reset")

        # Then: Should reject with Method Not Allowed
        assert response.status_code == 405

    def test_nonexistent_endpoints_return_404(self):
        """
        🧠 LEARNING: API Surface Area Testing

        Ensures our API only exposes intended endpoints and returns
        proper 404 errors for non-existent routes.
        """
        # When: We request a non-existent endpoint
        response = client.post("/nonexistent-endpoint/")

        # Then: Should return Not Found
        assert response.status_code == 404


# 🎉 POP QUIZ: Now that you've seen both model tests and API tests, can you answer this?
#
# Question: What's the key difference between testing a Pydantic model directly (like in test_chat_models.py)
# versus testing it through a FastAPI endpoint (like in this file)?
#
# Think about:
# 1. What layers of the application each approach tests
# 2. What types of bugs each approach would catch
# 3. Which approach is faster to run and why
# 4. When you might choose one approach over the other
#
# Try to formulate your answer before looking at the explanation below!


"""
🧠 LEARNING: Quiz Answer - Model vs API Testing

Key differences:

**Model Testing (Direct Pydantic)**:
- Tests data validation in isolation
- Fast execution (no HTTP overhead)
- Catches: validation logic bugs, default value issues, serialization problems
- Use when: validating business rules, data constraints, model behavior

**API Testing (Through FastAPI)**:
- Tests the complete HTTP request/response cycle
- Slower execution (HTTP + routing + serialization overhead)
- Catches: routing issues, HTTP status codes, request/response format problems, integration bugs
- Use when: validating user-facing behavior, testing error responses, workflow testing

**Both are needed** for comprehensive coverage:
- Model tests ensure your data layer works correctly
- API tests ensure your HTTP layer works correctly
- Together they provide confidence in the complete system

**Example**: A model test might verify that QueryRequest accepts Unicode characters,
while an API test verifies that a POST request with Unicode characters returns HTTP 200
with the correct response format.
"""
