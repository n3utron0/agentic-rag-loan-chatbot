# cli_app.py

from agent.llm_vertex import init_vertex
from agent.state import ConversationState
from agent.intent_router import route_intent
from agent.flows.emi_flow import handle_emi_turn, looks_like_answer
from agent.slot_extraction.emi_slot_extraction import extract_emi_slots
from agent.slot_extraction.loan_slot_extraction import extract_loan_slots
from agent.flows.loan_flow import handle_loan_turn
from tools.rag import rag_tool

from agent.supervisor import handle_turn
from agent.state import ConversationState

def main():
    init_vertex()

    print("=" * 60)
    print("CLI Test Harness — RAG + EMI Agent")
    print("Type 'exit' to quit")
    print("=" * 60)

    state = ConversationState()

    while True:
        # 1. Get and clean user input
        user_input = input("\nUSER > ").strip()

        # 2. Check for Exit commands
        if user_input.lower() in ("exit", "quit"):
            print("\nExiting...")
            break

        # 3. Handle empty input
        if not user_input:
            continue

        # 4. Check for Reset commands
        if any(k in user_input.lower() for k in ["reset", "clear", "start over"]):
            state.reset_flow()
            state.slots.clear()
            state.last_completed_flow = None
            print("\nBOT > All values cleared. How can I help you now?")
            continue

        # 5. Process normal conversation
        result = handle_turn(state, user_input)
        print("BOT >", result["reply"])
"""
        # ==================================================
        # ACTIVE EMI FLOW
        # ==================================================
        if state.active_flow == "EMI":
            extracted = extract_emi_slots(user_input)

            # Decide ownership
            owns_turn = False

            if state.awaiting_field:
                owns_turn = looks_like_answer(
                    state.awaiting_field, user_input
                )
            else:
                owns_turn = any(v is not None for v in extracted.values())

            if owns_turn:
                result = handle_emi_turn(state, user_input)

                print(
                    "\n[DEBUG EMI TURN]",
                    "awaiting_field =", state.awaiting_field,
                    "interrupt =", result["interrupt"]
                )

                if not result["interrupt"]:
                    if result["response"]:
                        print(f"\nBOT > {result['response']}")

                    if result.get("tool_output"):
                        state.last_completed_flow = {
                            "flow": "EMI",
                            "slots": state.slots.copy()
                        }
                        state.active_flow = None
                        state.awaiting_field = None
                    continue
                # else: fall through to router

        # ==================================================
        # RESUME FROM COMPLETED EMI
        # ==================================================
        if (
            state.active_flow is None
            and state.last_completed_flow
            and state.last_completed_flow["flow"] == "EMI"
        ):
            extracted = extract_emi_slots(user_input)

            if any(v is not None for v in extracted.values()):
                state.active_flow = "EMI"
                state.slots = state.last_completed_flow["slots"].copy()
                state.last_completed_flow = None

                result = handle_emi_turn(state, user_input)

                if result["response"]:
                    print(f"\nBOT > {result['response']}")
                continue

        # ==================================================
        # ACTIVE LOAN FLOW (ownership handling)
        # ==================================================
        if state.active_flow == "LOAN":
            result = handle_loan_turn(state, user_input)

            if result["response"]:
                print(f"\nBOT > {result['response']}")

            if result.get("tool_output"):
                state.last_completed_flow = {
                    "flow": "LOAN",
                    "slots": state.slots.copy()
                }
                state.active_flow = None
                state.awaiting_field = None

            continue
            # Otherwise → fall through to router

        # ==================================================
        # ROUTE INTENT
        # ==================================================
        action = route_intent(state, user_input)
        print("[ROUTED ACTION]", action)
        if action == "START_EMI":
            if (
                state.last_completed_flow
                and state.last_completed_flow["flow"] == "EMI"
            ):
                state.active_flow = "EMI"
                state.slots = state.last_completed_flow["slots"].copy()
            else:
                state.reset_flow()
                state.last_completed_flow = None
                state.active_flow = "EMI"

            result = handle_emi_turn(state, user_input)
            if result["response"]:
                print(f"\nBOT > {result['response']}")
            continue

        if action == "USE_RAG":
            rag_response = rag_tool(user_input)
            print(f"\nBOT > {rag_response['answer']}")
            continue
        
        if action == "START_LOAN":

            if (
                state.last_completed_flow
                and state.last_completed_flow["flow"] == "LOAN"
            ):
                state.active_flow = "LOAN"
                state.slots = state.last_completed_flow["slots"].copy()
            else:
                state.reset_flow()
                state.last_completed_flow = None
                state.active_flow = "LOAN"

            result = handle_loan_turn(state, user_input)

            if result["response"]:
                print(f"\nBOT > {result['response']}")

            continue
        
        print("\nBOT > I didn’t understand that.")
"""
if __name__ == "__main__":
    main()
