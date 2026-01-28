"""Frequency control using token bucket algorithm."""

import time
import logging
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)


class FrequencyController:
    """
    Frequency controller using token bucket algorithm.
    
    Implements rate limiting to avoid IP blocking by
    controlling request frequency.
    
    Token bucket algorithm:
    - Tokens are added at a fixed rate
    - Each request consumes tokens
    - If insufficient tokens, wait until available
    """
    
    def __init__(self, requests_per_second: float = 0.5):
        """
        Initialize frequency controller.
        
        Args:
            requests_per_second: Maximum requests per second
                                (default: 0.5 = 1 request per 2 seconds)
        """
        self.rate = requests_per_second
        self.tokens: float = 1.0  # Start with 1 token
        self.last_update: float = time.time()
        self.lock = Lock()
        
        # Convert rate to tokens per microsecond for precision
        self.tokens_per_microsecond = self.rate / 1_000_000
        
        logger.info(f"Frequency controller initialized: {requests_per_second} requests/sec")
    
    def _update_tokens(self):
        """
        Update token count based on elapsed time.
        
        Called internally to add tokens based on time passed.
        """
        now = time.time()
        elapsed_microseconds = (now - self.last_update) * 1_000_000
        added_tokens = elapsed_microseconds * self.tokens_per_microsecond
        
        self.tokens = min(self.tokens + added_tokens, 1.0)  # Cap at 1.0
        self.last_update = now
    
    def can_request(self) -> bool:
        """
        Check if request is allowed (has enough tokens).
        
        Returns:
            True if request is allowed, False otherwise
        """
        with self.lock:
            self._update_tokens()
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False
    
    def wait_if_needed(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until request is allowed.
        
        Args:
            timeout: Maximum wait time in seconds
                    If None, wait indefinitely
        
        Returns:
            True if request is now allowed, False if timeout
        """
        start_time = time.time()
        
        while True:
            if self.can_request():
                logger.debug("Request allowed")
                return True
            
            # Calculate wait time
            with self.lock:
                self._update_tokens()
                if self.tokens < 1.0:
                    needed_tokens = 1.0 - self.tokens
                    wait_seconds = needed_tokens / self.rate
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"Frequency control timeout after {timeout} seconds")
                return False
            
            # Wait a bit
            wait_seconds = max(0.1, min(wait_seconds, 1.0))
            time.sleep(wait_seconds)
    
    def reset(self):
        """Reset token count (useful after long pauses)."""
        with self.lock:
            self.tokens = 1.0
            self.last_update = time.time()
            logger.debug("Frequency controller reset")


# Test frequency controller
if __name__ == "__main__":
    # Example usage
    fc = FrequencyController(requests_per_second=0.5)  # 1 request per 2 seconds
    
    # Test multiple requests
    for i in range(5):
        print(f"Request {i+1}: ", end="")
        fc.wait_if_needed()
        print("Allowed!")
        time.sleep(1)
