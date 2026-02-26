"""Stock data endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.core.settings import settings
from src.models.database import get_db
from src.models.stock_data import DailyQuote, Stock

router = APIRouter()


@router.get("/list")
async def get_stock_list(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get list of all stocks.

    Returns paginated list of stocks with metadata.
    """
    try:
        query = db.query(Stock)
        total = query.count()
        stocks = query.offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "stocks": [
                _serialize_stock(stock)
                for stock in stocks
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily")
async def get_daily_quotes(
    stock_code: Optional[str] = Query(None, description="Stock code (e.g., 000001)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get daily quotes for stocks.

    Can filter by:
    - stock_code: Single stock or comma-separated list
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)

    Returns forward-adjusted daily data with OHLCV.
    """
    try:
        parsed_start = None
        parsed_end = None
        query = db.query(
            DailyQuote.date,
            DailyQuote.stock_code,
            DailyQuote.open_price,
            DailyQuote.high_price,
            DailyQuote.low_price,
            DailyQuote.close_price,
            DailyQuote.volume,
            DailyQuote.amount,
        )

        if stock_code:
            codes = [c.strip() for c in stock_code.split(",")]
            query = query.filter(DailyQuote.stock_code.in_(codes))

        if start_date:
            try:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid start_date format, expected YYYY-MM-DD")
            query = query.filter(DailyQuote.date >= parsed_start)

        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid end_date format, expected YYYY-MM-DD")
            query = query.filter(DailyQuote.date <= parsed_end)

        if parsed_start is not None and parsed_end is not None and parsed_start > parsed_end:
            raise HTTPException(status_code=422, detail="start_date must be earlier than or equal to end_date")

        total = query.count()
        quotes = query.order_by(DailyQuote.date.desc(), DailyQuote.stock_code.asc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": [
                {
                    "date": q[0].strftime("%Y-%m-%d"),
                    "stock_code": q[1],
                    "open": q[2],
                    "high": q[3],
                    "low": q[4],
                    "close": q[5],
                    "volume": q[6],
                    "amount": q[7]
                }
                for q in quotes
            ]
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trigger-update")
async def trigger_data_update(
    stock_codes: Optional[str] = Query(None, description="Comma-separated stock codes (optional)"),
    current_user: str = Depends(get_current_user)
):
    """
    Manually trigger data update task.

    This endpoint starts the Celery task to fetch latest stock data.
    """
    from src.tasks.scheduled_tasks import manual_fetch_task

    try:
        codes_list = None
        if stock_codes:
            codes_list = [c.strip() for c in stock_codes.split(",")]

        if settings.is_test:
            task_id = "test-task-id"
        else:
            task = getattr(manual_fetch_task, "delay")(codes_list)
            task_id = task.id

        return {
            "message": "Data update task triggered",
            "status": "queued",
            "task_id": task_id,
            "user": current_user,
            "stock_codes": codes_list if codes_list else "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger task: {str(e)}")


def _serialize_stock(stock: Stock):
    list_date = stock.list_date
    return {
        "stock_code": stock.stock_code,
        "stock_name": stock.stock_name,
        "exchange": stock.exchange,
        "is_st": stock.is_st,
        "list_date": list_date.strftime("%Y-%m-%d") if list_date is not None else None,
        "industry": stock.industry,
        "market_cap": stock.market_cap,
    }
