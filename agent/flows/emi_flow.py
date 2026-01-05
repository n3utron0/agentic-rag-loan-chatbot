# agent/flows/emi_flow.py

from typing import Optional, Dict, Any

from agent.state import ConversationState
from agent.slot_extraction.emi_slot_extraction import extract_emi_slots
from agent.answer_validation import validate_answer

from tools.emi import emi_tool

import re

# Order matters — this defines the question sequence
REQUIRED_SLOTS = ["principal", "rate", "tenure_months"]



def handle_emi_turn(
    state: ConversationState,
    user_message: str
) -> Dict[str, Any]:
    """
    Handle one conversational turn inside EMI flow.

    Returns a dict with:
    {
        "response": str,
        "tool_output": dict | None,
        "interrupt": bool
    }
    """

    # -------------------------------------------------
    # 1. Slot extraction (ALWAYS runs)
    # -------------------------------------------------
    extracted = extract_emi_slots(user_message)

    # Replace slots if new values are found
    for field, value in extracted.items():
        if value is not None:
            state.slots[field] = value

    # -------------------------------------------------
    # 2. If awaiting a field → validate answer
    # -------------------------------------------------
    if state.awaiting_field:
        expected = state.awaiting_field

        # If slot extractor already captured it, accept
        if extracted.get(expected) is not None:
            state.awaiting_field = None

        else:
            # 🔒 Deterministic numeric fast-path
            if expected == "tenure_months":
                months = _parse_tenure_to_months(user_message)
                if months is not None:
                    state.slots["tenure_months"] = months
                    state.awaiting_field = None
                else:
                    return {
                        "response": _question_for(expected),
                        "tool_output": None,
                        "interrupt": False
                    }

            elif _is_pure_number(user_message):
                value = float(user_message)
                state.slots[expected] = value
                state.awaiting_field = None

            else:
                # Fallback to LLM validation
                validation = validate_answer(expected, user_message)

                if validation["is_answer"]:
                    state.slots[expected] = validation["value"]
                    state.awaiting_field = None

                else:
                    # Not an answer → signal interruption
                    return {
                        "response": None,
                        "tool_output": None,
                        "interrupt": True
                    }


    # -------------------------------------------------
    # 3. Check for missing slots
    # -------------------------------------------------
    for field in REQUIRED_SLOTS:
        if field not in state.slots:
            state.awaiting_field = field
            return {
                "response": _question_for(field),
                "tool_output": None,
                "interrupt": False
            }

    # -------------------------------------------------
    # 4. All slots present → run EMI tool
    # -------------------------------------------------
    principal = state.slots["principal"]
    rate = state.slots["rate"]
    tenure = state.slots["tenure_months"]

    result = emi_tool(
        principal=principal,
        rate=rate,
        tenure_months=tenure
    )

    # Clear awaiting field but keep slots (for corrections)
    state.awaiting_field = None

    return {
        "response": _format_emi_result(result),
        "tool_output": result,
        "interrupt": False
    }


# -------------------------------------------------
# Helper: Questions
# -------------------------------------------------
def _question_for(field: str) -> str:
    if field == "principal":
        return "What loan amount should I use for EMI calculation?"
    if field == "rate":
        return "What annual interest rate should I use?"
    if field == "tenure_months":
        return "What should be the loan tenure?"
    return "Please provide the required information."


# -------------------------------------------------
# Helper: Formatting (temporary, CLI-safe)
# -------------------------------------------------
def _format_emi_result(result: Dict[str, Any]) -> str:
    if "error" in result:
        return f"Error: {result['error']}"

    lines = [
        "Here is your EMI calculation:\n",
        f"Loan Amount: ₹{result['principal']}",
        f"Interest Rate: {result['rate']}%",
        f"Tenure: {result['tenure_months']} months\n",
        f"EMI: ₹{result['emi']}",
        f"Total Interest: ₹{result['total_interest']}",
        f"Total Payment: ₹{result['total_payment']}",
        "\nAmortization Schedule (First Few Months):"
    ]

    for row in result.get("schedule_preview", []):
        lines.append(
            f"Month {row['month']}: "
            f"Opening ₹{row['opening']} | "
            f"Interest ₹{row['interest']} | "
            f"EMI ₹{row['emi']} | "
            f"Closing ₹{row['closing']}"
        )

    return "\n".join(lines)


def _is_pure_number(text: str) -> bool:
    try:
        float(text.strip())
        return True
    except ValueError:
        return False

def _parse_tenure_to_months(text: str):
    """
    Parse tenure from text.
    Supports:
    - "1 year", "2 years"
    - "12 months"
    - "12"
    """
    t = text.lower().strip()

    # years
    match = re.search(r"(\d+)\s*(year|years)", t)
    if match:
        return int(match.group(1)) * 12

    # months
    match = re.search(r"(\d+)\s*(month|months)", t)
    if match:
        return int(match.group(1))

    # pure number fallback
    try:
        return int(float(t))
    except:
        return None

def looks_like_answer(expected_field: str, text: str) -> bool:
    """
    Decide if user input plausibly answers the awaited field.
    Deterministic, no LLM.
    """
    text = text.strip().lower()

    if expected_field in ("principal", "rate"):
        return _is_pure_number(text)

    if expected_field == "tenure_months":
        return (
            _is_pure_number(text)
            or "year" in text
            or "month" in text
        )

    return False
