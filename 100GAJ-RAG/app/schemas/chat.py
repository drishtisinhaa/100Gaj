from pydantic import BaseModel, Field
from typing import List, Literal

# New model for a single message in the history
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    """Defines the structure of a request to the /chat endpoint."""
    message: str = Field(..., description="The user's message to the chatbot")
    # Add history field to accept conversation context
    history: List[ChatMessage] = Field([], description="The history of the conversation for the session")