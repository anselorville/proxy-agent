"""Scheduled Celery tasks for data fetching."""

from celery.schedules import crontab
import logging
from datetime import datetime, timedelta

from src.tasks.celery_app import celery_app
from src.services.data_fetcher import DataFetcher
from src.utils.proxy_pool import ProxyManager
from src.utils.frequency_control import FrequencyController
from src.models.database import SessionLocal
from src.models.stock_data import DailyQuote, Stock, FetchHistory

logger = logging.getLogger(__name__)


@celery_app.task(name="fetch_daily_data")
def fetch_daily_data_task():
    """
    Fetch daily stock data (scheduled at 15:05).

    This task runs every weekday at 15:05 (after market close)
    to fetch the latest trading data for all stocks.
    """
    logger.info("Starting scheduled daily data fetch...")

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

        proxy_manager = ProxyManager()
        frequency_controller = FrequencyController()
        data_fetcher = DataFetcher(proxy_manager, frequency_controller)

        stock_list = db.query(Stock).filter(Stock.is_st is False).all()
        logger.info(f"Found {len(stock_list)} non-ST stocks to fetch")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        for stock in stock_list:
            try:
                stock_code = stock.stock_code
                logger.info(f"Fetching data for {stock_code} - {stock.stock_name}")

                df = data_fetcher.fetch_daily_quotes(
                    stock_code=stock_code,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust="qfq"
                )

                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        quote = DailyQuote(
                            stock_code=stock_code,
                            date=datetime.strptime(row['日期'], "%Y-%m-%d"),
                            open_price=float(row['开盘']),
                            high_price=float(row['最高']),
                            low_price=float(row['最低']),
                            close_price=float(row['收盘']),
                            volume=int(row['成交量']),
                            amount=float(row['成交额']),
                            adjust_factor=1.0
                        )
                        db.merge(quote)
                        records_inserted += 1

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

        return {"status": "failed", "error": str(e)}

    finally:
        db.close()


@celery_app.task(name="manual_fetch")
def manual_fetch_task(stock_codes: list = None):
    """
    Manually trigger data fetch.

    Args:
        stock_codes: Optional list of specific stock codes to fetch.
                     If None, fetch all stocks.
    """
    logger.info(f"Starting manual data fetch for {len(stock_codes) if stock_codes else 'all'} stocks...")

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

        proxy_manager = ProxyManager()
        frequency_controller = FrequencyController()
        data_fetcher = DataFetcher(proxy_manager, frequency_controller)

        if stock_codes:
            stock_list = db.query(Stock).filter(Stock.stock_code.in_(stock_codes)).all()
        else:
            stock_list = db.query(Stock).filter(Stock.is_st is False).all()

        logger.info(f"Found {len(stock_list)} stocks to fetch")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        for stock in stock_list:
            try:
                stock_code = stock.stock_code
                logger.info(f"Fetching data for {stock_code} - {stock.stock_name}")

                df = data_fetcher.fetch_daily_quotes(
                    stock_code=stock_code,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust="qfq"
                )

                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        quote = DailyQuote(
                            stock_code=stock_code,
                            date=datetime.strptime(row['日期'], "%Y-%m-%d"),
                            open_price=float(row['开盘']),
                            high_price=float(row['最高']),
                            low_price=float(row['最低']),
                            close_price=float(row['收盘']),
                            volume=int(row['成交量']),
                            amount=float(row['成交额']),
                            adjust_factor=1.0
                        )
                        db.merge(quote)
                        records_inserted += 1

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
