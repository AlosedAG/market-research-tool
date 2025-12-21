# src/rate_limiter.py
import time
import asyncio
from functools import wraps

class RateLimiter:
    """Simple rate limiter to avoid hitting API quotas."""
    
    def __init__(self, calls_per_minute=10):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = 0
    
    async def wait(self):
        """Wait if necessary to respect rate limit."""
        now = time.time()
        time_since_last = now - self.last_call
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            print(f"   ⏳ Rate limiting: waiting {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)
        
        self.last_call = time.time()

# Global rate limiter - Flash model allows 15 RPM
# We'll use 10 RPM to be safe
gemini_limiter = RateLimiter(calls_per_minute=10)

def rate_limited(func):
    """Decorator to rate limit async functions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        await gemini_limiter.wait()
        return await func(*args, **kwargs)
    return wrapper

def rate_limited_sync(func):
    """Decorator to rate limit sync functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # For sync functions, use blocking sleep
        now = time.time()
        time_since_last = now - gemini_limiter.last_call
        
        if time_since_last < gemini_limiter.min_interval:
            wait_time = gemini_limiter.min_interval - time_since_last
            print(f"   ⏳ Rate limiting: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        gemini_limiter.last_call = time.time()
        return func(*args, **kwargs)
    return wrapper