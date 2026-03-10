import asyncio
import time


class TokenBucketRateLimiter:
    """Async token bucket rate limiter for API call throttling."""

    def __init__(self, rate: int, period: float = 60.0):
        self.rate = rate
        self.period = period
        self.tokens = float(rate)
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(
                float(self.rate),
                self.tokens + elapsed * (self.rate / self.period),
            )
            self.last_refill = now

            if self.tokens < 1.0:
                wait = (1.0 - self.tokens) * (self.period / self.rate)
                await asyncio.sleep(wait)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0
