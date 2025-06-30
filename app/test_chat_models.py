"""
🧠 LEARNING: Chat Models Test Suite

This test file demonstrates comprehensive Pydantic model testing for our AI RAG chatbot.
We're testing the data validation layer that ensures clean, predictable data flows
between the client and our FastAPI application.

Why test Pydantic models?
- Prevents runtime errors from invalid data
- Ensures default values work as expected
- Validates business rules at the data layer
- Provides living documentation of expected data formats
"""

import pytest
from pydantic import ValidationError

from app.chat.models import QueryRequest, QueryResponse, ResetRequest


class TestQueryRequest:
    """
    🧠 LEARNING: QueryRequest Model Testing

    QueryRequest is our input validation model for chat queries.
    We test both happy paths and error conditions to ensure robust validation.

    Testing Strategy:
    - Valid data scenarios (happy path)
    - Default value behavior
    - Required field validation
    - Edge cases (empty strings, special characters, Unicode)
    """

    def test_valid_query_request_creates_correctly(self):
        """
        🧠 LEARNING: Basic Happy Path Test

        This tests the fundamental expectation: when we provide valid data,
        the model should create correctly and store the values as expected.

        Why this matters: If this fails, our entire API input validation is broken.
        """
        # Given: Valid input data
        query_text = "What are farming grants?"
        user_id = "user123"

        # When: We create the model
        request = QueryRequest(query=query_text, user_id=user_id)

        # Then: Values should be stored correctly
        assert request.query == query_text
        assert request.user_id == user_id

    def test_query_request_applies_default_user_id_when_omitted(self):
        """
        🧠 LEARNING: Default Value Testing

        Pydantic allows default values in model fields. This test ensures
        our default value mechanism works correctly when optional fields are omitted.

        Why defaults matter: They provide sensible fallbacks and reduce
        the burden on API clients to provide every single field.
        """
        # Given: Only required field provided
        query_text = "Test query"

        # When: We create model without optional user_id
        request = QueryRequest(query=query_text)

        # Then: Default value should be applied
        assert request.query == query_text
        assert request.user_id == "default_user"  # Our defined default

    def test_query_request_raises_error_when_required_query_missing(self):
        """
        🧠 LEARNING: Required Field Validation

        Pydantic enforces required fields by raising ValidationError when they're missing.
        This test ensures our validation catches incomplete data before it reaches business logic.

        Alternative approaches:
        1. Make all fields optional with None defaults (more permissive)
        2. Use custom validators for complex validation rules
        3. Create separate models for different validation scenarios
        """
        # Given: Missing required field
        # When/Then: Expect ValidationError when creating incomplete model
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(user_id="test_user")  # Missing required 'query'

        # 🧠 LEARNING: We can also inspect the error details
        error = exc_info.value
        assert "query" in str(error)  # Error should mention the missing field

    def test_query_request_accepts_empty_string_query(self):
        """
        🧠 LEARNING: Edge Case Testing - Empty Strings

        Empty strings are technically valid strings, but may not be meaningful
        for our business logic. We test this to document the current behavior.

        Design decision: We allow empty queries at the model level,
        letting business logic decide how to handle them.
        """
        # Given: Empty query string
        # When: We create model with empty query
        request = QueryRequest(query="")

        # Then: Model should accept it (business logic will handle appropriateness)
        assert request.query == ""
        assert request.user_id == "default_user"

    def test_query_request_handles_very_long_input(self):
        """
        🧠 LEARNING: Boundary Testing - Large Inputs

        Real-world applications need to handle various input sizes.
        This test ensures our model doesn't break with large inputs.

        Production considerations:
        - You might want to add field length limits using Pydantic's Field()
        - Consider downstream impacts (database limits, AI model token limits)
        """
        # Given: Very long query string
        long_query = "What are farming grants? " * 100  # ~2,100 characters

        # When: We create model with large input
        request = QueryRequest(query=long_query, user_id="test_user")

        # Then: Model should handle it gracefully
        assert request.query == long_query
        assert request.user_id == "test_user"

    def test_query_request_preserves_special_characters(self):
        """
        🧠 LEARNING: Character Encoding and Special Symbols

        Real users input all kinds of characters: currencies, punctuation,
        symbols, numbers. This test ensures our model handles diverse character sets.

        Why this matters: Failing to handle special characters can cause
        encoding errors, database issues, or AI processing problems.
        """
        # Given: Query with various special characters
        special_query = "What about €1000 grants for farming (organic)?! @2024"
        special_user_id = "user-123_test"

        # When: We create model with special characters
        request = QueryRequest(query=special_query, user_id=special_user_id)

        # Then: All characters should be preserved
        assert request.query == special_query
        assert request.user_id == special_user_id

    def test_query_request_supports_unicode_characters(self):
        """
        🧠 LEARNING: International Character Support

        Modern applications must support international users.
        This test ensures our models work with non-Latin character sets.

        Unicode considerations:
        - Database must support UTF-8
        - API responses must declare proper encoding
        - AI models should handle multilingual input
        """
        # Given: Unicode characters (Chinese text)
        unicode_query = "农业补助金是什么？"  # "What are agricultural subsidies?"
        unicode_user_id = "中文用户"  # "Chinese user"

        # When: We create model with Unicode text
        request = QueryRequest(query=unicode_query, user_id=unicode_user_id)

        # Then: Unicode should be preserved perfectly
        assert request.query == unicode_query
        assert request.user_id == unicode_user_id


