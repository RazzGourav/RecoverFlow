"""
Immutable Decision Logger

Why this exists:
  Every autonomous or human-escalated decision in the system must be fully traceable.
  This module constructs the `AuditEvent` and persists it, guaranteeing
  compliance with Rule 6 (Safety Rails are Code).
"""

import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.models import AuditEvent, AuditEventType

async def log_decision(
    session: AsyncSession,
    case_id: str,
    action_type: str,
    decision: str,
    reason: str,
    model_version: str,
    policy_version: str,
    context: Dict[str, Any]
) -> AuditEvent:
    """
    Creates and persists an immutable audit log entry for a policy decision.
    
    Args:
        session: SQLAlchemy async session.
        case_id: UUID string of the RecoveryCase.
        action_type: The CandidateAction type that was evaluated.
        decision: The AuthorizationStatus ('AUTONOMOUS', 'AWAITING_HUMAN', 'BLOCKED').
        reason: The reason code from the policy engine.
        model_version: Version of the AI model that proposed the action.
        policy_version: Version of the Policy that evaluated it.
        context: Additional structured data (e.g. amounts, probabilities).
        
    Returns:
        The created AuditEvent object.
    """
    
    # Map decision to AuditEventType
    event_type = AuditEventType.POLICY_EVALUATED
    if decision == "AUTONOMOUS":
        event_type = AuditEventType.ACTION_AUTHORIZED
    elif decision == "BLOCKED":
        event_type = AuditEventType.ACTION_BLOCKED
    elif decision == "AWAITING_HUMAN":
        event_type = AuditEventType.HUMAN_ESCALATION

    audit_event = AuditEvent(
        case_id=uuid.UUID(case_id),
        event_type=event_type,
        model_version=model_version,
        policy_version=policy_version,
        decision=decision,
        reason=reason,
        context={
            "action_type": action_type,
            **context
        }
    )
    
    session.add(audit_event)
    await session.flush()
    return audit_event
