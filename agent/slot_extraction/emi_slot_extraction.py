# agent/slot_extraction/emi_slot_extraction.py

import json
from typing import Dict, Optional
from agent.llm_vertex import llm_generate


def extract_emi_slots(user_message: str) -> Dict[str, Optional[float]]:
    system_prompt = """
You are a strict information extraction engine.

Extract EMI-related values ONLY if explicitly present.
Do NOT guess or infer missing information.

Fields:
- principal: loan amount (number)
- rate: annual interest rate percentage
- tenure_months: loan tenure in months (integer)

Conversion rules:
- If tenure is given in years, convert to months.
- If tenure is already in months, use as is.

Return ONLY valid JSON:
{
  "principal": null,
  "rate": null,
  "tenure_months": null
}
"""

    prompt = f"""
{system_prompt}

User message:
"{user_message}"
"""

    try:
        raw = llm_generate(prompt)

        # --- Extract JSON safely ---
        start = raw.find("{")
        end = raw.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("No JSON found in LLM output")

        data = json.loads(raw[start:end + 1])
    except Exception as e:
        print("[EMI SLOT EXTRACTION FAILED]", e)
        return {"principal": None, "rate": None, "tenure_months": None}

    return {
        "principal": _to_float(data.get("principal")),
        "rate": _to_float(data.get("rate")),
        "tenure_months": _to_int(data.get("tenure_months")),
    }


def _to_float(v):
    try:
        return float(v)
    except:
        return None


def _to_int(v):
    try:
        return int(v)
    except:
        return None
