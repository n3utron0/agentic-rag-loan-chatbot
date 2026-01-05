# agent/state.py

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ConversationState:
    """
    Central state object for the chatbot.

    This class ONLY stores state.
    It does NOT:
    - call LLMs
    - run tools
    - decide intent
    """

    # Which flow currently owns the conversation
    # None | "EMI" | "LOAN"
    active_flow: Optional[str] = None

    # If the bot has asked a question and is waiting for a specific field
    # Example: "principal", "rate", "tenure_months"
    awaiting_field: Optional[str] = None

    # Collected slot values (mutable at all times)
    slots: Dict[str, Any] = field(default_factory=dict)

    # Used when user interrupts a flow
    # Stores a snapshot of the previous flow state
    paused_flow: Optional[Dict[str, Any]] = None

    # Used after a flow is completed
    # Stores a snapshot of the completed flow state
    last_completed_flow: Optional[Dict[str, Any]] = None

    def reset_flow(self):
        """
        Completely reset the active flow.
        Used when starting a fresh intent.
        """
        self.active_flow = None
        self.awaiting_field = None
        self.slots.clear()
        self.paused_flow = None

    def pause_current_flow(self):
        """
        Save current flow state before interruption.
        """
        self.paused_flow = {
            "active_flow": self.active_flow,
            "awaiting_field": self.awaiting_field,
            "slots": self.slots.copy(),
        }
        self.active_flow = None
        self.awaiting_field = None

    def resume_paused_flow(self):
        """
        Resume a previously paused flow (if any).
        """
        if not self.paused_flow:
            return

        self.active_flow = self.paused_flow["active_flow"]
        self.awaiting_field = self.paused_flow["awaiting_field"]
        self.slots = self.paused_flow["slots"]
        self.paused_flow = None
