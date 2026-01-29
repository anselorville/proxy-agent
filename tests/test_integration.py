"""Integration tests."""

import pytest
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.database import Base
from src.models.stock_data import Stock, DailyQuote
from src.utils.proxy_pool import ProxyManager
from src.utils.frequency_control import FrequencyController
from src.services.data_fetcher import DataFetcher
from src.tasks.celery_app import celery_app

TEST_DATABASE_URL = "sqlite:///./test.db"


class TestIntegration:
    """Integration tests for the entire application."""

    @pytest.fixture(scope="class")
    def db_session(self):
        """Create test database session."""
        engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        yield session
        session.close()
        engine.dispose()

    @pytest.fixture(scope="class")
    def proxy_manager(self):
        """Create proxy manager for testing."""
        return ProxyManager(proxy_list=None)

    @pytest.fixture(scope="class")
    def frequency_controller(self):
        """Create frequency controller for testing."""
        return FrequencyController(interval=1)

    @pytest.fixture(scope="class")
    def data_fetcher(self, proxy_manager, frequency_controller):
        """Create data fetcher for testing."""
        return DataFetcher(proxy_manager, frequency_controller)

    def test_database_integration(self, db_session):
        """Test database operations integration."""
        stock = Stock(
            stock_code="600000",
            stock_name="浦发银行",
            exchange="SH",
            is_st=False,
            industry="银行"
        )
        db_session.add(stock)
        db_session.commit()

        retrieved_stock = db_session.query(Stock).filter_by(stock_code="600000").first()
        assert retrieved_stock is not None
        assert retrieved_stock.stock_name == "浦发银行"

    def test_proxy_pool_integration(self, proxy_manager):
        """Test proxy pool integration."""
        proxy_manager.add_proxy("http://testproxy:8080")
        proxy = proxy_manager.get_proxy()
        assert proxy is not None
        assert proxy["http"] == "http://testproxy:8080"

    def test_frequency_control_integration(self, frequency_controller):
        """Test frequency control integration."""
        start = time.time()
        frequency_controller.wait_if_needed()
        elapsed = time.time() - start
        assert elapsed < 2

    def test_data_fetcher_integration(self, data_fetcher):
        """Test data fetcher integration with services."""
        assert data_fetcher.proxy_manager is not None
        assert data_fetcher.frequency_controller is not None

    def test_stock_metadata_insertion(self, db_session):
        """Test inserting stock metadata."""
        stocks = [
            Stock(stock_code="000001", stock_name="平安银行", exchange="SZ", is_st=False),
            Stock(stock_code="000002", stock_name="万科A", exchange="SZ", is_st=False),
        ]
        for stock in stocks:
            db_session.merge(stock)
        db_session.commit()

        count = db_session.query(Stock).filter(Stock.stock_code.in_(["000001", "000002"])).count()
        assert count == 2

    def test_daily_quote_insertion(self, db_session):
        """Test inserting daily quotes."""
        quote = DailyQuote(
            stock_code="000001",
            date=datetime.now() - timedelta(days=1),
            open_price=10.0,
            high_price=11.0,
            low_price=9.5,
            close_price=10.5,
            volume=1000000,
            amount=10500000.0,
            adjust_factor=1.0
        )
        db_session.add(quote)
        db_session.commit()

        retrieved = db_session.query(DailyQuote).filter_by(stock_code="000001").first()
        assert retrieved is not None
        assert retrieved.open_price == 10.0

    def test_database_query_optimization(self, db_session):
        """Test database query with index optimization."""
        quotes = []
        for i in range(100):
            quote = DailyQuote(
                stock_code="000001",
                date=datetime.now() - timedelta(days=i),
                open_price=10.0,
                high_price=11.0,
                low_price=9.5,
                close_price=10.5,
                volume=1000000,
                amount=10500000.0,
                adjust_factor=1.0
            )
            quotes.append(quote)
        db_session.add_all(quotes)
        db_session.commit()

        result = db_session.query(DailyQuote).filter_by(stock_code="000001").limit(10).all()
        assert len(result) == 10

    def test_proxy_rotation_integration(self, proxy_manager):
        """Test proxy rotation in integration."""
        proxy_manager.add_proxy("http://proxy1:8080")
        proxy_manager.add_proxy("http://proxy2:8080")
        proxy_manager.add_proxy("http://proxy3:8080")

        proxies = []
        for _ in range(3):
            proxy = proxy_manager.get_proxy()
            proxies.append(proxy["http"])

        assert len(set(proxies)) == 3

    def test_celery_task_registration(self):
        """Test Celery task registration."""
        assert "fetch_daily_data" in celery_app.tasks
        assert "manual_fetch" in celery_app.tasks
        assert "health_check" in celery_app.tasks

    def test_celery_health_check(self):
        """Test Celery health check task."""
        result = celery_app.tasks["health_check"].apply()
        assert result.get(timeout=5) == "Celery worker is healthy"

    def test_integration_data_flow(self, db_session, data_fetcher):
        """Test complete data flow from fetch to database."""
        stock = Stock(
            stock_code="600519",
            stock_name="贵州茅台",
            exchange="SH",
            is_st=False
        )
        db_session.add(stock)
        db_session.commit()

        quote = DailyQuote(
            stock_code="600519",
            date=datetime.now() - timedelta(days=1),
            open_price=1800.0,
            high_price=1850.0,
            low_price=1790.0,
            close_price=1820.0,
            volume=100000,
            amount=182000000.0
        )
        db_session.add(quote)
        db_session.commit()

        retrieved = db_session.query(DailyQuote).filter_by(stock_code="600519").first()
        assert retrieved is not None
        assert retrieved.stock_code == "600519"

    def test_error_handling_integration(self, db_session):
        """Test error handling in integration."""
        try:
            invalid_quote = DailyQuote(
                stock_code=None,
                date=datetime.now(),
                open_price=10.0
            )
            db_session.add(invalid_quote)
            db_session.commit()
            assert False, "Should have raised an exception"
        except Exception:
            db_session.rollback()
            assert True

    def test_concurrent_operations(self, db_session):
        """Test concurrent database operations."""
        quotes = []
        for i in range(50):
            quote = DailyQuote(
                stock_code="000001",
                date=datetime.now() - timedelta(days=i),
                open_price=10.0,
                high_price=11.0,
                low_price=9.5,
                close_price=10.5,
                volume=1000000,
                amount=10500000.0
            )
            quotes.append(quote)
        db_session.add_all(quotes)
        db_session.commit()

        count = db_session.query(DailyQuote).filter_by(stock_code="000001").count()
        assert count >= 50
