#emi.py
"""
Standalone EMI calculation flow.
Ask user for all required fields in sequence,
validate inputs, and calculate EMI + amortization.

This does NOT use LLM — this ensures deterministic behavior.
"""
import math

# ------------------------------------
# 1. EMI core formulas
# ------------------------------------
def calculate_emi(principal, annual_rate_pct, tenure_months):
    monthly_rate = (annual_rate_pct / 100) / 12
    emi = (principal * monthly_rate * (1 + monthly_rate)**tenure_months) / (
        (1 + monthly_rate)**tenure_months - 1
    )

    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    return round(emi, 2), round(total_payment, 2), round(total_interest, 2)


def amortization_schedule(principal, annual_rate_pct, tenure_months, rows=6):
    monthly_rate = (annual_rate_pct / 100) / 12
    emi, _, _ = calculate_emi(principal, annual_rate_pct, tenure_months)

    schedule = []
    balance = principal

    for month in range(1, rows + 1):
        interest = balance * monthly_rate
        principal_comp = emi - interest
        closing_balance = balance - principal_comp

        schedule.append({
            "month": month,
            "opening": round(balance, 2),
            "emi": round(emi, 2),
            "interest": round(interest, 2),
            "closing": round(closing_balance, 2)
        })

        balance = closing_balance

    return schedule


# ------------------------------------
# 2. Single-turn EMI Tool
# ------------------------------------
def emi_tool(principal, rate, tenure_months):
    """
    Deterministic EMI calculation tool.
    Returns pure structured data.
    LLM will format the human-readable output.
    """

    # Validate inputs
    if principal <= 0:
        return {"error": "Principal must be greater than zero."}

    if rate <= 0:
        return {"error": "Rate must be greater than zero."}

    if tenure_months <= 0:
        return {"error": "Tenure must be greater than zero."}

    # Compute financials
    emi, total_payment, total_interest = calculate_emi(principal, rate, tenure_months)
    schedule = amortization_schedule(principal, rate, tenure_months)

    # Structured output (NO strings)
    return {
        "principal": round(principal, 2),
        "rate": round(rate, 2),
        "tenure_months": tenure_months,
        "emi": emi,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "schedule_preview": schedule,  # LLM decides how much to show
    }
