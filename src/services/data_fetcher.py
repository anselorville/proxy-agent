"""Data fetcher service integrating akshare with proxy management."""

import time
import random
import logging
import akshare as ak

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Data fetcher service with proxy support.

    Integrates with akshare to fetch A-share stock data
    while avoiding IP blocking through proxy rotation.
    """

    def __init__(self, proxy_manager=None, frequency_controller=None):
        """Initialize data fetcher."""
        self.proxy_manager = proxy_manager
        self.frequency_controller = frequency_controller

    def fetch_daily_quotes(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
        max_retries: int = 3
    ):
        """
        Fetch daily quotes for a single stock.

        Args:
            stock_code: Stock code (e.g., "000001")
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            adjust: Adjustment type (qfq: 前复权, hfq: 后复权, None: 不复权)
            max_retries: Maximum retry attempts with exponential backoff

        Returns:
            DataFrame with OHLCV data or None if failed
        """
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                logger.info(f"Fetching data for {stock_code} from {start_date} to {end_date} "
                            f"(attempt {retry_count + 1}/{max_retries})")

                if self.frequency_controller:
                    if not self.frequency_controller.wait_if_needed():
                        logger.warning(f"Frequency control timeout for {stock_code}")
                        break

                proxy_dict = None
                if self.proxy_manager:
                    proxy_dict = self.proxy_manager.get_proxy()
                    if proxy_dict:
                        logger.debug(f"Using proxy: {proxy_dict.get('http')}")

                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )

                if df is not None and not df.empty:
                    logger.info(f"Successfully fetched {len(df)} records for {stock_code}")
                    return df
                else:
                    logger.warning(f"Empty data returned for {stock_code}")
                    return None

            except Exception as e:
                last_error = e
                logger.error(f"Failed to fetch data for {stock_code} (attempt {retry_count + 1}): {e}")

                if proxy_dict and self.proxy_manager and "timeout" in str(e).lower():
                    proxy_url = proxy_dict.get("http") or proxy_dict.get("https")
                    self.proxy_manager.remove_proxy(proxy_url)

                if retry_count < max_retries - 1:
                    wait_time = (2 ** retry_count) + random.uniform(0, 1)
                    logger.info(f"Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)

                retry_count += 1

        logger.error(f"Failed to fetch data for {stock_code} after {max_retries} attempts. Last error: {last_error}")
        return None

    def fetch_batch_quotes(self, stock_codes: list, start_date: str, end_date: str):
        """
        Fetch daily quotes for multiple stocks.

        Args:
            stock_codes: List of stock codes
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)

        Returns:
            Dictionary of stock_code -> DataFrame
        """
        results = {}

        for code in stock_codes:
            if self.frequency_controller:
                self.frequency_controller.wait_if_needed()

            data = self.fetch_daily_quotes(code, start_date, end_date)

            if data is not None:
                results[code] = data

        return results

    def get_stock_list(self, filter_st: bool = True, max_retries: int = 3):
        """
        Get list of all stocks.

        Args:
            filter_st: Exclude ST stocks if True
            max_retries: Maximum retry attempts

        Returns:
            DataFrame of stocks with metadata
        """
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                logger.info(f"Fetching stock list (attempt {retry_count + 1}/{max_retries})")

                if self.frequency_controller:
                    self.frequency_controller.wait_if_needed()

                proxy_dict = None
                if self.proxy_manager:
                    proxy_dict = self.proxy_manager.get_proxy()
                    if proxy_dict:
                        logger.debug(f"Using proxy: {proxy_dict.get('http')}")

                df = ak.stock_info_a_code_name()

                if df is not None and not df.empty:
                    if filter_st:
                        df = df[~df['name'].str.contains('ST', na=False)]

                    logger.info(f"Successfully fetched {len(df)} stocks")
                    return df
                else:
                    logger.warning("Empty data returned for stock list")
                    return None

            except Exception as e:
                last_error = e
                logger.error(f"Failed to fetch stock list (attempt {retry_count + 1}): {e}")

                if retry_count < max_retries - 1:
                    wait_time = (2 ** retry_count) + random.uniform(0, 1)
                    logger.info(f"Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)

                retry_count += 1

        logger.error(f"Failed to fetch stock list after {max_retries} attempts. Last error: {last_error}")
        return None
