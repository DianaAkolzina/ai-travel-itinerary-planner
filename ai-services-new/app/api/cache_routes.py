from fastapi import APIRouter, HTTPException
from ..services.cache_service import CacheService

router = APIRouter(prefix="/cache", tags=["cache"])

cache_service = CacheService()

@router.get("/stats")
async def get_cache_stats():
    """Get cache statistics"""
    return cache_service.get_cache_stats()

@router.post("/cleanup")
async def cleanup_cache():
    """Clean up expired cache entries"""
    cache_service.cleanup_expired_cache()
    return {"message": "Cache cleanup completed"}

@router.delete("/clear")
async def clear_cache():
    """Clear all cache entries (use with caution)"""
    try:
        if hasattr(cache_service, 'collection') and cache_service.collection is not None:
            result = cache_service.collection.delete_many({})
            message = f"Cleared {result.deleted_count} MongoDB cache entries"
        else:
            cache_service._memory_cache.clear()
            message = "Cleared memory cache entries"
        
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
