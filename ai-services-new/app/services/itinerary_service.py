import re
import logging
from typing import Dict, Any, List
from datetime import date
from app.models.requests import ItineraryRequest
from app.services.location_service import LocationService
from app.services.weather_service import WeatherService
from app.services.llm_service import LLMService
from app.services.route_optimizer import RouteOptimizer
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

class ItineraryService:
    """Main service for generating travel itineraries with intelligent caching"""
    
    def __init__(self):
        self.location_service = LocationService()
        self.weather_service = WeatherService()
        self.llm_service = LLMService()
        self.route_optimizer = RouteOptimizer()
        self.cache_service = CacheService()  # NEW: Initialize cache service
    
    async def generate_itinerary(self, request: ItineraryRequest) -> Dict[str, Any]:
        """Generate a complete travel itinerary for specific dates with caching"""
        
        # Validation
        if not request.destination:
            raise ValueError("Destination must be provided.")
        
        if not request.travel_dates or len(request.travel_dates) == 0:
            raise ValueError("At least one travel date must be provided.")
        
        sorted_dates = sorted(request.travel_dates)
        num_days = len(sorted_dates)
        
        # Convert dates to strings for consistent caching
        date_strings = [str(d) for d in sorted_dates]
        
        # NEW: Check cache first
        cached_response = self.cache_service.get_cached_response(
            destination=request.destination,
            travel_dates=date_strings,
            preferences=request.preferences.dict() if hasattr(request.preferences, 'dict') else request.preferences,
            radius=request.radius
        )
        
        if cached_response:
            logger.info(f"🎯 Cache hit for destination: {request.destination}, dates: {date_strings}")
            # Add cache metadata
            cached_response["cache_info"] = {
                "from_cache": True,
                "generated_at": cached_response.get("generated_at"),
                "cache_enabled": self.cache_service.cache_enabled
            }
            return cached_response
        
        # NEW: Log cache miss
        logger.info(f"🔄 Cache miss - generating new itinerary for: {request.destination}")
        print(f"🗓️ Planning itinerary for {num_days} days: {sorted_dates}")
        
        # Parse coordinates
        lat, lng = self._parse_coordinates(request.destination)
        if lat is None or lng is None:
            print("❌ Invalid coordinates format")
            return {"plan": []}
        
        print(f"🌍 Coordinates: {lat}, {lng}")
        
        # Get location context
        nearby_cities = await self.location_service.get_nearby_cities(lat, lng, request.radius)
        location_details = await self.location_service.get_location_details(lat, lng)
        
        if location_details:
            print(f"📍 Location details: {location_details}")
            nearby_cities.extend([
                location_details.get('city', ''), 
                location_details.get('region', '')
            ])
            nearby_cities = [city for city in nearby_cities if city]
        
        print("🏙️ Enhanced location context:", nearby_cities)
        
        # Generate plan with LLM
        try:
            raw_plan = await self.llm_service.generate_plan(request, nearby_cities)
            if not raw_plan:
                print("⚠️ LLM failed to generate plan, using fallback")
                raw_plan = await self.llm_service.generate_fallback_plan(request, lat, lng, nearby_cities)
        except Exception as e:
            print(f"❌ LLM service error: {e}")
            raw_plan = await self.llm_service.generate_fallback_plan(request, lat, lng, nearby_cities)
        
        # Enrich and validate the plan
        enriched_plan = await self.location_service.enrich_and_validate_plan(
            (lat, lng), raw_plan, request.radius
        )
        
        # Optimize route if multiple days
        if len(enriched_plan) > 1:
            enriched_plan = self.route_optimizer.optimize_route((lat, lng), enriched_plan)
        
        # Assign dates to each day
        for i, day_plan in enumerate(enriched_plan):
            if i < len(sorted_dates):
                day_plan['date'] = str(sorted_dates[i])
                day_plan['formatted_date'] = sorted_dates[i].strftime('%B %d, %Y')
        
        print("✅ Final Enriched Plan:", enriched_plan)
        
        # Get weather forecast
        weather_data = await self.weather_service.get_forecast_for_dates(lat, lng, sorted_dates)
        
        # Build complete response
        response = {
            "plan": enriched_plan,
            "nearby_cities": nearby_cities,
            "user_coordinates": {"lat": lat, "lng": lng},
            "search_radius": request.radius,
            "travel_dates": date_strings,
            "total_days": num_days,
            "generated_at": self._get_current_timestamp(),  # NEW: Add timestamp
            "cache_info": {  # NEW: Add cache metadata
                "from_cache": False,
                "cache_enabled": self.cache_service.cache_enabled
            }
        }
        
        # Add weather data if available
        if weather_data:
            response["weather"] = weather_data
            print(f"✅ Weather forecast included for {len(weather_data['forecast'])} days")
        else:
            print("ℹ️ No weather forecast included - not available for requested dates")
            response["weather"] = {
                "forecast": [],
                "location": location_details.get('city', 'Unknown') if location_details else 'Unknown',
                "missing_dates": date_strings
            }
        
        # NEW: Cache the complete response
        cache_success = self.cache_service.cache_response(
            destination=request.destination,
            travel_dates=date_strings,
            preferences=request.preferences.dict() if hasattr(request.preferences, 'dict') else request.preferences,
            radius=request.radius,
            response_data=response
        )
        
        if cache_success:
            logger.info(f"✅ Successfully cached itinerary for {request.destination}")
        else:
            logger.warning(f"⚠️ Failed to cache itinerary for {request.destination}")
        
        return response
    
    def _parse_coordinates(self, destination: str) -> tuple[float | None, float | None]:
        """Parse coordinates from destination string"""
        match = re.search(r"Lat:\s*([0-9\.-]+),\s*Lng:\s*([0-9\.-]+)", destination)
        if not match:
            return None, None
        
        try:
            lat, lng = map(float, match.groups())
            return lat, lng
        except ValueError:
            return None, None
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    # NEW: Cache management methods
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache_service.get_cache_stats()
    
    async def clear_expired_cache(self) -> None:
        """Clear expired cache entries"""
        self.cache_service.cleanup_expired_cache()
        logger.info("🧹 Cleared expired cache entries")
    
    async def clear_all_cache(self) -> Dict[str, Any]:
        """Clear all cache entries (admin function)"""
        if not self.cache_service.cache_enabled:
            return {"message": "Cache not enabled"}
        
        try:
            result = self.cache_service.collection.delete_many({})
            logger.info(f"🗑️ Cleared {result.deleted_count} cache entries")
            return {"message": f"Cleared {result.deleted_count} cache entries"}
        except Exception as e:
            logger.error(f"❌ Failed to clear cache: {e}")
            return {"error": str(e)}
    
    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled"""
        return self.cache_service.cache_enabled
    
    # NEW: Method to invalidate specific cache entries
    async def invalidate_cache_for_location(self, destination: str) -> Dict[str, Any]:
        """Invalidate all cache entries for a specific destination"""
        if not self.cache_service.cache_enabled:
            return {"message": "Cache not enabled"}
        
        try:
            # Find entries matching the destination
            result = self.cache_service.collection.delete_many({
                "destination": destination
            })
            
            logger.info(f"🎯 Invalidated {result.deleted_count} cache entries for destination: {destination}")
            return {
                "message": f"Invalidated {result.deleted_count} cache entries",
                "destination": destination
            }
        except Exception as e:
            logger.error(f"❌ Failed to invalidate cache for {destination}: {e}")
            return {"error": str(e)}
    
    # NEW: Advanced cache warming method
    async def warm_cache_for_popular_destinations(self, destinations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Pre-populate cache for popular destinations"""
        if not self.cache_service.cache_enabled:
            return {"message": "Cache not enabled"}
        
        warmed_count = 0
        failed_count = 0
        
        for dest_config in destinations:
            try:
                # Create a mock request for cache warming
                mock_request = ItineraryRequest(
                    destination=dest_config["destination"],
                    travel_dates=dest_config.get("travel_dates", [date.today()]),
                    preferences=dest_config.get("preferences", {"interests": ["General"]}),
                    radius=dest_config.get("radius", 50)
                )
                
                # Generate and cache the itinerary
                await self.generate_itinerary(mock_request)
                warmed_count += 1
                logger.info(f"🔥 Warmed cache for: {dest_config['destination']}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Cache warming failed for {dest_config.get('destination', 'unknown')}: {e}")
        
        return {
            "warmed_destinations": warmed_count,
            "failed_destinations": failed_count,
            "total_attempted": len(destinations)
        }


