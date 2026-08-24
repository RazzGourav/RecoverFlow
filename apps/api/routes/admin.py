from fastapi import APIRouter, Request
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/reconcile-now")
async def trigger_reconciliation(request: Request):
    """
    Manual trigger for the reconciliation worker.
    Used purely for demo/dev purposes so we aren't at the mercy of a cron timer.
    """
    logger.info("admin.manual_reconciliation_triggered")
    
    # Enqueue the worker function asynchronously via Redis (arq)
    await request.app.state.arq_pool.enqueue_job("verify_executed_actions")
    
    return {"status": "success", "message": "Reconciliation job triggered in the background."}
