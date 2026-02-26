"""Scheduled Celery tasks for data fetching."""

from celery.schedules import crontab
import logging
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram
from typing import Optional

from src.tasks.celery_app import celery_app
from src.core.settings import settings
from src.services.data_fetcher import DataFetcher
from src.utils.proxy_pool import ProxyManager
from src.utils.frequency_control import FrequencyController
from src.models.database import SessionLocal
from src.models.stock_data import DailyQuote, Stock, FetchHistory

logger = logging.getLogger(__name__)

task_runs_total = Counter("celery_task_runs_total", "Total Celery task runs", ["task", "status"])
task_duration_seconds = Histogram("celery_task_duration_seconds", "Celery task duration", ["task"])


def _requests_per_second() -> float:
    if settings.request_interval <= 0:
        return 1.0
    return 1.0 / settings.request_interval


def _upsert_quotes(db, stock_code: str, df) -> int:
    if df is None or df.empty:
        return 0

    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "date": datetime.strptime(row["日期"], "%Y-%m-%d"),
                "open_price": float(row["开盘"]),
                "high_price": float(row["最高"]),
                "low_price": float(row["最低"]),
                "close_price": float(row["收盘"]),
                "volume": int(row["成交量"]),
                "amount": float(row["成交额"]),
                "adjust_factor": 1.0,
            }
        )

    inserted_or_updated = 0
    batch_size = max(1, settings.data_fetch_batch_size)
    for i in range(0, len(records), batch_size):
        chunk = records[i:i + batch_size]
        existing_dates = [item["date"] for item in chunk]
        existing_rows = db.query(DailyQuote).filter(
            DailyQuote.stock_code == stock_code,
            DailyQuote.date.in_(existing_dates),
        ).all()
        existing_map = {item.date: item for item in existing_rows}

        for item in chunk:
            existing = existing_map.get(item["date"])
            if existing:
                existing.open_price = item["open_price"]
                existing.high_price = item["high_price"]
                existing.low_price = item["low_price"]
                existing.close_price = item["close_price"]
                existing.volume = item["volume"]
                existing.amount = item["amount"]
                existing.adjust_factor = item["adjust_factor"]
            else:
                db.add(
                    DailyQuote(
                        stock_code=stock_code,
                        date=item["date"],
                        open_price=item["open_price"],
                        high_price=item["high_price"],
                        low_price=item["low_price"],
                        close_price=item["close_price"],
                        volume=item["volume"],
                        amount=item["amount"],
                        adjust_factor=item["adjust_factor"],
                    )
                )
            inserted_or_updated += 1

    return inserted_or_updated


@celery_app.task(name="fetch_daily_data")
def fetch_daily_data_task():
    """
    Fetch daily stock data (scheduled at 15:05).

    This task runs every weekday at 15:05 (after market close)
    to fetch the latest trading data for all stocks.
    """
    logger.info("Starting scheduled daily data fetch...")
    task_started = datetime.utcnow()
    task_name = "fetch_daily_data"

    db = SessionLocal()
    fetch_history = None
    stocks_processed = 0
    records_inserted = 0

    try:
        fetch_history = FetchHistory(
            fetch_type="scheduled",
            started_at=datetime.utcnow(),
            status="running",
            stocks_processed=0,
            records_inserted=0
        )
        db.add(fetch_history)
        db.commit()

        proxy_manager = ProxyManager(pool_size=settings.proxy_pool_size)
        frequency_controller = FrequencyController(requests_per_second=_requests_per_second())
        data_fetcher = DataFetcher(proxy_manager, frequency_controller)

        stock_list = db.query(Stock).filter(Stock.is_st.is_(False)).all()
        logger.info(f"Found {len(stock_list)} non-ST stocks to fetch")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        for stock in stock_list:
            try:
                stock_code = str(stock.stock_code)
                logger.info(f"Fetching data for {stock_code} - {stock.stock_name}")

                df = data_fetcher.fetch_daily_quotes(
                    stock_code=stock_code,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust="qfq",
                    max_retries=settings.max_retries,
                )

                if df is not None and not df.empty:
                    records_inserted += _upsert_quotes(db, stock_code, df)

                    db.commit()
                    logger.info(f"Inserted/Updated {len(df)} records for {stock_code}")

                stocks_processed += 1

            except Exception as e:
                logger.error(f"Failed to process stock {stock.stock_code}: {e}")
                db.rollback()

        fetch_history.status = "success"
        fetch_history.completed_at = datetime.utcnow()
        fetch_history.stocks_processed = stocks_processed
        fetch_history.records_inserted = records_inserted
        db.commit()

        logger.info(f"Daily data fetch completed successfully. Processed {stocks_processed} stocks, "
                    f"inserted {records_inserted} records")
        task_runs_total.labels(task_name, "success").inc()
        task_duration_seconds.labels(task_name).observe((datetime.utcnow() - task_started).total_seconds())
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "stocks_processed": stocks_processed,
            "records_inserted": records_inserted
        }

    except Exception as e:
        logger.error(f"Daily data fetch failed: {e}")
        db.rollback()

        if fetch_history:
            fetch_history.status = "failed"
            fetch_history.completed_at = datetime.utcnow()
            fetch_history.error_message = str(e)
            db.commit()

        task_runs_total.labels(task_name, "failed").inc()
        task_duration_seconds.labels(task_name).observe((datetime.utcnow() - task_started).total_seconds())
        return {"status": "failed", "error": str(e)}

    finally:
        db.close()


