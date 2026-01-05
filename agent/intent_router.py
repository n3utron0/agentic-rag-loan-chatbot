# agent/intent_router.py

import json
from typing import Literal
from agent.llm_vertex import llm_generate
from agent.state import ConversationState

RouterDecision = Literal[
    "START_EMI",
    "START_LOAN",
    "USE_RAG",
    "RESUME_PAUSED_FLOW"
]


def route_intent(state: ConversationState, user_message: str) -> RouterDecision:
    system_prompt = """
You are an intent routing engine for a banking chatbot.

Decide ONE action:
- START_EMI (only if user message contains calculate/check EMI or gives numbers)
- START_LOAN (only if user message contains: eligible/calculate/check/apply AND "home loan" OR "loan")
- USE_RAG (for explanations, info, definitions, policies, documents, cards, etc.)

IMPORTANT:
- Do NOT choose START_EMI for general EMI information.
- Do NOT choose START_LOAN for general  or loan info.
- If unsure, choose USE_RAG.

Return ONLY JSON:
{ "action": "START_EMI | START_LOAN | USE_RAG" }
"""

    prompt = f"""
{system_prompt}

User message:
"{user_message}"
"""

    try:
        raw = llm_generate(prompt)

        # 🔒 Robust JSON extraction (THIS IS THE FIX)
        start = raw.find("{")
        end = raw.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("No JSON found")

        data = json.loads(raw[start:end + 1])

        action = data.get("action")

        if action in ("START_EMI", "START_LOAN", "USE_RAG"):
            return action

        raise ValueError("Invalid action")

    except Exception as e:
        print("[INTENT ROUTER ERROR]", raw)
        return "USE_RAG"