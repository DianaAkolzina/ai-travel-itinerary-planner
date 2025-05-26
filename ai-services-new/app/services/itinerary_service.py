import re
from typing import Dict, Any, List
from datetime import date
from app.models.requests import ItineraryRequest
from app.services.location_service import LocationService
from app.services.weather_service import WeatherService
from app.services.llm_service import LLMService
from app.services.route_optimizer import RouteOptimizer

class ItineraryService:
    """Main service for generating travel itineraries"""
    
    def __init__(self):
        self.location_service = LocationService()
        self.weather_service = WeatherService()
        self.llm_service = LLMService()
        self.route_optimizer = RouteOptimizer()
    
    async def generate_itinerary(self, request: ItineraryRequest) -> Dict[str, Any]:
        """Generate a complete travel itinerary for specific dates"""
        
    
        if not request.destination:
            raise ValueError("Destination must be provided.")
        
        if not request.travel_dates or len(request.travel_dates) == 0:
            raise ValueError("At least one travel date must be provided.")
        
        sorted_dates = sorted(request.travel_dates)
        num_days = len(sorted_dates)
        
        print(f"🗓️ Planning itinerary for {num_days} days: {sorted_dates}")
        
        lat, lng = self._parse_coordinates(request.destination)
        if lat is None or lng is None:
            print("❌ Invalid coordinates format")
            return {"plan": []}
        
        print(f"🌍 Coordinates: {lat}, {lng}")
        
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
        
  
        try:
            raw_plan = await self.llm_service.generate_plan(request, nearby_cities)
            if not raw_plan:
                print("⚠️ LLM failed to generate plan, using fallback")
                raw_plan = await self.llm_service.generate_fallback_plan(request, lat, lng, nearby_cities)
        except Exception as e:
            print(f"❌ LLM service error: {e}")
            raw_plan = await self.llm_service.generate_fallback_plan(request, lat, lng, nearby_cities)
        
   
        enriched_plan = await self.location_service.enrich_and_validate_plan(
            (lat, lng), raw_plan, request.radius
        )
        
        if len(enriched_plan) > 1:
            enriched_plan = self.route_optimizer.optimize_route((lat, lng), enriched_plan)
   
        for i, day_plan in enumerate(enriched_plan):
            if i < len(sorted_dates):
                day_plan['date'] = str(sorted_dates[i])
                day_plan['formatted_date'] = sorted_dates[i].strftime('%B %d, %Y')
        
        print("✅ Final Enriched Plan:", enriched_plan)
        

        weather_data = await self.weather_service.get_forecast_for_dates(lat, lng, sorted_dates)
        

        response = {
            "plan": enriched_plan,
            "nearby_cities": nearby_cities,
            "user_coordinates": {"lat": lat, "lng": lng},
            "search_radius": request.radius,
            "travel_dates": [str(d) for d in sorted_dates],
            "total_days": num_days
        }
        
        
        if weather_data:
            response["weather"] = weather_data
            print(f"✅ Weather forecast included for {len(weather_data['forecast'])} days")
        else:
            print("ℹ️ No weather forecast included - not available for requested dates")
        
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