# NEW: Helper class for request comparison (advanced caching)
class RequestSignature:
    """Helper class to create consistent signatures for caching"""
    
    @staticmethod
    def create_signature(request: ItineraryRequest) -> str:
        """Create a consistent signature for a request"""
        import hashlib
        import json
        
        # Normalize the request data
        signature_data = {
            "destination": request.destination,
            "travel_dates": sorted([str(d) for d in request.travel_dates]),
            "preferences": RequestSignature._normalize_preferences(request.preferences),
            "radius": request.radius
        }
        
        # Create hash
        signature_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.sha256(signature_str.encode()).hexdigest()
    
    @staticmethod
    def _normalize_preferences(preferences: Any) -> Dict[str, Any]:
        """Normalize preferences for consistent hashing"""
        if hasattr(preferences, 'dict'):
            pref_dict = preferences.dict()
        elif isinstance(preferences, dict):
            pref_dict = preferences
        else:
            pref_dict = {}
        
        # Sort interests and other lists for consistency
        if 'interests' in pref_dict and isinstance(pref_dict['interests'], list):
            pref_dict['interests'] = sorted(pref_dict['interests'])
        
        return dict(sorted(pref_dict.items()))


# NEW: Example usage and testing
if __name__ == "__main__":
    async def test_caching():
        """Test the caching functionality"""
        from app.models.requests import ItineraryRequest
        from datetime import date, timedelta
        
        service = ItineraryService()
        
        # Create test request
        test_request = ItineraryRequest(
            destination="Lat: 52.5200, Lng: 13.4050",  # Berlin
            travel_dates=[date.today(), date.today() + timedelta(days=1)],
            preferences={"interests": ["Food", "History"]},
            radius=50
        )
        
        print("🧪 Testing cache functionality...")
        
        # First request - should generate new
        print("1️⃣ First request (should generate new)...")
        import time
        start_time = time.time()
        result1 = await service.generate_itinerary(test_request)
        duration1 = time.time() - start_time
        print(f"⏱️ First request took: {duration1:.2f} seconds")
        print(f"📊 From cache: {result1.get('cache_info', {}).get('from_cache', False)}")
        
        # Second request - should use cache
        print("\n2️⃣ Second request (should use cache)...")
        start_time = time.time()
        result2 = await service.generate_itinerary(test_request)
        duration2 = time.time() - start_time
        print(f"⏱️ Second request took: {duration2:.2f} seconds")
        print(f"📊 From cache: {result2.get('cache_info', {}).get('from_cache', False)}")
        
        # Performance comparison
        if duration1 > 0 and duration2 > 0:
            improvement = duration1 / duration2
            print(f"\n📈 Performance improvement: {improvement:.1f}x faster")
        
        # Cache stats
        stats = await service.get_cache_stats()
        print(f"\n📊 Cache stats: {stats}")
    
    # Run test
    import asyncio
    asyncio.run(test_caching())