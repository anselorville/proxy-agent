"""Stock data endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime

from src.api.auth import get_current_user
from src.models.database import get_db
from src.models.stock_data import DailyQuote, Stock

router = APIRouter()


@router.get("/list")
async def get_stock_list(
    skip: int = 0,
    limit: int = 100,
    current_user: str = Depends(get_current_user)
):
    """
    Get list of all stocks.

    Returns paginated list of stocks with metadata.
    """
    db = next(get_db())

    try:
        query = db.query(Stock)
        total = query.count()
        stocks = query.offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "stocks": [
                {
                    "stock_code": stock.stock_code,
                    "stock_name": stock.stock_name,
                    "exchange": stock.exchange,
                    "is_st": stock.is_st,
                    "list_date": stock.list_date.strftime("%Y-%m-%d") if stock.list_date else None,
                    "industry": stock.industry,
                    "market_cap": stock.market_cap
                }
                for stock in stocks
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/daily")
async def get_daily_quotes(
    stock_code: Optional[str] = Query(None, description="Stock code (e.g., 000001)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Records per page"),
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
    db = next(get_db())

    try:
        query = db.query(DailyQuote)

        if stock_code:
            codes = [c.strip() for c in stock_code.split(",")]
            query = query.filter(DailyQuote.stock_code.in_(codes))

        if start_date:
            query = query.filter(DailyQuote.date >= datetime.strptime(start_date, "%Y-%m-%d"))

        if end_date:
            query = query.filter(DailyQuote.date <= datetime.strptime(end_date, "%Y-%m-%d"))

        total = query.count()
        quotes = query.order_by(DailyQuote.date.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": [
                {
                    "date": q.date.strftime("%Y-%m-%d"),
                    "stock_code": q.stock_code,
                    "open": q.open_price,
                    "high": q.high_price,
                    "low": q.low_price,
                    "close": q.close_price,
                    "volume": q.volume,
                    "amount": q.amount
                }
                for q in quotes
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


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

        task = manual_fetch_task.delay(codes_list)

        return {
            "message": "Data update task triggered",
            "status": "queued",
            "task_id": task.id,
            "user": current_user,
            "stock_codes": codes_list if codes_list else "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger task: {str(e)}")
