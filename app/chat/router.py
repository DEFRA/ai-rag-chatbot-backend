import logging

from fastapi import APIRouter, HTTPException

from app.chat.models import QueryRequest, QueryResponse
from app.core.agents.agentic_graph import (
    run_graph_with_memory,  # Uses persistent memory
)

logger = logging.getLogger(__name__)

# Define the router with a prefix, http://localhost:8085/query/
router = APIRouter(prefix="/query", tags=["Query"])


async def get_agent_final_response(
    user_query: str, user_id: str = "default_user"
) -> str:
    """
    Invokes the agent graph with persistent memory and extracts the final response.

    Memory Feature:
    - Uses MemorySaver to persist conversation state per user/session.
    - Each user_id gets a separate memory stream, allowing multi-turn context retention.
    - To enable multi-user memory, pass a unique user_id for each session/user.
    """
    logger.info("Received query for agent processing: '%s'", user_query)
    final_answer = (
        "Sorry, I encountered an issue processing your query."  # Default error message
    )

    try:
        # Use run_graph_with_memory for persistent memory
        # NOTE: run_graph_with_memory is synchronous, so run in thread executor
        import asyncio

        loop = asyncio.get_running_loop()
        final_state = await loop.run_in_executor(
            None, run_graph_with_memory, user_id, user_query
        )

        # --- Extract the final response ---
        if final_state and "messages" in final_state and final_state["messages"]:
            last_message = final_state["messages"][-1]
            if isinstance(last_message, str):
                final_answer = last_message
                logger.debug("Extracted final answer as string from last message.")
            elif hasattr(
                last_message, "content"
            ):  # Handles AIMessage, HumanMessage etc.
                final_answer = last_message.content
                logger.debug(
                    "Extracted final answer from content of %s.", type(last_message)
                )
            else:
                logger.warning(
                    "Could not extract final answer from last message structure: %s",
                    last_message,
                )
        else:
            logger.warning(
                "Final state or messages list is missing/empty: %s", final_state
            )
        # --- End Extraction Logic ---

        logger.info(
            "Agent processing complete."
        )  # Avoid logging potentially sensitive answer

    except Exception as e:
        logger.exception("Error during agent graph execution: %s", e)
        # Raise HTTPException to return a standard FastAPI error response
        error_detail = "An internal error occurred while processing your query."
        raise HTTPException(status_code=500, detail=error_detail) from e

    return final_answer


# Define the POST endpoint
@router.post("/", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """
    Accepts a user query via POST request (JSON body) and returns
    the agent's final response.

    Memory Feature:
    - The agent now remembers previous messages for each user/session.
    - Uses the user_id provided in the request for per-user memory.
    """
    # Use the user_id from the request (defaults to "default_user" if not provided)
    final_answer = await get_agent_final_response(
        request.query, user_id=request.user_id
    )
    return QueryResponse(answer=final_answer)
