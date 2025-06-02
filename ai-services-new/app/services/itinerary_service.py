import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import date, datetime
from app.models.requests import ItineraryRequest
from app.services.location_service import LocationService
from app.services.weather_service import WeatherService
from app.services.llm_service import LLMService
from app.services.route_optimizer import RouteOptimizer
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

class ItineraryService:
    def __init__(self):
        self.location_service = LocationService()
        self.weather_service = WeatherService()
        self.llm_service = LLMService()
        self.route_optimizer = RouteOptimizer()
        self.cache_service = CacheService()
    
    async def generate_itinerary(self, request: ItineraryRequest) -> Dict[str, Any]:
        # Validate request
        self._validate_request(request)
        
        sorted_dates = sorted(request.travel_dates)
        date_strings = [str(d) for d in sorted_dates]
        
        # Check cache first
        cached_response = self._check_cache(request, date_strings)
        if cached_response:
            logger.info(f"Cache hit for destination: {request.destination}")
            return cached_response
        
        logger.info(f"Cache miss - generating new itinerary for: {request.destination}")
        
        # Parse coordinates and get location context
        lat, lng = self._parse_coordinates(request.destination)
        if lat is None or lng is None:
            logger.error("Invalid coordinates format")
            return {"plan": []}
        
        nearby_cities, location_details = await self._get_location_context(lat, lng, request.radius)
        
        # Generate plan with fallback
        raw_plan = await self._generate_plan_with_fallback(request, nearby_cities, lat, lng)
        
        # Enrich and optimize plan
        enriched_plan = await self._enrich_and_optimize_plan(lat, lng, raw_plan, request.radius, sorted_dates)
        
        # Get weather data
        weather_data = await self._get_weather_data(lat, lng, sorted_dates, location_details)
        
        # Build and cache response
        response = self._build_response(
            enriched_plan, nearby_cities, lat, lng, request.radius, 
            date_strings, len(sorted_dates), weather_data
        )
        
        self._cache_response(request, date_strings, response)
        return response
    
    def _validate_request(self, request: ItineraryRequest) -> None:
        """Validate the incoming request"""
        if not request.destination:
            raise ValueError("Destination must be provided.")
        if not request.travel_dates or len(request.travel_dates) == 0:
            raise ValueError("At least one travel date must be provided.")
    
    def _check_cache(self, request: ItineraryRequest, date_strings: List[str]) -> Optional[Dict[str, Any]]:
        """Check for cached response"""
        preferences = self._extract_preferences(request.preferences)
        cached_response = self.cache_service.get_cached_response(
            destination=request.destination,
            travel_dates=date_strings,
            preferences=preferences,
            radius=request.radius
        )
        
        if cached_response:
            cached_response["cache_info"] = {
                "from_cache": True,
                "generated_at": cached_response.get("generated_at"),
                "cache_enabled": self.cache_service.cache_enabled
            }
            
        return cached_response
    
    def _extract_preferences(self, preferences: Any) -> Dict[str, Any]:
        """Extract preferences in a consistent format"""
        if hasattr(preferences, 'dict'):
            return preferences.dict()
        elif isinstance(preferences, dict):
            return preferences
        return {}
    
    async def _get_location_context(self, lat: float, lng: float, radius: int) -> Tuple[List[str], Optional[Dict]]:
        """Get nearby cities and location details"""
        nearby_cities = await self.location_service.get_nearby_cities(lat, lng, radius)
        location_details = await self.location_service.get_location_details(lat, lng)
        
        if location_details:
            logger.info(f"Location details: {location_details}")
            # Add location details to nearby cities
            additional_cities = [
                location_details.get('city', ''), 
                location_details.get('region', '')
            ]
            nearby_cities.extend([city for city in additional_cities if city])
        
        return nearby_cities, location_details
    
    async def _generate_plan_with_fallback(self, request: ItineraryRequest, nearby_cities: List[str], 
                                         lat: float, lng: float) -> List[Dict[str, Any]]:
        """Generate plan with automatic fallback on failure"""
        try:
            raw_plan = await self.llm_service.generate_plan(request, nearby_cities)
            if raw_plan:
                return raw_plan
            logger.warning("LLM failed to generate plan, using fallback")
        except Exception as e:
            logger.error(f"LLM service error: {e}")
        
        # Use fallback plan - the LLMService already has fallback logic built in
        return await self.llm_service.generate_plan(request, nearby_cities)
    
    async def _enrich_and_optimize_plan(self, lat: float, lng: float, raw_plan: List[Dict], 
                                      radius: int, sorted_dates: List[date]) -> List[Dict[str, Any]]:
        """Enrich plan with location data and optimize route"""
        # Enrich with location validation
        enriched_plan = await self.location_service.enrich_and_validate_plan(
            (lat, lng), raw_plan, radius
        )
        
        # Optimize route if multiple days
        if len(enriched_plan) > 1:
            enriched_plan = self.route_optimizer.optimize_route((lat, lng), enriched_plan)
        
        # Update dates
        for i, day_plan in enumerate(enriched_plan):
            if i < len(sorted_dates):
                day_plan['date'] = str(sorted_dates[i])
                day_plan['formatted_date'] = sorted_dates[i].strftime('%B %d, %Y')
        
        logger.info(f"Generated enriched plan with {len(enriched_plan)} days")
        return enriched_plan
    
    async def _get_weather_data(self, lat: float, lng: float, sorted_dates: List[date], 
                              location_details: Optional[Dict]) -> Dict[str, Any]:
        """Get weather forecast data"""
        weather_data = await self.weather_service.get_forecast_for_dates(lat, lng, sorted_dates)
        
        if weather_data:
            logger.info(f"Weather forecast included for {len(weather_data['forecast'])} days")
            return weather_data
        
        logger.info("No weather forecast available for requested dates")
        return {
            "forecast": [],
            "location": location_details.get('city', 'Unknown') if location_details else 'Unknown',
            "missing_dates": [str(d) for d in sorted_dates]
        }
    
    def _build_response(self, enriched_plan: List[Dict], nearby_cities: List[str], 
                       lat: float, lng: float, radius: int, date_strings: List[str], 
                       num_days: int, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build the final response object"""
        return {
            "plan": enriched_plan,
            "nearby_cities": nearby_cities,
            "user_coordinates": {"lat": lat, "lng": lng},
            "search_radius": radius,
            "travel_dates": date_strings,
            "total_days": num_days,
            "generated_at": self._get_current_timestamp(),
            "weather": weather_data,
            "cache_info": {
                "from_cache": False,
                "cache_enabled": self.cache_service.cache_enabled
            }
        }
    
    def _cache_response(self, request: ItineraryRequest, date_strings: List[str], response: Dict[str, Any]) -> None:
        """Cache the response"""
        preferences = self._extract_preferences(request.preferences)
        cache_success = self.cache_service.cache_response(
            destination=request.destination,
            travel_dates=date_strings,
            preferences=preferences,
            radius=request.radius,
            response_data=response
        )
        
        if cache_success:
            logger.info(f"Successfully cached itinerary for {request.destination}")
        else:
            logger.warning(f"Failed to cache itinerary for {request.destination}")
    
    def _parse_coordinates(self, destination: str) -> Tuple[Optional[float], Optional[float]]:
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
        return datetime.utcnow().isoformat()
    
    # Cache management methods - consolidated error handling
    def _execute_cache_operation(self, operation_name: str, operation_func) -> Dict[str, Any]:
        """Execute cache operation with consistent error handling"""
        if not self.cache_service.cache_enabled:
            return {"message": "Cache not enabled"}
        
        try:
            result = operation_func()
            logger.info(f"Cache operation '{operation_name}' completed successfully")
            return result
        except Exception as e:
            logger.error(f"Cache operation '{operation_name}' failed: {e}")
            return {"error": str(e)}
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache_service.get_cache_stats()
    
    async def clear_expired_cache(self) -> None:
        """Clear expired cache entries"""
        self.cache_service.cleanup_expired_cache()
        logger.info("Cleared expired cache entries")
    
    async def clear_all_cache(self) -> Dict[str, Any]:
        """Clear all cache entries (admin function)"""
        def clear_operation():
            result = self.cache_service.collection.delete_many({})
            return {"message": f"Cleared {result.deleted_count} cache entries"}
        
        return self._execute_cache_operation("clear_all_cache", clear_operation)
    
    async def invalidate_cache_for_location(self, destination: str) -> Dict[str, Any]:
        """Invalidate all cache entries for a specific destination"""
        def invalidate_operation():
            result = self.cache_service.collection.delete_many({"destination": destination})
            return {
                "message": f"Invalidated {result.deleted_count} cache entries",
                "destination": destination
            }
        
        return self._execute_cache_operation("invalidate_cache_for_location", invalidate_operation)
    
    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled"""
        return self.cache_service.cache_enabled
    
    async def warm_cache_for_popular_destinations(self, destinations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Pre-populate cache for popular destinations"""
        if not self.cache_service.cache_enabled:
            return {"message": "Cache not enabled"}
        
        warmed_count = 0
        failed_count = 0
        
        for dest_config in destinations:
            try:
                mock_request = ItineraryRequest(
                    destination=dest_config["destination"],
                    travel_dates=dest_config.get("travel_dates", [date.today()]),
                    preferences=dest_config.get("preferences", {"interests": ["General"]}),
                    radius=dest_config.get("radius", 50)
                )
                
                await self.generate_itinerary(mock_request)
                warmed_count += 1
                logger.info(f"Warmed cache for: {dest_config['destination']}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Cache warming failed for {dest_config.get('destination', 'unknown')}: {e}")
        
        return {
            "warmed_destinations": warmed_count,
            "failed_destinations": failed_count,
            "total_attempted": len(destinations)
        }


class RequestSignature:
    """Helper class to create consistent signatures for caching"""
    
    @staticmethod
    def create_signature(request: ItineraryRequest) -> str:
        """Create a consistent signature for a request"""
        import hashlib
        import json
        
        signature_data = {
            "destination": request.destination,
            "travel_dates": sorted([str(d) for d in request.travel_dates]),
            "preferences": RequestSignature._normalize_preferences(request.preferences),
            "radius": request.radius
        }
        
        signature_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.sha256(signature_str.encode()).hexdigest()
    
    @staticmethod
    def _normalize_preferences(preferences: Any) -> Dict[str, Any]:
        """Normalize preferences for consistent hashing"""
        if hasattr(preferences, 'dict'):
            pref_dict = preferences.dict()
        elif isinstance(preferences, dict):
            pref_dict = preferences.copy()
        else:
            pref_dict = {}
        
        # Sort interests if present
        if 'interests' in pref_dict and isinstance(pref_dict['interests'], list):
            pref_dict['interests'] = sorted(pref_dict['interests'])
        
        return dict(sorted(pref_dict.items()))


# Simplified test function
if __name__ == "__main__":
    async def test_caching():
        """Test the caching functionality"""
        import time
        from datetime import timedelta
        
        service = ItineraryService()
        test_request = ItineraryRequest(
            destination="Lat: 52.5200, Lng: 13.4050", 
            travel_dates=[date.today(), date.today() + timedelta(days=1)],
            preferences={"interests": ["Food", "History"]},
            radius=50
        )
        
        print("Testing cache functionality...")
        
        # First request
        start_time = time.time()
        result1 = await service.generate_itinerary(test_request)
        duration1 = time.time() - start_time
        print(f"First request: {duration1:.2f}s, From cache: {result1.get('cache_info', {}).get('from_cache', False)}")
        
        # Second request (should use cache)
        start_time = time.time()
        result2 = await service.generate_itinerary(test_request)
        duration2 = time.time() - start_time
        print(f"Second request: {duration2:.2f}s, From cache: {result2.get('cache_info', {}).get('from_cache', False)}")
        
        if duration1 > 0 and duration2 > 0:
            improvement = duration1 / duration2
            print(f"Performance improvement: {improvement:.1f}x faster")
        
        stats = await service.get_cache_stats()
        print(f"Cache stats: {stats}")
    
    import asyncio
    asyncio.run(test_caching())