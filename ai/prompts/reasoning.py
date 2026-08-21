from pydantic import BaseModel, Field


class ExplanationResult(BaseModel):
    narrative: str = Field(
        description="A human-readable explanation of what happened, why the action was selected, and any alternatives considered. Max 500 characters."
    )
    reason_codes: list[str] = Field(
        description="A list of machine-readable reason codes for the decision (e.g., ['HIGH_RECOVERABILITY', 'COOLDOWN_ACTIVE'])."
    )

REASONING_PROMPT_TEMPLATE = """You are the AI Reasoning Engine for RecoverFlow, a payments recovery control plane.

Your job is to explain the decision made by our deterministic policy engine.
You MUST NOT change the decision, you are simply explaining it.

CASE CONTEXT:
- Amount: {amount_paise} paise
- Failure Type: {failure_type}
- AI Recoverability Score (P(success)): {recoverability_score}
- Risk Level: {risk_level}

POLICY ENGINE DECISION:
- Selected Action: {action_type}
- Authorization Status: {authorization_status}
- Blocking Reason (if any): {reason}

Produce a structured JSON response containing:
1. `narrative`: A clear, professional explanation of why this action was selected based on the case context and policy outcome. (e.g., "The payment of X was selected for RETRY because its recoverability score is high (Y). The action was authorized autonomously.")
2. `reason_codes`: A list of 1-3 concise reason codes explaining the context (e.g., ["HIGH_RECOVERABILITY", "AUTONOMOUS_LIMIT_CLEARED"]).

Remember, output strictly valid JSON matching the schema.
"""
