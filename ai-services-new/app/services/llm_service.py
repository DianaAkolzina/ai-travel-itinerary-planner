import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import aiohttp
from .cache_service import CacheService
from ..utils.json_repair import *

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        """Initialize the LLM service with caching and external services"""
        self.ollama_base_url = "http://localhost:11434" 
        self.model_name = "llama3"
        self.cache_service = CacheService()
        self.max_retries = 3  
        self.retry_delay = 2  
        self.request_timeout = 120  
        
        # Initialize optional services
        try:
            from app.services.weather_service import WeatherService
            self.weather_service = WeatherService()
        except ImportError:
            logger.warning("WeatherService not available")
            self.weather_service = None
            
        try:
            from app.services.location_service import LocationService
            self.location_service = LocationService()
        except ImportError:
            logger.warning("LocationService not available")
            self.location_service = None
        
        logger.info("LLM Service initialized with caching enabled")

    async def generate_itinerary(self, destination: str, travel_dates: List[str], 
                               preferences: Dict[str, Any], radius: int) -> Dict[str, Any]:
        """Generate a travel itinerary with intelligent caching and retry logic"""
        try:
            # Check cache first
            cached_response = self.cache_service.get_cached_response(
                destination, travel_dates, preferences, radius
            )
            
            if cached_response:
                logger.info(f"Cache hit for destination: {destination}")
                return cached_response
            
            logger.info(f"Generating new itinerary for destination: {destination}")
            
            lat, lng = self._parse_coordinates(destination)
            location_info = await self._get_location_context(lat, lng, radius)
            weather_data = await self._get_weather_forecast(lat, lng, travel_dates)
            
            prompt = self._build_itinerary_prompt(
                location_info, travel_dates, preferences, radius, weather_data
            )
            
            structured_itinerary = await self._generate_with_retries(prompt, travel_dates)
            enhanced_itinerary = await self._enhance_itinerary(
                structured_itinerary, lat, lng, weather_data, location_info
            )
            
            # Cache the result
            self.cache_service.cache_response(
                destination, travel_dates, preferences, radius, enhanced_itinerary
            )
            
            logger.info(f"Successfully generated and cached itinerary for {destination}")
            return enhanced_itinerary
            
        except Exception as e:
            logger.error(f"Error generating itinerary: {str(e)}")
            lat, lng = self._parse_coordinates(destination)
            fallback = self._create_fallback_itinerary(travel_dates, lat, lng)
            return await self._enhance_itinerary(fallback, lat, lng, {}, {})

    async def _generate_with_retries(self, prompt: str, travel_dates: List[str]) -> Dict[str, Any]:
        """Generate itinerary with LLM, retrying if JSON parsing fails"""
        for attempt in range(self.max_retries + 1): 
            try:
                logger.info(f"LLM generation attempt {attempt + 1}/{self.max_retries + 1}")
                raw_response = await self._call_ollama(prompt)
                structured_itinerary = self._parse_llm_response_with_validation(raw_response, travel_dates)
                
                if structured_itinerary:
                    logger.info(f"Successfully generated valid itinerary on attempt {attempt + 1}")
                    return structured_itinerary
                    
                if attempt < self.max_retries:
                    logger.warning(f"JSON parsing failed on attempt {attempt + 1}, retrying in {self.retry_delay}s...")
                    await asyncio.sleep(self.retry_delay)
                    prompt = self._modify_prompt_for_retry(prompt, attempt)
                        
            except Exception as e:
                logger.error(f"LLM generation attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay}s...")
                    await asyncio.sleep(self.retry_delay)
        
        logger.info("Creating fallback itinerary after all retries failed")
        return self._create_fallback_itinerary(travel_dates)

    def _modify_prompt_for_retry(self, original_prompt: str, attempt_number: int) -> str:
        """Modify the prompt for retry attempts to encourage different responses"""
        retry_instructions = [
            "\n\nIMPORTANT: Please ensure your response is VALID JSON format with proper commas and brackets.",
            "\n\nNOTE: Your previous response had JSON formatting issues. Please be extra careful with JSON syntax.",
            "\n\nREMINDER: Respond ONLY with valid JSON. Double-check all commas, brackets, and quotation marks.",
        ]
        
        instruction = retry_instructions[min(attempt_number, len(retry_instructions) - 1)]
        return original_prompt + instruction

    def _parse_llm_response_with_validation(self, raw_response: str, travel_dates: List[str]) -> Optional[Dict[str, Any]]:
        """Parse and validate LLM response with JSON repair"""
        try:
            logger.info("Parsing LLM response...")
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON found in response")
                return None
            
            json_str = raw_response[json_start:json_end]
            
            # Try direct parsing first
            try:
                parsed = json.loads(json_str)
                if self._validate_itinerary_structure(parsed, travel_dates):
                    logger.info("Original JSON parsed successfully!")
                    return parsed
            except json.JSONDecodeError:
                pass
            
            # Try repair strategies
            repair_strategies = [
                repair_json_basic,
                fix_missing_commas,
                smart_comma_repair,
                character_level_repair,
                validate_and_repair_json
            ]
            
            for i, repair_func in enumerate(repair_strategies):
                try:
                    logger.info(f"Trying repair strategy {i + 1}...")
                    repaired_json = repair_func(json_str)
                    parsed = json.loads(repaired_json)
                    
                    if self._validate_itinerary_structure(parsed, travel_dates):
                        logger.info(f"Successfully repaired JSON using strategy {i + 1}")
                        return parsed
                        
                except Exception as e:
                    logger.warning(f"Repair strategy {i + 1} failed: {e}")
                    continue
            
            logger.error("All JSON repair strategies failed")
            return None
                
        except Exception as e:
            logger.error(f"Unexpected error in LLM response parsing: {e}")
            return None

    def _validate_itinerary_structure(self, parsed_data: Dict[str, Any], travel_dates: List[str]) -> bool:
        """Validate that the parsed JSON has the correct structure for an itinerary"""
        try:
            if "plan" not in parsed_data or not isinstance(parsed_data["plan"], list):
                return False
            
            plan = parsed_data["plan"]
            
            for i, day_plan in enumerate(plan):
                if not isinstance(day_plan, dict):
                    return False
                    
                required_fields = ["day", "date", "town", "place", "activities"]
                if not all(field in day_plan for field in required_fields):
                    return False
                
                if not isinstance(day_plan.get("activities"), list):
                    return False
            
            logger.info("Itinerary structure validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error validating itinerary structure: {e}")
            return False
    
    async def generate_plan(self, request, nearby_cities: List[str]) -> List[Dict[str, Any]]:
        """Generate travel plan - this is what ItineraryService expects"""
        try:
            destination = request.destination
            travel_dates = [str(d) for d in request.travel_dates]
            
            # Extract preferences
            preferences = {}
            if hasattr(request, 'preferences'):
                if hasattr(request.preferences, '__dict__'):
                    preferences = request.preferences.__dict__
                elif hasattr(request.preferences, 'interests'):
                    preferences = {"interests": request.preferences.interests}
                elif isinstance(request.preferences, dict):
                    preferences = request.preferences
            
            radius = request.radius
            logger.info(f"generate_plan called for {destination} with {len(travel_dates)} days")
            
            full_itinerary = await self.generate_itinerary(destination, travel_dates, preferences, radius)
            plan = full_itinerary.get('plan', [])
            logger.info(f"Generated plan with {len(plan)} days")
            
            return plan
            
        except Exception as e:
            logger.error(f"Error in generate_plan: {e}")
            lat, lng = self._parse_coordinates(request.destination)
            return self._create_fallback_itinerary(
                [str(d) for d in request.travel_dates], lat, lng, nearby_cities
            ).get('plan', [])
    
    def _create_fallback_itinerary(self, travel_dates: List[str], lat: float = 0.0, lng: float = 0.0, 
                                 nearby_cities: List[str] = None) -> Dict[str, Any]:
        """Unified fallback itinerary creation - replaces all similar functions"""
        try:
            if nearby_cities is None:
                nearby_cities = ["Local Area", "City Center", "Downtown"]
            
            # Remove duplicates while preserving order
            unique_cities = []
            seen = set()
            for city in nearby_cities:
                city_name = city.get('name') if isinstance(city, dict) else str(city)
                if city_name not in seen:
                    unique_cities.append(city_name)
                    seen.add(city_name)
            
            if not unique_cities:
                unique_cities = ["Local Area"]
            
            plan = []
            for i, date in enumerate(travel_dates):
                # Rotate through available cities
                city_index = i % len(unique_cities)
                current_city = unique_cities[city_index]
                
                # Handle date formatting
                try:
                    if isinstance(date, str):
                        date_obj = datetime.strptime(date, "%Y-%m-%d")
                        formatted_date = date_obj.strftime("%B %d, %Y")
                    else:
                        formatted_date = date.strftime("%B %d, %Y")
                        date = str(date)
                except:
                    formatted_date = date
                
                day_plan = {
                    "day": i + 1,
                    "date": date,
                    "formatted_date": formatted_date,
                    "town": current_city,
                    "place": f"{current_city} Center",
                    "activities": [
                        f"Morning: Explore {current_city} historic center and main attractions",
                        f"Lunch: Try traditional local cuisine in {current_city}",
                        f"Afternoon: Visit cultural sites and museums in {current_city}",
                        f"Evening: Experience {current_city} local atmosphere and dining"
                    ],
                    "lat": lat,
                    "lng": lng,
                    "distance_from_start": 0.0,
                    "estimated_cost": "€50-100 per person",
                    "weather_note": "Check local weather conditions"
                }
                plan.append(day_plan)
            
            return {
                "plan": plan,
                "summary": {
                    "total_estimated_cost": f"€{50 * len(travel_dates)}-{100 * len(travel_dates)} per person",
                    "best_season": "Year-round",
                    "recommended_duration": f"{len(travel_dates)} days",
                    "difficulty_level": "Moderate",
                    "transportation_tips": "Use public transportation or walking",
                    "cultural_notes": "Respect local customs and traditions"
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating fallback itinerary: {e}")
            # Return minimal fallback
            return {
                "plan": [{
                    "day": 1,
                    "date": travel_dates[0] if travel_dates else "2025-06-01",
                    "formatted_date": "June 1, 2025",
                    "town": "Local Area",
                    "place": "City Center", 
                    "activities": ["Explore local attractions"],
                    "lat": lat,
                    "lng": lng,
                    "distance_from_start": 0.0,
                    "estimated_cost": "€50-100 per person",
                    "weather_note": "Check local weather conditions"
                }],
                "summary": {"total_estimated_cost": "€50-100 per person"}
            }
    
    def _parse_coordinates(self, destination: str) -> tuple:
        """Parse coordinates from destination string format 'Lat: X, Lng: Y'"""
        try:
            parts = destination.replace("Lat:", "").replace("Lng:", "").split(",")
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            return lat, lng
        except (ValueError, IndexError):
            logger.error(f"Invalid destination format: {destination}")
            return 0.0, 0.0
    
    async def _get_location_context(self, lat: float, lng: float, radius: int) -> Dict[str, Any]:
        """Get location context including city name, country, nearby places"""
        default_context = {
            "main_location": {"city": "Unknown", "country": "Unknown"},
            "nearby_cities": [],
            "coordinates": {"lat": lat, "lng": lng},
            "radius": radius
        }
        
        if not self.location_service:
            return default_context
            
        try:
            location_info = await self.location_service.get_location_details(lat, lng)
            nearby_cities = await self.location_service.get_nearby_cities(lat, lng, radius)
            
            if location_info:
                default_context["main_location"] = location_info
            if nearby_cities:
                default_context["nearby_cities"] = nearby_cities
                
        except Exception as e:
            logger.warning(f"Could not get full location context: {e}")
        
        return default_context
    
    async def _get_weather_forecast(self, lat: float, lng: float, travel_dates: List[str]) -> Dict[str, Any]:
        """Get weather forecast for the travel dates"""
        default_weather = {
            "forecast": [],
            "location": "Unknown",
            "missing_dates": travel_dates
        }
        
        if not self.weather_service:
            return default_weather
            
        try:
            weather_data = await self.weather_service.get_forecast_for_dates(lat, lng, travel_dates)
            return weather_data if weather_data else default_weather
        except Exception as e:
            logger.warning(f"Could not get weather data: {e}")
            return default_weather
    
    def _build_itinerary_prompt(self, location_info: Dict, travel_dates: List[str], 
                               preferences: Dict, radius: int, weather_data: Dict) -> str:
        """Build comprehensive prompt for LLM"""
        
        # Extract preferences
        interests = preferences.get("interests", [])
        budget_level = preferences.get("budget", "moderate")
        group_size = preferences.get("group_size", 1)
        accommodation_type = preferences.get("accommodation", "any")
        
        main_location = location_info.get("main_location", {"city": "Unknown", "country": "Unknown"})
        nearby_cities = location_info.get("nearby_cities", [])
        
        # Build weather info
        weather_info = ""
        if weather_data.get("forecast"):
            weather_info = "\n\nWeather Forecast:\n"
            for forecast in weather_data["forecast"]:
                weather_info += f"- {forecast.get('date')}: {forecast.get('description')}, {forecast.get('temperature')}°C\n"
        
        # Extract nearby city names
        nearby_city_names = [
            city.get('name', str(city)) if isinstance(city, dict) else str(city) 
            for city in nearby_cities[:5]
        ]
        
        return f"""You are an expert travel planner. Create a detailed day-by-day itinerary.

LOCATION: {main_location.get('city', 'Unknown')}, {main_location.get('country', 'Unknown')}
COORDINATES: {location_info.get('coordinates', {}).get('lat', 0)}, {location_info.get('coordinates', {}).get('lng', 0)}
RADIUS: {radius}km
NEARBY CITIES: {', '.join(nearby_city_names) if nearby_city_names else 'Local area'}

TRAVEL DETAILS:
- Dates: {', '.join(travel_dates)} ({len(travel_dates)} days)
- Group: {group_size} people
- Budget: {budget_level}
- Interests: {', '.join(interests) if interests else 'General sightseeing'}
{weather_info}

RESPOND WITH VALID JSON ONLY:
{{
  "plan": [
    {{
      "day": 1,
      "date": "{travel_dates[0] if travel_dates else '2025-06-15'}",
      "formatted_date": "June 15, 2025",
      "town": "City Name",
      "place": "Main attraction/area",
      "activities": [
        "Morning: Specific activity with details",
        "Lunch: Restaurant recommendation",
        "Afternoon: Another activity",
        "Evening: Dinner and evening activity"
      ],
      "lat": 52.5200,
      "lng": 13.4050,
      "distance_from_start": 0.0,
      "estimated_cost": "€50-80 per person",
      "weather_note": "Weather-appropriate note"
    }}
  ],
  "summary": {{
    "total_estimated_cost": "€200-400 per person",
    "best_season": "Spring/Summer",
    "recommended_duration": "{len(travel_dates)} days",
    "difficulty_level": "Easy/Moderate/Challenging",
    "transportation_tips": "Best transportation methods",
    "cultural_notes": "Important cultural information"
  }}
}}"""
    
    async def _call_ollama(self, prompt: str) -> str:
        """Make async call to Ollama API"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.request_timeout)) as session:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 4000
                    }
                }
                
                async with session.post(f"{self.ollama_base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama API returned status {response.status}")
                    
                    result = await response.json()
                    return result.get("response", "")
                    
        except asyncio.TimeoutError:
            raise Exception("LLM request timed out")
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise Exception(f"LLM service unavailable: {str(e)}")
    
    async def _enhance_itinerary(self, itinerary: Dict, lat: float, lng: float, 
                               weather_data: Dict, location_info: Dict) -> Dict[str, Any]:
        """Enhance the itinerary with additional data"""
        try:
            enhanced = {
                **itinerary,
                "weather": weather_data or {},
                "user_coordinates": {"lat": lat, "lng": lng},
                "nearby_cities": [
                    city.get("name") if isinstance(city, dict) else str(city) 
                    for city in location_info.get("nearby_cities", [])
                ],
                "generated_at": datetime.utcnow().isoformat(),
                "cache_info": {
                    "generated_fresh": True,
                    "cache_enabled": self.cache_service.cache_enabled
                }
            }
            
            # Calculate distances
            for day_plan in enhanced.get("plan", []):
                if day_plan.get("lat") and day_plan.get("lng"):
                    distance = self._calculate_distance(
                        lat, lng, day_plan["lat"], day_plan["lng"]
                    )
                    day_plan["distance_from_start"] = round(distance, 1)
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"Could not enhance itinerary: {e}")
            return itinerary or {}
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        import math
        
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    async def get_cached_itinerary_count(self) -> int:
        """Get count of cached itineraries"""
        stats = self.cache_service.get_cache_stats()
        return stats.get("mongodb_active_entries", stats.get("memory_entries", 0))
    
    async def clear_expired_cache(self) -> None:
        """Clear expired cache entries"""
        self.cache_service.cleanup_expired_cache()
    
    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled"""
        return self.cache_service.cache_enabled