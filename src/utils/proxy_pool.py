"""Proxy pool management for IP rotation."""

import random
import requests
import logging
from typing import List, Optional, Dict
import time

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Manages proxy pool with rotation and validation.
    
    Features:
    - Proxy rotation through pool
    - Automatic proxy validation
    - Failed proxy removal
    - User-Agent randomization
    """
    
    def __init__(self, proxy_list: Optional[List[str]] = None, pool_size: int = 5):
        """
        Initialize proxy manager.
        
        Args:
            proxy_list: Initial list of proxies
            pool_size: Target pool size
        """
        self.proxies: List[str] = proxy_list or []
        self.failed_proxies: List[str] = []
        self.current_index: int = 0
        self.pool_size = pool_size
        
        # User-Agent list for randomization
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        ]
        
        if self.proxies:
            logger.info(f"Proxy manager initialized with {len(self.proxies)} proxies")
        else:
            logger.warning("No proxies provided. Proxy rotation disabled.")
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get next proxy from pool with rotation.
        
        Returns:
            Dictionary with http/https keys or None if no proxies available
        """
        if not self.proxies:
            logger.warning("Proxy pool is empty")
            return None
        
        # Get current proxy
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        proxy_dict = {
            "http": proxy,
            "https": proxy
        }
        
        logger.debug(f"Using proxy: {proxy}")
        return proxy_dict
    
    def get_random_user_agent(self) -> str:
        """
        Get random User-Agent string.
        
        Returns:
            Random User-Agent string
        """
        return random.choice(self.user_agents)
    
    def validate_proxy(self, proxy: str, timeout: int = 10) -> bool:
        """
        Validate if proxy is alive and working.
        
        Args:
            proxy: Proxy URL (e.g., "http://1.2.3.4:8080")
            timeout: Connection timeout in seconds
        
        Returns:
            True if proxy is valid, False otherwise
        """
        try:
            test_url = "http://httpbin.org/ip"
            response = requests.get(
                test_url,
                proxies={"http": proxy, "https": proxy},
                timeout=timeout
            )
            is_valid = response.status_code == 200
            logger.debug(f"Proxy {proxy} validation: {'valid' if is_valid else 'invalid'}")
            return is_valid
            
        except Exception as e:
            logger.debug(f"Proxy {proxy} validation failed: {e}")
            return False
    
    def add_proxy(self, proxy: str):
        """
        Add proxy to pool.
        
        Args:
            proxy: Proxy URL to add
        """
        if proxy not in self.proxies and proxy not in self.failed_proxies:
            self.proxies.append(proxy)
            logger.info(f"Added proxy to pool: {proxy}")
    
    def remove_proxy(self, proxy: str):
        """
        Remove failed proxy from pool.
        
        Args:
            proxy: Proxy URL to remove
        """
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            self.failed_proxies.append(proxy)
            logger.warning(f"Removed failed proxy from pool: {proxy}")
    
    def get_request_headers(self) -> Dict[str, str]:
        """
        Get request headers with random User-Agent.
        
        Returns:
            Dictionary with common headers
        """
        return {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
    
    def rotate_proxies(self):
        """
        Rotate proxy pool to use different proxy order.
        """
        if self.proxies:
            random.shuffle(self.proxies)
            self.current_index = 0
            logger.info("Proxy pool rotated")


# Test proxy manager
if __name__ == "__main__":
    # Example usage
    proxy_list = [
        "http://116.196.115.168:8080",
        "http://43.135.158.111:8080",
    ]
    
    pm = ProxyManager(proxy_list)
    
    # Get proxy
    proxy = pm.get_proxy()
    print(f"Proxy: {proxy}")
    
    # Get headers
    headers = pm.get_request_headers()
    print(f"User-Agent: {headers['User-Agent']}")
