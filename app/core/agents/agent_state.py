import operator
from collections.abc import Sequence
from typing import Annotated, Optional

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Conversation so far, accumulated across turns
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # Have we already done at least one retrieval?
    retrieval_attempted: bool
    # The raw list of Document objects from the last retrieval
    docs: Optional[list[Document]]
    should_generate: bool
