from collections.abc import Sequence
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Conversation so far, accumulated across turns
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Have we already done at least one retrieval?
    retrieval_attempted: bool
    # The raw list of Document objects from the last retrieval
    docs: list[Any]
