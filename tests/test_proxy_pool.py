"""Tests for proxy pool functionality."""

import pytest
from src.utils.proxy_pool import ProxyManager


class TestProxyManager:
    """Test cases for ProxyManager class."""
    
    def test_initialization_with_proxies(self):
        """Test proxy manager initialization with proxy list."""
        proxy_list = [
            "http://1.2.3.4:8080",
            "http://5.6.7.8:8080"
        ]
        pm = ProxyManager(proxy_list=proxy_list)
        
        assert len(pm.proxies) == 2
        assert pm.current_index == 0
    
    def test_initialization_without_proxies(self):
        """Test proxy manager initialization without proxies."""
        pm = ProxyManager(proxy_list=None)
        
        assert len(pm.proxies) == 0
        assert pm.get_proxy() is None
    
    def test_get_proxy_rotation(self):
        """Test proxy rotation through pool."""
        proxy_list = [
            "http://proxy1:8080",
            "http://proxy2:8080",
            "http://proxy3:8080"
        ]
        pm = ProxyManager(proxy_list=proxy_list)
        
        # Get proxies in order
        proxies = []
        for _ in range(3):
            proxy = pm.get_proxy()
            proxies.append(proxy['http'])
        
        assert proxies == proxy_list
        
        # Verify rotation
        proxy4 = pm.get_proxy()
        assert proxy4['http'] == proxy_list[0]  # Back to start
    
    def test_add_proxy(self):
        """Test adding proxy to pool."""
        pm = ProxyManager(proxy_list=[])
        
        pm.add_proxy("http://newproxy:8080")
        
        assert len(pm.proxies) == 1
        assert "http://newproxy:8080" in pm.proxies
    
    def test_remove_proxy(self):
        """Test removing proxy from pool."""
        proxy_list = ["http://proxy1:8080", "http://proxy2:8080"]
        pm = ProxyManager(proxy_list=proxy_list)
        
        pm.remove_proxy("http://proxy1:8080")
        
        assert len(pm.proxies) == 1
        assert "http://proxy1:8080" not in pm.proxies
        assert "http://proxy1:8080" in pm.failed_proxies
    
    def test_get_random_user_agent(self):
        """Test User-Agent randomization."""
        pm = ProxyManager(proxy_list=[])
        
        ua = pm.get_random_user_agent()
        
        assert isinstance(ua, str)
        assert len(ua) > 50
        assert "Mozilla" in ua
    
    def test_get_request_headers(self):
        """Test request headers generation."""
        pm = ProxyManager(proxy_list=[])
        
        headers = pm.get_request_headers()
        
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Connection" in headers
        assert headers["User-Agent"] != ""
    
    def test_rotate_proxies(self):
        """Test proxy pool rotation."""
        proxy_list = [
            "http://proxy1:8080",
            "http://proxy2:8080",
            "http://proxy3:8080"
        ]
        pm = ProxyManager(proxy_list=proxy_list)
        
        # Rotate
        pm.rotate_proxies()
        
        # Order should be different
        rotated_proxies = []
        for _ in range(3):
            proxy = pm.get_proxy()
            rotated_proxies.append(proxy['http'])
        
        # Should contain same proxies but possibly different order
        assert set(rotated_proxies) == set(proxy_list)
