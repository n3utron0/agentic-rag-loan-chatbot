# agent/slot_extraction/loan_slot_extraction.py

import json
from typing import Dict, Optional
from agent.llm_vertex import llm_generate


def extract_loan_slots(user_message: str) -> Dict[str, Optional[object]]:
    """
    Extract loan-related slots if explicitly present.

    Slots:
    - loan_type: "fresh" | "balance_transfer"
    - age: int 
    - employment_type: "salaried" | "self_employed"
    - monthly_income: float
    - monthly_expenses: float
    - tenure_years: int

    Returns None for missing fields.
    """

    system_prompt = """
You are a strict information extraction engine.

Extract loan-related information ONLY if explicitly present.
Do NOT guess or infer missing values.

Slots:
- loan_type: "fresh" or "balance_transfer"
- age: integer (years (between 1 & 100))
- employment_type: "salaried" or "self_employed"
- monthly_income: number
- monthly_expenses: number (includes existing EMIs)
- tenure_years: integer

Return ONLY valid JSON in this format:
{
  "loan_type": null,
  "age": null,
  "employment_type": null,
  "monthly_income": null,
  "monthly_expenses": null,
  "tenure_years": null
}
"""

    prompt = f"""
{system_prompt}

User message:
"{user_message}"
"""

    try:
        raw = llm_generate(prompt)

        start = raw.find("{")
        end = raw.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("No JSON found")

        data = json.loads(raw[start:end + 1])

    except Exception:
        return {
            "loan_type": None,
            "age": None,
            "employment_type": None,
            "monthly_income": None,
            "monthly_expenses": None,
            "tenure_years": None
        }

    return {
        "loan_type": data.get("loan_type"),
        "age": _to_int(data.get("age")),
        "employment_type": data.get("employment_type"),
        "monthly_income": _to_float(data.get("monthly_income")),
        "monthly_expenses": _to_float(data.get("monthly_expenses")),
        "tenure_years": _to_int(data.get("tenure_years")),
    }


def _to_int(v):
    try:
        return int(v)
    except:
        return None


def _to_float(v):
    try:
        return float(v)
    except:
        return None
