"""
Risk Firewall Scorer

Why this exists:
  Assesses contextual risk before authorizing autonomous action. 
  Uses an auditable rules engine (with lightweight heuristics) to classify 
  risk as LOW, MEDIUM, or HIGH, satisfying PRD Module D requirements.
"""

from typing import Any


def score_risk(case_data: dict[str, Any]) -> tuple[str, list[str]]:
    """
    Evaluates a case and returns the RiskLevel and reason codes.
    
    Args:
        case_data: Raw dictionary of case attributes.
        
    Returns:
        (RiskLevel string, list of reason codes)
    """
    reasons = []
    level = "LOW"
    
    amount = float(case_data.get("amount_paise", 0))
    segment = case_data.get("segment", "UNKNOWN")
    failure_type = case_data.get("failure_type", "UNKNOWN")
    high_freq = case_data.get("high_frequency_contact", False)
    
    # Rule 1: High frequency contact indicates policy violation / spam risk
    if high_freq:
        level = "HIGH"
        reasons.append("RISK_HIGH_FREQUENCY")
        
    # Rule 2: Exceptionally high amounts are inherently high risk for autonomous actions
    if amount > 2_500_000:
        level = "HIGH"
        reasons.append("RISK_HIGH_AMOUNT")
        
    # Rule 3: Customer action failures (e.g., authentication required) have medium risk of churn if handled poorly
    if failure_type == "CUSTOMER_ACTION" and level == "LOW":
        level = "MEDIUM"
        reasons.append("RISK_CUSTOMER_FRICTION")
        
    # Rule 4: New customers with very high amounts get a medium risk bump if not already high
    if segment == "NEW" and amount > 500_000 and level == "LOW":
        level = "MEDIUM"
        reasons.append("RISK_NEW_USER_LARGE_AMOUNT")
        
    if not reasons:
        reasons.append("RISK_NORMAL")
        
    return level, reasons
