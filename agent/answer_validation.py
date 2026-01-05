# agent/answer_validation.py

import json
from typing import Dict, Optional
from agent.llm_vertex import llm_generate


def validate_answer(expected_field: str, user_message: str) -> Dict[str, Optional[float]]:
    system_prompt = f"""
You are validating whether a user message answers a specific question.

Expected field: {expected_field}

Rules:
- Respond ONLY in valid JSON.
- Do NOT guess.
- If the message does not clearly answer the expected field, return is_answer=false.
- If it answers, extract and normalize the value.

JSON format:
{{
  "is_answer": false,
  "value": null
}}
"""

    prompt = f"""
{system_prompt}

User message:
"{user_message}"
"""

    try:
        raw = llm_generate(prompt)
        data = json.loads(raw)
    except Exception:
        return {"is_answer": False, "value": None}

    if not data.get("is_answer"):
        return {"is_answer": False, "value": None}

    value = data.get("value")

    try:
        value = int(value) if expected_field == "tenure_months" else float(value)
    except:
        return {"is_answer": False, "value": None}

    return {"is_answer": True, "value": value}
