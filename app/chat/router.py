import logging

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage

from app.chat.models import QueryRequest, QueryResponse
from app.core.agents.agentic_graph import graph

logger = logging.getLogger(__name__)

# Define the router with a prefix, http://localhost:8085/query/
router = APIRouter(prefix="/query", tags=["Query"])


async def get_agent_final_response(user_query: str) -> str:
    """Invokes the agent graph and extracts the final response."""
    logger.info("Received query for agent processing: '%s'", user_query)
    # Initial state for the graph, ensuring correct message format
    initial_state = {"messages": [HumanMessage(content=user_query)]}
    final_answer = (
        "Sorry, I encountered an issue processing your query."  # Default error message
    )

    try:
        # Use ainvoke for a single, complete result
        final_state = await graph.ainvoke(initial_state)

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
    """
    final_answer = await get_agent_final_response(request.query)
    return QueryResponse(answer=final_answer)
