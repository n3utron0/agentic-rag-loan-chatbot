# backend/session_store.py
# NOTE:
# This is an in-memory store suitable for:
# - local development
# - demos
# - single-instance deployments
#
# In production, this can be replaced with Redis
# without changing any agent logic.

from typing import Dict
from agent.state import ConversationState

# In-memory session store (OK for local / demo)
_SESSIONS: Dict[str, ConversationState] = {}


def get_session(session_id: str) -> ConversationState:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = ConversationState()
    return _SESSIONS[session_id]
