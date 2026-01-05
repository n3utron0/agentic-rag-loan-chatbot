# backend/graph.py

from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional

from agent.state import ConversationState
from agent.intent_router import route_intent
from agent.flows.emi_flow import handle_emi_turn
from agent.flows.loan_flow import handle_loan_turn
from tools.rag import rag_tool
from agent.slot_extraction.emi_slot_extraction import extract_emi_slots
from agent.intent_router import route_intent

# -------------------------
# LangGraph State
# -------------------------
class GraphState(TypedDict):
    convo_state: ConversationState
    user_input: str
    bot_reply: str

# -------------------------
# Nodes (ONLY business logic)
# -------------------------
def emi_node(state: GraphState) -> GraphState:
    cs = state["convo_state"]
    result = handle_emi_turn(cs, state["user_input"])

    if not result["interrupt"]:
        if result.get("tool_output"):
            cs.last_completed_flow = {
                "flow": "EMI",
                "slots": cs.slots.copy()
            }
            cs.active_flow = None
            cs.awaiting_field = None
        state["bot_reply"] = result.get("response", "")
        return state

    # interruption → pause
    cs.pause_current_flow()
    state["bot_reply"] = ""
    return state

def loan_node(state: GraphState) -> GraphState:
    cs = state["convo_state"]
    result = handle_loan_turn(cs, state["user_input"])

    if result.get("tool_output"):
        cs.last_completed_flow = {
            "flow": "LOAN",
            "slots": cs.slots.copy()
        }
        cs.active_flow = None
        cs.awaiting_field = None

    state["bot_reply"] = result.get("response", "")
    return state

def rag_node(state: GraphState) -> GraphState:
    cs = state["convo_state"]
    rag_result = rag_tool(state["user_input"])
    state["bot_reply"] = rag_result["answer"]

    if cs.paused_flow:
        cs.resume_paused_flow()

    return state

def reset_node(state: GraphState) -> GraphState:
    cs = state["convo_state"]
    cs.reset_flow()
    cs.last_completed_flow = None
    state["bot_reply"] = "All values have been cleared. How can I help you?"
    return state

# -------------------------
# ROUTING FUNCTIONS (NO STATE WRITES)
# -------------------------
def policy(state: GraphState) -> str:
    cs = state["convo_state"]
    msg = state["user_input"].lower().strip()

    # 1. Reset
    if msg in ("reset", "clear", "start over", "clear emi", "clear loan"):
        return "reset"

    # 2. Active flow always owns the turn
    if cs.active_flow == "EMI":
        return "emi"

    if cs.active_flow == "LOAN":
        return "loan"

    # 3. Resume completed EMI if user updates values
    if (
        cs.last_completed_flow
        and cs.last_completed_flow["flow"] == "EMI"
    ):
        extracted = extract_emi_slots(state["user_input"])
        if any(v is not None for v in extracted.values()):
            cs.active_flow = "EMI"
            cs.slots = cs.last_completed_flow["slots"].copy()
            cs.last_completed_flow = None
            return "emi"

    # 4. Fresh intent routing
    action = route_intent(cs, state["user_input"])
    if action == "START_EMI":
        cs.reset_flow()
        cs.active_flow = "EMI"
        return "emi"

    if action == "START_LOAN":
        cs.reset_flow()
        cs.active_flow = "LOAN"
        return "loan"

    # 5. Default → RAG
    return "rag"

# -------------------------
# Build Graph
# -------------------------
def build_graph():
    graph = StateGraph(GraphState)

    # Add actual processing nodes
    graph.add_node("emi", emi_node)
    graph.add_node("loan", loan_node)
    graph.add_node("rag", rag_node)
    graph.add_node("reset", reset_node)

    # Set entry point and route directly using policy function
    graph.set_entry_point("router")
    
    # Create a dummy router node if needed, or route from START
    graph.add_node("router", lambda s: s)  # Or just use conditional_entry_point
    
    graph.add_conditional_edges(
        "router",
        policy,
        {
            "emi": "emi",
            "loan": "loan",
            "rag": "rag",
            "reset": "reset",
        },
    )

    graph.add_edge("emi", END)
    graph.add_edge("loan", END)
    graph.add_edge("rag", END)
    graph.add_edge("reset", END)

    return graph.compile()