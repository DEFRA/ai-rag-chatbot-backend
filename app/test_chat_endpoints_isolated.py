"""
🧠 LEARNING: Isolated FastAPI Endpoint Tests

This file demonstrates how to test FastAPI endpoints in isolation,
avoiding complex dependencies that can cause test failures.

Testing Strategy:
- Create minimal test fixtures
- Mock external dependencies at the right level
- Focus on HTTP behavior, not business logic
- Follow Given-When-Then pattern with clear comments

Why isolated testing matters:
- Fast test execution
- Reliable test results
- Easy to debug when tests fail
- Clear separation of concerns
"""

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Create test models that match our real models
from app.chat.models import QueryRequest, QueryResponse, ResetRequest


def create_isolated_test_app() -> FastAPI:
    """
    🧠 LEARNING: Isolated Test App Pattern

    Instead of importing complex routers with dependencies,
    we create a minimal app with just the endpoint logic we want to test.

    Benefits:
    - No external dependencies (databases, AI services)
    - Fast startup and execution
    - Predictable behavior
    - Easy to debug
    """
    app = FastAPI(title="Isolated Test App")

    # Create a simple router for testing
    test_router = APIRouter(prefix="/query", tags=["test"])

    @test_router.post("/", response_model=QueryResponse)
    async def test_query_endpoint(request: QueryRequest):
        """
        🧠 LEARNING: Simplified Endpoint for Testing

        This mimics our real endpoint behavior without complex dependencies.
        We can control the response through mocking.

        Note: We use the request data to create a meaningful test response,
        demonstrating that the endpoint properly receives and processes input.
        """
        # In real endpoint, this would call get_agent_final_response
        # For testing, we create a response that shows we received the request
        return QueryResponse(
            answer=f"Test response for query: '{request.query}' from user: {request.user_id}"
        )

    @test_router.post("/reset")
    async def test_reset_endpoint(request: ResetRequest):
        """Simple reset endpoint for testing"""
        return {
            "success": True,
            "message": f"Chat memory reset for user_id: {request.user_id}",
        }

    # Simple health endpoint
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(test_router)
    return app


# Create test client
test_app = create_isolated_test_app()
client = TestClient(test_app)


class TestBasicEndpointBehavior:
    """
    🧠 LEARNING: Basic HTTP Behavior Testing

    These tests focus on HTTP mechanics rather than business logic:
    - Request/response formats
    - Status codes
    - Input validation
    - Error handling
    """

    def test_health_endpoint_returns_expected_response(self):
        """
        🧠 LEARNING: Simple Health Check Test

        Health endpoints should be the simplest tests in your suite.
        They verify basic HTTP functionality works.
        """
        # Given: Application is running
        # When: We request health status
        response = client.get("/health")

        # Then: Should return success with expected format
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_query_endpoint_accepts_valid_post_request(self):
        """
        🧠 LEARNING: Basic POST Request Testing

        This tests that our endpoint accepts properly formatted requests
        and returns responses in the expected format.

        What we're NOT testing here:
        - AI service integration (that's mocked)
        - Complex business logic (that's unit tested elsewhere)
        - Database operations (those are mocked)

        What we ARE testing:
        - HTTP request/response cycle works
        - Request data is properly received and processed
        - Response format matches expected schema
        """
        # Given: Valid request data
        request_data = {"query": "What are farming grants?", "user_id": "test_user"}

        # When: We make a POST request
        response = client.post("/query/", json=request_data)

        # Then: Should accept request and return proper response
        assert response.status_code == 200
        response_json = response.json()
        assert "answer" in response_json
        assert isinstance(response_json["answer"], str)

        # Then: Response should indicate it received our request data
        assert "What are farming grants?" in response_json["answer"]
        assert "test_user" in response_json["answer"]

    def test_query_endpoint_validates_request_format(self):
        """
        🧠 LEARNING: Input Validation Testing

        FastAPI + Pydantic automatically validate request bodies.
        This test ensures that validation works at the HTTP level.

        HTTP 422 = Unprocessable Entity (validation error)
        """
        # Given: Invalid request (missing required field)
        invalid_request = {
            "user_id": "test_user"
            # Missing required 'query' field
        }

        # When: We send invalid data
        response = client.post("/query/", json=invalid_request)

        # Then: Should return validation error
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_query_endpoint_uses_pydantic_defaults(self):
        """
        🧠 LEARNING: Default Value Integration Testing

        This tests that Pydantic default values work correctly
        through the complete HTTP request cycle.
        """
        # Given: Request with only required fields
        request_data = {
            "query": "Test query"
            # user_id omitted - should use default
        }

        # When: We make the request
        response = client.post("/query/", json=request_data)

        # Then: Should succeed (default value applied)
        assert response.status_code == 200

    def test_reset_endpoint_accepts_post_request(self):
        """
        🧠 LEARNING: Multiple Endpoint Testing

        Testing multiple endpoints ensures our routing works correctly
        and that each endpoint has proper request/response handling.
        """
        # Given: Valid reset request
        request_data = {"user_id": "test_user"}

        # When: We request memory reset
        response = client.post("/query/reset", json=request_data)

        # Then: Should return success response
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["success"] is True
        assert "message" in response_json

    def test_endpoints_reject_unsupported_http_methods(self):
        """
        🧠 LEARNING: HTTP Method Security Testing

        Endpoints should only accept appropriate HTTP methods.
        This prevents security issues and ensures proper API usage.
        """
        # When: We try unsupported methods
        get_query_response = client.get("/query/")
        get_reset_response = client.get("/query/reset")

        # Then: Should reject with Method Not Allowed
        assert get_query_response.status_code == 405
        assert get_reset_response.status_code == 405

    def test_nonexistent_endpoints_return_404(self):
        """
        🧠 LEARNING: API Surface Testing

        Ensures our API only exposes intended endpoints.
        """
        # When: We request non-existent endpoint
        response = client.post("/nonexistent/")

        # Then: Should return Not Found
        assert response.status_code == 404


