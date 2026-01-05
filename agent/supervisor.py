from agent.intent_router import route_intent
from agent.flows.emi_flow import handle_emi_turn
from agent.flows.loan_flow import handle_loan_turn
from tools.rag import rag_tool
from agent.state import ConversationState
from agent.slot_extraction.emi_slot_extraction import extract_emi_slots


def handle_turn(state: ConversationState, user_message: str) -> dict:
    # -----------------------------
    # 0. Global reset
    # -----------------------------
    msg = user_message.lower().strip()
    if msg in ("reset", "clear", "start over"):
        state.reset_flow()
        return {
            "reply": "All values have been cleared. How can I help you?",
            "state": state
        }

    # -----------------------------
    # 1. Resume active flow
    # -----------------------------
    if state.active_flow == "EMI":
        result = handle_emi_turn(state, user_message)

        # Normal continuation
        if not result["interrupt"]:
            if result.get("tool_output"):
                state.last_completed_flow = {
                    "flow": "EMI",
                    "slots": state.slots.copy()
                }
                state.active_flow = None
                state.awaiting_field = None

            return {
                "reply": result.get("response", ""),
                "state": state
            }

        # Interrupted → pause flow and continue routing
        state.pause_current_flow()

    if state.active_flow == "LOAN":
        result = handle_loan_turn(state, user_message)

        # If loan flow produced output → normal continuation
        if result.get("tool_output"):
            state.last_completed_flow = {
                "flow": "LOAN",
                "slots": state.slots.copy()
            }
            state.active_flow = None
            state.awaiting_field = None

            return {
                "reply": result.get("response", ""),
                "state": state
            }

        # If no response, assume interruption
        if result.get("response") is None:
            state.pause_current_flow()
        else:
            return {
                "reply": result.get("response", ""),
                "state": state
            }

    # --------------------------------
    # 2. Resume completed EMI on update
    # --------------------------------
    if (
        state.active_flow is None
        and state.last_completed_flow
        and state.last_completed_flow["flow"] == "EMI"
    ):
        extracted = extract_emi_slots(user_message)

        # If user provided ANY EMI-related value
        if any(v is not None for v in extracted.values()):
            state.active_flow = "EMI"
            state.slots = state.last_completed_flow["slots"].copy()
            state.last_completed_flow = None

            result = handle_emi_turn(state, user_message)

            return {
                "reply": result.get("response", ""),
                "state": state
            }
    # -----------------------------
    # 3. No active flow → route intent
    # -----------------------------
    action = route_intent(state, user_message)

    if action == "START_EMI":
        state.reset_flow()
        state.last_completed_flow = None
        state.active_flow = "EMI"
        result = handle_emi_turn(state, user_message)
        return {
            "reply": result.get("response", ""),
            "state": state
        }

    if action == "START_LOAN":
        state.reset_flow()
        state.active_flow = "LOAN"
        result = handle_loan_turn(state, user_message)
        return {
            "reply": result.get("response", ""),
            "state": state
        }

    # -----------------------------
    # 4. Default → RAG
    # -----------------------------
    rag_result = rag_tool(user_message)

    # Resume paused flow if any
    if state.paused_flow:
        state.resume_paused_flow()

    return {
        "reply": rag_result["answer"],
        "state": state
    }
