from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib
import json

class CachedRequest(BaseModel):
    id: Optional[str] = None
    request_hash: str
    destination: str
    travel_dates: list
    preferences: Dict[str, Any]
    radius: int
    response_data: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    @classmethod
    def generate_hash(cls, destination: str, travel_dates: list, preferences: dict, radius: int) -> str:
        """Generate a unique hash for the request parameters"""
        request_data = {
            "destination": destination,
            "travel_dates": sorted(travel_dates),
            "preferences": dict(sorted(preferences.items())),
            "radius": radius
        }
        request_str = json.dumps(request_data, sort_keys=True)
        return hashlib.sha256(request_str.encode()).hexdigest()
