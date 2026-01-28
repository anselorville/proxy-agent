"""Stock data endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import pandas as pd

from src.api.auth import get_current_user
from src.models.database import get_db
from src.models.stock_data import DailyQuote
from sqlalchemy.orm import Session

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
    # TODO: Implement stock list query
    return {
        "total": 4500,
        "skip": skip,
        "limit": limit,
        "stocks": []
    }


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
    current_user: str = Depends(get_current_user)
):
    """
    Manually trigger data update task.
    
    This endpoint starts the Celery task to fetch latest stock data.
    """
    # TODO: Trigger Celery task
    return {
        "message": "Data update task triggered",
        "status": "queued",
        "user": current_user
    }
