from enum import Enum
from dataclasses import dataclass
from typing import Optional

class MessageRole(str, Enum):
    """Enum for chat message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

@dataclass
class ChatMessage:
    """Class to represent a chat message"""
    role: MessageRole
    content: str
    name: Optional[str] = None 