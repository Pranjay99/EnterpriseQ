from collections import defaultdict
from langchain_classic.memory import ConversationBufferWindowMemory

# In-memory store: session_id -> LangChain memory object
# k=10 means we keep the last 10 turns of conversation
_sessions: dict[str, ConversationBufferWindowMemory] = defaultdict(
    lambda: ConversationBufferWindowMemory(k=10, return_messages=True)
)


def get_memory(session_id: str) -> ConversationBufferWindowMemory:
    """Return (or lazily create) the memory object for a session."""
    return _sessions[session_id]


def clear_memory(session_id: str) -> None:
    """Wipe all conversation history for a session."""
    if session_id in _sessions:
        del _sessions[session_id]


def list_sessions() -> list[str]:
    """Return all active session IDs (useful for debugging)."""
    return list(_sessions.keys())