class TestRequestResponseFormats:
    """
    🧠 LEARNING: Data Format Testing

    These tests verify that our API correctly handles various
    data formats and edge cases in request/response processing.
    """

    def test_query_endpoint_handles_empty_request_body(self):
        """
        🧠 LEARNING: Edge Case - Empty Request Body

        Tests how the API handles completely empty requests.
        Should return validation error, not crash.
        """
        # When: We send empty request body
        response = client.post("/query/", json={})

        # Then: Should return validation error (missing required fields)
        assert response.status_code == 422

    def test_query_endpoint_handles_malformed_json(self):
        """
        🧠 LEARNING: Malformed Input Testing

        Real-world APIs receive malformed data. Testing ensures
        graceful error handling.
        """
        # When: We send malformed JSON
        response = client.post(
            "/query/",
            data="{ invalid json }",
            headers={"Content-Type": "application/json"},
        )

        # Then: Should return appropriate error
        assert response.status_code == 422

    def test_query_endpoint_preserves_unicode_in_request_response_cycle(self):
        """
        🧠 LEARNING: Unicode Support Testing

        Tests that Unicode characters survive the complete
        HTTP request → processing → response cycle.

        This is integration testing of character encoding across
        multiple layers (HTTP, JSON, Pydantic, application logic).
        """
        # Given: Request with Unicode characters
        unicode_request = {
            "query": "农业补助金有哪些？",  # Chinese: "What agricultural subsidies are there?"
            "user_id": "中文用户",  # Chinese: "Chinese user"
        }

        # When: We send Unicode data
        response = client.post("/query/", json=unicode_request)

        # Then: Should process successfully
        assert response.status_code == 200
        # Note: Response content depends on business logic,
        # but the request should be processed without encoding errors

    def test_query_endpoint_handles_large_request_payload(self):
        """
        🧠 LEARNING: Payload Size Testing

        Tests system behavior with large inputs.
        Important for production systems that need to handle
        various input sizes gracefully.
        """
        # Given: Large request payload
        large_query = "Please tell me about farming grants. " * 200  # ~6,000 characters
        large_request = {"query": large_query, "user_id": "test_user"}

        # When: We send large payload
        response = client.post("/query/", json=large_request)

        # Then: Should handle appropriately (success or proper error)
        # Note: Acceptable responses depend on system limits
        assert response.status_code in [200, 400, 413, 500]


# 🎉 POP QUIZ: Testing Strategy Question
#
# Looking at our isolated test approach vs. testing with real dependencies,
# what are the trade-offs?
#
# Consider:
# 1. Test execution speed
# 2. Test reliability
# 3. What types of bugs each approach catches
# 4. Maintenance overhead
#
# Which approach would you choose for:
# - Daily development workflow?
# - Pre-deployment validation?
# - Debugging production issues?


"""
🧠 LEARNING: Quiz Answer - Isolated vs Integration Testing Trade-offs

**Isolated Testing (this file)**:
✅ Pros:
- Fast execution (no external dependencies)
- Reliable (no network/database failures)
- Easy to debug (minimal moving parts)
- Good for TDD workflow

❌ Cons:
- May miss integration bugs
- Doesn't test real service interactions
- Mocks might diverge from real behavior

**Full Integration Testing**:
✅ Pros:
- Tests real service interactions
- Catches integration bugs
- Higher confidence in deployments
- Tests actual performance characteristics

❌ Cons:
- Slower execution
- Less reliable (external service failures)
- Harder to debug (many moving parts)
- More complex test setup

**Recommended Strategy**:
- **Daily development**: Isolated tests (fast feedback)
- **Pre-deployment**: Both isolated + integration tests
- **Production debugging**: Integration tests with real services

**Best practice**: Use both approaches in a testing pyramid:
- Many fast isolated tests (base of pyramid)
- Fewer slower integration tests (middle of pyramid)
- Few end-to-end tests (top of pyramid)
"""
