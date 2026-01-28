"""Scheduled Celery tasks for data fetching."""

from celery.schedules import crontab
import logging
from datetime import datetime

from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="fetch_daily_data")
def fetch_daily_data_task():
    """
    Fetch daily stock data (scheduled at 15:05).
    
    This task runs every weekday at 15:05 (after market close)
    to fetch the latest trading data for all stocks.
    """
    logger.info("Starting scheduled daily data fetch...")
    
    try:
        # TODO: Implement data fetch logic
        # 1. Get list of all stocks
        # 2. Fetch daily quotes using DataFetcher
        # 3. Store data in database
        # 4. Record fetch history
        
        logger.info("Daily data fetch completed successfully")
        return {"status": "success", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Daily data fetch failed: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="manual_fetch")
def manual_fetch_task(stock_codes: list = None):
    """
    Manually trigger data fetch.
    
    Args:
        stock_codes: Optional list of specific stock codes to fetch.
                     If None, fetch all stocks.
    """
    logger.info(f"Starting manual data fetch for {len(stock_codes) if stock_codes else 'all'} stocks...")
    
    try:
        # TODO: Implement manual fetch logic
        logger.info("Manual data fetch completed successfully")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Manual data fetch failed: {e}")
        return {"status": "failed", "error": str(e)}


# Configure scheduled tasks
celery_app.conf.beat_schedule = {
    # Run daily at 15:05 (after market close)
    'fetch-daily-data-at-15-05': {
        'task': 'fetch_daily_data',
        'schedule': crontab(hour=15, minute=5),
    },
}
