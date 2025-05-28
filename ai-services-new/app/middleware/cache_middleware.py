
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import random
from ..services.cache_service import CacheService

class CacheCleanupMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, cleanup_probability: float = 0.01):
        super().__init__(app)
        self.cleanup_probability = cleanup_probability
        self.cache_service = CacheService()
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Randomly trigger cache cleanup (1% chance by default)
        if random.random() < self.cleanup_probability:
            self.cache_service.cleanup_expired_cache()
        
        return response