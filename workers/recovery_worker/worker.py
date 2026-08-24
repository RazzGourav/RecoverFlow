"""
RecoverFlow — Recovery Worker

Why this file exists:
  Provides the arq worker for executing recovery actions (e.g., sending payment links).
  Actions are processed asynchronously to avoid blocking the decision pipeline and
  to safely handle external API timeouts or errors.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from arq.connections import RedisSettings
from arq.cron import cron
from config import settings
from db.models import Action, AuthorizationStatus, ExecutionStatus
from db.session import AsyncSessionLocal
from sqlalchemy import select

from domain.finance.executor import execute_action

logger = structlog.get_logger(__name__)


async def dispatch_action_job(ctx: dict, action_id: str) -> None:
    """
    Executes a single action. Invoked by the decision pipeline.
    """
    logger.info("worker.dispatch_action.started", action_id=action_id)
    
    async with AsyncSessionLocal() as session:
        try:
            await execute_action(session, uuid.UUID(action_id))
            logger.info("worker.dispatch_action.success", action_id=action_id)
        except Exception as e:
            logger.exception("worker.dispatch_action.error", action_id=action_id, exc_info=e)
            raise


async def poll_pending_actions(ctx: dict) -> None:
    """
    Cron job: Finds actions stuck in PENDING state (e.g. if a direct job was lost)
    and executes them. We look for actions older than 1 minute to avoid racing
    with the immediate dispatch jobs.
    """
    logger.info("worker.poll_pending.started")
    
    async with AsyncSessionLocal() as session:
        one_minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
        
        stmt = (
            select(Action.id)
            .where(
                Action.execution_status == ExecutionStatus.PENDING,
                Action.authorization_status.in_([
                    AuthorizationStatus.AUTONOMOUS,
                    AuthorizationStatus.APPROVED
                ]),
                Action.created_at <= one_minute_ago,
            )
            .limit(50)
        )
        
        result = await session.execute(stmt)
        pending_ids = result.scalars().all()
        
        if not pending_ids:
            logger.info("worker.poll_pending.no_actions")
            return
            
        logger.info("worker.poll_pending.found_actions", count=len(pending_ids))
        
        # We dispatch them locally using the same execute_action function
        # since we are already inside the worker.
        for action_id in pending_ids:
            try:
                await execute_action(session, action_id)
            except Exception as e:
                logger.error("worker.poll_pending.action_error", action_id=str(action_id), error=str(e))
                # Continue processing others


# ARQ worker settings
class WorkerSettings:
    queue_name = "arq:recovery_queue"
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [dispatch_action_job]
    cron_jobs = [
        cron(poll_pending_actions, minute=set(range(60)))  # Run every minute
    ]
    max_jobs = settings.worker_concurrency