@celery_app.task(name="manual_fetch")
def manual_fetch_task(stock_codes: Optional[list] = None):
    """
    Manually trigger data fetch.

    Args:
        stock_codes: Optional list of specific stock codes to fetch.
                     If None, fetch all stocks.
    """
    logger.info(f"Starting manual data fetch for {len(stock_codes) if stock_codes else 'all'} stocks...")
    task_started = datetime.utcnow()
    task_name = "manual_fetch"

    db = SessionLocal()
    fetch_history = None
    stocks_processed = 0
    records_inserted = 0

    try:
        fetch_history = FetchHistory(
            fetch_type="manual",
            started_at=datetime.utcnow(),
            status="running",
            stocks_processed=0,
            records_inserted=0
        )
        db.add(fetch_history)
        db.commit()

        proxy_manager = ProxyManager(pool_size=settings.proxy_pool_size)
        frequency_controller = FrequencyController(requests_per_second=_requests_per_second())
        data_fetcher = DataFetcher(proxy_manager, frequency_controller)

        if stock_codes:
            stock_list = db.query(Stock).filter(Stock.stock_code.in_(stock_codes)).all()
        else:
            stock_list = db.query(Stock).filter(Stock.is_st.is_(False)).all()

        logger.info(f"Found {len(stock_list)} stocks to fetch")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        for stock in stock_list:
            try:
                stock_code = str(stock.stock_code)
                logger.info(f"Fetching data for {stock_code} - {stock.stock_name}")

                df = data_fetcher.fetch_daily_quotes(
                    stock_code=stock_code,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust="qfq",
                    max_retries=settings.max_retries,
                )

                if df is not None and not df.empty:
                    records_inserted += _upsert_quotes(db, stock_code, df)

                    db.commit()
                    logger.info(f"Inserted/Updated {len(df)} records for {stock_code}")

                stocks_processed += 1

            except Exception as e:
                logger.error(f"Failed to process stock {stock.stock_code}: {e}")
                db.rollback()

        fetch_history.status = "success"
        fetch_history.completed_at = datetime.utcnow()
        fetch_history.stocks_processed = stocks_processed
        fetch_history.records_inserted = records_inserted
        db.commit()

        logger.info(f"Manual data fetch completed successfully. Processed {stocks_processed} stocks, "
                    f"inserted {records_inserted} records")
        task_runs_total.labels(task_name, "success").inc()
        task_duration_seconds.labels(task_name).observe((datetime.utcnow() - task_started).total_seconds())
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "stocks_processed": stocks_processed,
            "records_inserted": records_inserted
        }

    except Exception as e:
        logger.error(f"Manual data fetch failed: {e}")
        db.rollback()

        if fetch_history:
            fetch_history.status = "failed"
            fetch_history.completed_at = datetime.utcnow()
            fetch_history.error_message = str(e)
            db.commit()

        task_runs_total.labels(task_name, "failed").inc()
        task_duration_seconds.labels(task_name).observe((datetime.utcnow() - task_started).total_seconds())
        return {"status": "failed", "error": str(e)}

    finally:
        db.close()


# Configure scheduled tasks
celery_app.conf.beat_schedule = {
    # Run daily at 15:05 (after market close)
    'fetch-daily-data-at-15-05': {
        'task': 'fetch_daily_data',
        'schedule': crontab(hour=15, minute=5),
    },
}
