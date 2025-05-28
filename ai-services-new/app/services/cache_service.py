import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pprint import pprint

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.cache_expiry_hours = int(os.getenv("CACHE_EXPIRY_HOURS", "24"))
        self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

        self._memory_cache = {}

        self.client = None
        self.db = None
        self.collection = None

        if self.cache_enabled:
            self._connect()

    def _connect(self):
        try:
            from pymongo import MongoClient
            self.client = MongoClient(self.mongodb_uri)
            self.db = self.client.get_database("travel_planner")
            self.collection = self.db.get_collection("cached_itineraries")

            self.collection.create_index("request_hash", unique=True)
            self.collection.create_index("expires_at")

            logger.info("✅ Connected to MongoDB at travel_planner.cached_itineraries")
        except Exception as e:
            logger.warning(f"❌ MongoDB connection failed: {e}")
            self.client = None

    def _generate_hash(self, destination: str, travel_dates: list, preferences: dict, radius: int) -> str:
        import hashlib, json
        request_data = {
            "destination": destination,
            "travel_dates": sorted(travel_dates),
            "preferences": dict(sorted(preferences.items())),
            "radius": radius
        }
        request_str = json.dumps(request_data, sort_keys=True)
        return hashlib.sha256(request_str.encode()).hexdigest()

    def get_cached_response(self, destination: str, travel_dates: list,
                            preferences: dict, radius: int) -> Optional[Dict[str, Any]]:
        if not self.cache_enabled:
            return None

        try:
            request_hash = self._generate_hash(destination, travel_dates, preferences, radius)

            if self.collection is not None:
                cached = self.collection.find_one({
                    "request_hash": request_hash,
                    "$or": [{"expires_at": {"$gt": datetime.utcnow()}}, {"expires_at": None}]
                })
                if cached:
                    logger.info(f"📦 MongoDB cache hit for hash {request_hash}")
                    return cached["response_data"]

            if request_hash in self._memory_cache:
                entry = self._memory_cache[request_hash]
                if entry["expires_at"] is None or entry["expires_at"] > datetime.utcnow():
                    logger.info(f"📦 Memory cache hit for hash {request_hash}")
                    return entry["response_data"]
                else:
                    del self._memory_cache[request_hash]

        except Exception as e:
            logger.error(f"❌ Cache retrieval error: {e}")

        return None

    def cache_response(self, destination: str, travel_dates: list,
                       preferences: dict, radius: int, response_data: Dict[str, Any]) -> bool:
        if not self.cache_enabled:
            return False

        try:
            request_hash = self._generate_hash(destination, travel_dates, preferences, radius)
            expires_at =  None  # Keep entries forever

            entry = {
                "request_hash": request_hash,
                "destination": destination,
                "travel_dates": travel_dates,
                "preferences": preferences,
                "radius": radius,
                "response_data": response_data,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at
            }

            if self.collection is not None:
                self.collection.replace_one({"request_hash": request_hash}, entry, upsert=True)
                logger.info(f"✅ Cached response to MongoDB for hash: {request_hash}")
                print("📝 Saved MongoDB entry:")
                pprint(entry)
                return True

            self._memory_cache[request_hash] = entry
            logger.info(f"✅ Cached response to memory for hash: {request_hash}")
            print("📝 Saved in-memory entry:")
            pprint(entry)
            return True

        except Exception as e:
            logger.error(f"❌ Cache save error: {e}")
            return False

    def cleanup_expired_cache(self):
        if not self.cache_enabled:
            return
        try:
            if self.collection:
                result = self.collection.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
                logger.info(f"🧹 Removed {result.deleted_count} expired MongoDB entries")

            now = datetime.utcnow()
            expired = [k for k, v in self._memory_cache.items() if v["expires_at"] and v["expires_at"] < now]
            for k in expired:
                del self._memory_cache[k]

            if expired:
                logger.info(f"🧹 Removed {len(expired)} expired memory entries")

        except Exception as e:
            logger.error(f"❌ Cache cleanup error: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        if not self.cache_enabled:
            return {"cache_enabled": False}

        try:
            stats = {"cache_enabled": True, "memory_entries": len(self._memory_cache)}
            if self.collection:
                total = self.collection.count_documents({})
                expired = self.collection.count_documents({"expires_at": {"$lt": datetime.utcnow()}})
                stats.update({
                    "mongodb_total_entries": total,
                    "mongodb_active_entries": total - expired,
                    "mongodb_expired_entries": expired
                })
            return stats
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
            return {"cache_enabled": True, "error": str(e)}
