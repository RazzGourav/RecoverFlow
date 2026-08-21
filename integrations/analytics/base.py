import abc
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class FunnelSummaryNode(BaseModel):
    stage: str
    count: int
    dropoff_rate_percent: Optional[float]
    value_paise: int

class EventTrackingProvider(abc.ABC):
    """
    Abstract interface for analytics/funnel event tracking.
    Currently implemented by SyntheticProvider backed by our local database.
    In the future, a GA4Provider or SegmentProvider could implement this interface.
    """

    @abc.abstractmethod
    async def track_event(
        self,
        session_id: str,
        event_type: str,
        timestamp: datetime,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Record a top-of-funnel tracking event.
        Must be idempotent on (session_id, event_type, timestamp).
        """
        pass

    @abc.abstractmethod
    async def get_funnel_summary(self) -> List[FunnelSummaryNode]:
        """
        Compute the funnel aggregation: stage counts, drop-offs, and values.
        """
        pass
