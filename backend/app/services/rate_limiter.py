import time

from redis.asyncio import Redis


class RateLimiter:
    def __init__(self, valkey: Redis):
        self.valkey = valkey

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = int(time.time())
        bucket = f"ratelimit:{key}:{now // window_seconds}"
        pipe = self.valkey.pipeline()
        pipe.incr(bucket)
        pipe.expire(bucket, window_seconds + 1)
        results = await pipe.execute()
        count = results[0]
        return count <= limit

    async def enforce(self, key:str, limit: int, window_seconds: int = 60) -> None:
        allowed = await self.check(key, limit, window_seconds)
        if not allowed:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded",
            )
