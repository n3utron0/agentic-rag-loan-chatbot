#loan.py
"""
Standalone Home Loan Eligibility Flow (Preview + Final).
Strict step-by-step input.
No LLM. Deterministic behavior.
"""
from datetime import datetime

# ---------------------------
# 1. Helper: Calculate age
# ---------------------------
def calculate_age(dob: str):
    """
    dob format: YYYY-MM-DD
    """
    try:
        birth = datetime.strptime(dob, "%Y-%m-%d")
    except:
        raise ValueError("DOB must be in YYYY-MM-DD format.")

    today = datetime.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


# ---------------------------
# 2. Helper: Calculate multiplier (dynamic)
# ---------------------------
def determine_multiplier(employment: str, age: int):
    """
    Employment-based + age-based multiplier adjustments.
    """
    # base
    if employment == "salaried":
        multiplier = 60
    else:
        multiplier = 50

    # age adjustment
    if age < 30:
        multiplier *= 1.10   # +10%
    elif age > 45:
        multiplier *= 0.80   # -20%

    return multiplier


# ---------------------------
# 3. MAIN TOOL: loan_tool()
# ---------------------------
def loan_tool(
    loan_type: str,
    employment: str,
    income: float,
    obligations: float,
    dob: str,
    phone: str
):
    """
    Deterministic single-turn home loan eligibility calculator.
    All inputs are already extracted by LLM.
    """

    # Validate income/obligations
    if income <= 0:
        return {"error": "Income must be greater than zero."}

    if obligations < 0:
        return {"error": "Obligations cannot be negative."}

    # Validate phone
    if not phone.isdigit() or len(phone) != 10:
        return {"error": "Phone number must be 10 digits."}

    # Calculate age
    age = calculate_age(dob)

    # Net income
    net_income = income - obligations
    if net_income <= 0:
        return {"error": "Net income is insufficient for eligibility."}

    # Multiplier
    multiplier = determine_multiplier(employment, age)

    # Eligible amount
    eligible_amount = net_income * multiplier

    return {
        "loan_type": loan_type,
        "employment": employment,
        "income": income,
        "obligations": obligations,
        "dob": dob,
        "age": age,
        "phone": phone,
        "net_income": round(net_income, 2),
        "multiplier": round(multiplier, 2),
        "eligible_amount": round(eligible_amount, 2)
    }
