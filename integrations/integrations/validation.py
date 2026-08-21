"""
RecoverFlow API — Payment Provider Validation Base

Why this file exists:
  Provides the validation contracts and models for the Phase 7.5 Validation Layer.
  This allows checking if a recommended action is still valid against the live state
  before money actually moves or actions execute.
"""

from __future__ import annotations
import enum
from dataclasses import dataclass


class ValidationStatus(str, enum.Enum):
    """Outcomes of a live state validation check."""
    VALID = "VALID"
    INVALID_STATE = "INVALID_STATE"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class ValidationOutcome:
    """Result returned by the validation layer."""
    status: ValidationStatus
    reason: str
