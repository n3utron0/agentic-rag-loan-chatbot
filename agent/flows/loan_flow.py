# agent/flows/loan_flow.py

from typing import Dict, Any
from agent.state import ConversationState
from agent.slot_extraction.loan_slot_extraction import extract_loan_slots


# Fixed order — like EMI
LOAN_FIELDS = [
    "loan_type",
    "age",
    "employment_type",
    "monthly_income",
    "monthly_expenses",
    "tenure_years",
]


def handle_loan_turn(state: ConversationState, user_message: str) -> Dict[str, Any]:
    """
    Strict form-based loan eligibility flow.
    Mirrors emi_flow behavior exactly.
    """

    # -----------------------------------------
    # 1. If awaiting a specific field
    # -----------------------------------------
    if state.awaiting_field:
        field = state.awaiting_field
        text = user_message.strip()

        # --- numeric fast-path (like EMI) ---
        try:
            value = normalize_indian_amount(text)
            if value is None:
                raise ValueError

            if field in ("age", "tenure_years"):
                value = int(value)

            # After assigning the value
            state.slots[field] = value
            state.awaiting_field = None

            # IMMEDIATELY ask next question
            for next_field in LOAN_FIELDS:
                if next_field not in state.slots:
                    state.awaiting_field = next_field
                    return {
                        "response": _question_for(next_field),
                        "tool_output": None,
                        "interrupt": False,
                    }

            # If no fields left, calculate now
            result = _calculate_eligibility(state.slots)
            return {
                "response": _format_result(result),
                "tool_output": result,
                "interrupt": False,
            }

        except ValueError:
            pass  # try LLM extraction below

        # --- contextual extraction fallback ---
        extracted = extract_loan_slots(user_message)
        value = extracted.get(field)

        if value is not None:
            state.slots[field] = value
            state.awaiting_field = None

            # Immediately ask the next missing field
            for next_field in LOAN_FIELDS:
                if next_field not in state.slots:
                    state.awaiting_field = next_field
                    return {
                        "response": _question_for(next_field),
                        "tool_output": None,
                        "interrupt": False,
                    }

            # If no fields left, calculate immediately
            result = _calculate_eligibility(state.slots)
            return {
                "response": _format_result(result),
                "tool_output": result,
                "interrupt": False,
            }


        # still missing → re-ask SAME question
        return {
            "response": _question_for(field),
            "tool_output": None,
            "interrupt": False,
        }

    # -----------------------------------------
    # 2. No awaiting field → extract once
    # -----------------------------------------
    extracted = extract_loan_slots(user_message)
    for k, v in extracted.items():
        if v is not None:
            state.slots[k] = v

    # -----------------------------------------
    # 3. Ask next missing field (strict order)
    # -----------------------------------------
    for field in LOAN_FIELDS:
        if field not in state.slots:
            state.awaiting_field = field
            return {
                "response": _question_for(field),
                "tool_output": None,
                "interrupt": False,
            }

    # -----------------------------------------
    # 4. All fields present → calculate
    # -----------------------------------------
    result = _calculate_eligibility(state.slots)

    return {
        "response": _format_result(result),
        "tool_output": result,
        "interrupt": False,
    }


# -------------------------------------------------
# Eligibility calculation (with employment type logic)
# -------------------------------------------------
def _calculate_eligibility(slots: Dict[str, Any]) -> Dict[str, Any]:
    age = slots["age"]
    tenure = slots["tenure_years"]

    if age < 21 or age > 65:
        return {"eligible": False, "reason": "Age not eligible"}

    if tenure > (65 - age):
        return {"eligible": False, "reason": "Tenure exceeds retirement age"}

    net_income = slots["monthly_income"] - slots["monthly_expenses"]
    if net_income <= 0:
        return {"eligible": False, "reason": "Insufficient income"}

    # Employment type multiplier: salaried gets full amount, self-employed gets 85%
    employment_type = slots.get("employment_type", "").lower()
    if "self" in employment_type or "self-employed" in employment_type:
        income_multiplier = 0.85  # 85% for self-employed
    else:
        income_multiplier = 1.0  # 100% for salaried

    eligible_emi = net_income * 0.5 * income_multiplier

    annual_rate = 8.75
    monthly_rate = annual_rate / (12 * 100)
    months = tenure * 12

    principal = (
        eligible_emi
        * ((1 + monthly_rate) ** months - 1)
        / (monthly_rate * (1 + monthly_rate) ** months)
    )

    return {
        "eligible": True,
        "eligible_amount": round(principal),
        "net_income": round(net_income),
        "eligible_emi": round(eligible_emi),
        "tenure_years": tenure,
        "employment_type": slots["employment_type"],
    }


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _question_for(field: str) -> str:
    return {
        "loan_type": "Is this a fresh home loan or a balance transfer?",
        "age": "What is your age?",
        "employment_type": "Are you salaried or self-employed?",
        "monthly_income": "What is your monthly income?",
        "monthly_expenses": "What are your monthly expenses including EMIs?",
        "tenure_years": "For how many years do you want the loan?",
    }[field]


def _format_result(result: Dict[str, Any]) -> str:
    if not result["eligible"]:
        return f"You are not eligible for a home loan.\nReason: {result['reason']}"

    return (
        f"You may be eligible for a home loan of approximately "
        f"₹{result['eligible_amount']:,}.\n"
        f"Net Monthly Income: ₹{result['net_income']}\n"
        f"Eligible EMI: ₹{result['eligible_emi']}\n"
        f"Tenure: {result['tenure_years']} years\n"
        "\033[1mTo change loan eligibility parameters, please type 'reset' or 'clear loan values'\033[0m."
    )

def normalize_indian_amount(text: str):
    text = text.lower().replace(",", "").strip()

    if "lakh" in text:
        num = float(text.split()[0])
        return num * 100000

    if "crore" in text:
        num = float(text.split()[0])
        return num * 10000000

    try:
        return float(text)
    except:
        return None