class TestQueryResponse:
    """
    🧠 LEARNING: QueryResponse Model Testing

    QueryResponse is our output model that structures the AI's response
    back to the client. While simpler than input validation, it's crucial
    for ensuring consistent API responses.

    Why test response models?
    - Ensures consistent response format for API consumers
    - Validates that our business logic produces compatible data
    - Catches serialization issues early
    """

    def test_query_response_creates_with_valid_answer(self):
        """
        🧠 LEARNING: Basic Response Model Test

        This verifies our response model correctly structures the AI's answer
        for JSON serialization back to the client.
        """
        # Given: Valid response data
        answer_text = "Farming grants are financial assistance programs..."

        # When: We create the response model
        response = QueryResponse(answer=answer_text)

        # Then: Answer should be stored correctly
        assert response.answer == answer_text

    def test_query_response_handles_empty_answer(self):
        """
        🧠 LEARNING: Edge Case - Empty Responses

        Sometimes the AI might return empty responses due to errors
        or lack of relevant information. We test this edge case.
        """
        # Given: Empty answer
        # When: We create response with empty answer
        response = QueryResponse(answer="")

        # Then: Should accept empty string
        assert response.answer == ""

    def test_query_response_preserves_multiline_text(self):
        """
        🧠 LEARNING: Complex Response Formatting

        AI responses often contain formatting like newlines, lists, etc.
        This test ensures our model preserves text formatting.
        """
        # Given: Multiline answer with formatting
        formatted_answer = """Here are the available farming grants:

1. Organic Transition Grant - Up to $5,000
2. Equipment Purchase Grant - Up to $10,000
3. Sustainable Practices Grant - Up to $3,000

Contact your local office for more details."""

        # When: We create response with formatted text
        response = QueryResponse(answer=formatted_answer)

        # Then: Formatting should be preserved
        assert response.answer == formatted_answer
        assert "\n" in response.answer  # Newlines preserved


class TestResetRequest:
    """
    🧠 LEARNING: ResetRequest Model Testing

    ResetRequest handles chat memory reset functionality.
    Similar to QueryRequest but simpler - only needs user identification.

    Testing focus:
    - Default value behavior
    - User ID validation patterns
    """

    def test_reset_request_creates_with_user_id(self):
        """
        🧠 LEARNING: Basic Reset Request Test

        Verifies the reset request model works with explicit user ID.
        """
        # Given: Specific user ID
        user_id = "user456"

        # When: We create reset request
        request = ResetRequest(user_id=user_id)

        # Then: User ID should be stored
        assert request.user_id == user_id

    def test_reset_request_applies_default_user_id_when_omitted(self):
        """
        🧠 LEARNING: Default Behavior Consistency

        Both QueryRequest and ResetRequest use the same default user ID.
        This consistency is important for user experience.
        """
        # Given: No user ID provided
        # When: We create reset request without user_id
        request = ResetRequest()

        # Then: Should use default
        assert request.user_id == "default_user"

    def test_reset_request_accepts_various_user_id_formats(self):
        """
        🧠 LEARNING: User ID Format Flexibility

        Different systems use different user ID formats.
        Our model should be flexible enough to handle various patterns.
        """
        # Given: Different user ID formats
        test_cases = [
            "user123",  # Simple alphanumeric
            "user-456",  # With hyphen
            "user_789",  # With underscore
            "abc123def456",  # Mixed format
            "User@Domain.com",  # Email-like format
        ]

        # When/Then: All formats should be accepted
        for user_id in test_cases:
            request = ResetRequest(user_id=user_id)
            assert request.user_id == user_id


# 🎉 POP QUIZ: Before we move to API endpoint tests, let's test your understanding!
#
# Question: Why do we test both QueryRequest and ResetRequest for default values
# when they both have the same default ("default_user")?
#
# Think about:
# 1. What happens if someone changes one model but not the other?
# 2. How does this help with future refactoring?
# 3. What would happen if we only tested one model's defaults?
#
# Try to answer before looking at the explanation below!


"""
🧠 LEARNING: Quiz Answer Explanation

We test default values in both models because:

1. **Independence**: Each model should be tested independently. If someone changes
   the default in one model, the tests will catch the inconsistency.

2. **Refactoring Safety**: If we later decide to use different defaults for different
   operations, existing tests ensure we don't break current behavior.

3. **Documentation**: Tests serve as living documentation. Someone reading the tests
   can immediately see what defaults each model uses.

4. **Regression Prevention**: If defaults accidentally change during code changes,
   tests will catch it before it reaches production.

This is a principle called "test isolation" - each test should verify one specific
behavior without depending on other tests.
"""
