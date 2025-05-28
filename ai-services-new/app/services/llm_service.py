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
        
        self.request_timeout = 120  
        
        logger.info("LLM Service initialized with caching enabled")
        
    def repair_json_aggressive(self, json_str: str) -> str:
        """More aggressive JSON repair with comprehensive error handling"""
        print("🔧 Applying aggressive JSON repairs...")
        
        try:
    
            json_str = repair_json_basic(json_str)
            
      
            array_match = re.search(r'\[.*\]', json_str, re.DOTALL)
            if array_match:
                json_str = array_match.group()
                print("🔧 Extracted main JSON array")
            else:
                print("⚠️ No JSON array found, working with full string")
            
           
            json_str = json_str.strip()
            
            if not json_str.startswith('['):
             
                bracket_pos = json_str.find('[')
                if bracket_pos != -1:
                    json_str = json_str[bracket_pos:]
            
            if not json_str.endswith(']'):
                
                bracket_pos = json_str.rfind(']')
                if bracket_pos != -1:
                    json_str = json_str[:bracket_pos + 1]
            
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            if open_braces > close_braces:
                missing_braces = open_braces - close_braces
               
                if json_str.endswith(']'):
                    json_str = json_str[:-1] + '}' * missing_braces + ']'
                else:
                    json_str = json_str + '}' * missing_braces
                print(f"🔧 Added {missing_braces} missing closing braces")
            
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')
            if open_brackets > close_brackets:
                missing_brackets = open_brackets - close_brackets
                json_str = json_str + ']' * missing_brackets
                print(f"🔧 Added {missing_brackets} missing closing brackets")
            
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            json_str = re.sub(r'(\})\s*(\{)', r'\1,\2', json_str)
            
            final_bracket = json_str.rfind(']')
            if final_bracket != -1:
                json_str = json_str[:final_bracket + 1]
            
            print("🔧 Aggressive JSON repair completed successfully")
            return json_str
            
        except Exception as e:
            print(f"❌ Error in aggressive JSON repair: {e}")
        
            return json_str

    async def generate_itinerary(self, destination: str, travel_dates: List[str], 
                               preferences: Dict[str, Any], radius: int) -> Dict[str, Any]:
        """
        Generate a travel itinerary with intelligent caching and retry logic
        """
        try:
 
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
            
     
            self.cache_service.cache_response(
                destination, travel_dates, preferences, radius, enhanced_itinerary
            )
            
            logger.info(f"Successfully generated and cached itinerary for {destination}")
            return enhanced_itinerary
            
        except Exception as e:
            logger.error(f"Error generating itinerary: {str(e)}")
        
            lat, lng = self._parse_coordinates(destination)
            fallback = self._create_fallback_itinerary(travel_dates)
            return await self._enhance_itinerary(fallback, lat, lng, {}, {})

    async def _generate_with_retries(self, prompt: str, travel_dates: List[str]) -> Dict[str, Any]:
        """
        Generate itinerary with LLM, retrying if JSON parsing fails
        """
        for attempt in range(self.max_retries + 1): 
            try:
                logger.info(f"🎯 LLM generation attempt {attempt + 1}/{self.max_retries + 1}")
       
                raw_response = await self._call_ollama(prompt)
             
                structured_itinerary = self._parse_llm_response_with_validation(raw_response, travel_dates)
                
                if structured_itinerary:
                    logger.info(f"✅ Successfully generated valid itinerary on attempt {attempt + 1}")
                    return structured_itinerary
                else:
                   
                    if attempt < self.max_retries:
                        logger.warning(f"❌ JSON parsing failed on attempt {attempt + 1}, retrying in {self.retry_delay}s...")
                        await asyncio.sleep(self.retry_delay)
                       
                        prompt = self._modify_prompt_for_retry(prompt, attempt)
                    else:
                        logger.error(f"❌ All {self.max_retries + 1} attempts failed, using fallback")
                        break
                        
            except Exception as e:
                logger.error(f"❌ LLM generation attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries:
                    logger.info(f"🔄 Retrying in {self.retry_delay}s...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"❌ All {self.max_retries + 1} attempts failed due to errors")
                    break
        
      
        logger.info("🔄 Creating fallback itinerary after all retries failed")
        return self._create_fallback_itinerary(travel_dates)

    def _modify_prompt_for_retry(self, original_prompt: str, attempt_number: int) -> str:
        """
        Slightly modify the prompt for retry attempts to encourage different responses
        """
        retry_instructions = [
            "\n\nIMPORTANT: Please ensure your response is VALID JSON format with proper commas and brackets.",
            "\n\nNOTE: Your previous response had JSON formatting issues. Please be extra careful with JSON syntax.",
            "\n\nREMINDER: Respond ONLY with valid JSON. Double-check all commas, brackets, and quotation marks.",
        ]
        
        if attempt_number < len(retry_instructions):
            return original_prompt + retry_instructions[attempt_number]
        else:
            return original_prompt + retry_instructions[-1]

    def _parse_llm_response_with_validation(self, raw_response: str, travel_dates: List[str]) -> Optional[Dict[str, Any]]:
        """
        Parse and validate LLM response with comprehensive JSON repair
        Returns None if parsing fails after all attempts
        """
        try:
            logger.info("🔍 Parsing LLM response...")
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("❌ No JSON found in response")
                return None
            
            json_str = raw_response[json_start:json_end]
            logger.info(f"📄 Extracted JSON string (length: {len(json_str)})")
            
            try:
                parsed = json.loads(json_str)
                logger.info("✅ Original JSON parsed successfully!")
                
                if not self._validate_itinerary_structure(parsed, travel_dates):
                    logger.warning("❌ JSON structure validation failed")
                    return None
                
                return parsed
                
            except json.JSONDecodeError as e:
                logger.warning(f"❌ Initial JSON parsing failed: {e}")
                logger.info("🔧 Attempting JSON repair...")
                
                repair_strategies = [
                    ("Basic repair", repair_json_basic),
                    ("Missing commas fix", fix_missing_commas),
                    ("Smart comma repair", smart_comma_repair),
                    ("Character-level repair", character_level_repair),
                    ("Aggressive repair", self.repair_json_aggressive),
                    ("Final validation repair", validate_and_repair_json)
                ]
                
                for strategy_name, repair_func in repair_strategies:
                    try:
                        logger.info(f"🔧 Trying {strategy_name}...")
                        repaired_json = repair_func(json_str)
                        
                        parsed = json.loads(repaired_json)
                        logger.info(f"✅ {strategy_name} successful!")
                        
                        if not self._validate_itinerary_structure(parsed, travel_dates):
                            logger.warning(f"❌ {strategy_name} produced invalid structure")
                            continue
                        
                        logger.info(f"🎉 Successfully repaired and validated JSON using {strategy_name}")
                        return parsed
                        
                    except json.JSONDecodeError as repair_error:
                        logger.warning(f"❌ {strategy_name} failed: {repair_error}")
                        continue
                    except Exception as repair_error:
                        logger.warning(f"❌ {strategy_name} error: {repair_error}")
                        continue
                
                logger.error("❌ All JSON repair strategies failed - will trigger LLM retry")
                logger.debug(f"Problematic JSON (first 500 chars): {json_str[:500]}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Unexpected error in LLM response parsing: {e}")
            return None

    def _validate_itinerary_structure(self, parsed_data: Dict[str, Any], travel_dates: List[str]) -> bool:
        """
        Validate that the parsed JSON has the correct structure for an itinerary
        """
        try:
    
            if "plan" not in parsed_data:
                logger.warning("Missing 'plan' key in parsed JSON")
                return False
            
            plan = parsed_data["plan"]
            if not isinstance(plan, list):
                logger.warning("'plan' is not a list")
                return False
            
            if len(plan) != len(travel_dates):
                logger.warning(f"Plan has {len(plan)} days but {len(travel_dates)} dates provided")
            
            for i, day_plan in enumerate(plan):
                if not isinstance(day_plan, dict):
                    logger.warning(f"Day {i+1} plan is not a dictionary")
                    return False
       
                required_fields = ["day", "date", "town", "place", "activities"]
                for field in required_fields:
                    if field not in day_plan:
                        logger.warning(f"Day {i+1} missing required field: {field}")
                        return False
                
          
                if not isinstance(day_plan.get("activities"), list):
                    logger.warning(f"Day {i+1} activities is not a list")
                    return False
            
            logger.info("✅ Itinerary structure validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error validating itinerary structure: {e}")
            return False
    
    async def generate_plan(self, request, nearby_cities: List[str]) -> List[Dict[str, Any]]:
        """
        Generate travel plan - this is what ItineraryService expects
        """
        try:
            
            destination = request.destination
            travel_dates = [str(d) for d in request.travel_dates]
            
            preferences = {}
            if hasattr(request, 'preferences'):
                if hasattr(request.preferences, '__dict__'):
                    preferences = request.preferences.__dict__
                elif hasattr(request.preferences, 'interests'):
                    preferences = {"interests": request.preferences.interests}
                elif isinstance(request.preferences, dict):
                    preferences = request.preferences
                else:
                    preferences = {}
            
            radius = request.radius
            
            logger.info(f"🎯 generate_plan called for {destination} with {len(travel_dates)} days")
            
            full_itinerary = await self.generate_itinerary(destination, travel_dates, preferences, radius)
            
            plan = full_itinerary.get('plan', [])
            logger.info(f"✅ Generated plan with {len(plan)} days")
            
            return plan
            
        except Exception as e:
            logger.error(f"Error in generate_plan: {e}")
            
            return self._create_simple_fallback_plan(request, nearby_cities)
    
    async def generate_fallback_plan(self, request, lat: float, lng: float, nearby_cities: List[str]) -> List[Dict[str, Any]]:
        """
        Generate fallback plan when main generation fails
        """
        try:
            logger.info("🔄 Generating fallback plan")
            return self._create_simple_fallback_plan(request, nearby_cities, lat, lng)
            
        except Exception as e:
            logger.error(f"Error in generate_fallback_plan: {e}")
           
            return self._create_minimal_fallback(request, lat, lng)
    
    def _create_simple_fallback_plan(self, request, nearby_cities: List[str], lat: float = None, lng: float = None) -> List[Dict[str, Any]]:
        """Create a simple fallback plan with proper city rotation"""
        try:
            if lat is None or lng is None:
                lat, lng = self._parse_coordinates(request.destination)
            
            plan = []
            
            if not nearby_cities:
                nearby_cities = ["Local Area", "City Center", "Downtown"]
            
            unique_cities = []
            seen = set()
            for city in nearby_cities:
                if city not in seen:
                    unique_cities.append(city)
                    seen.add(city)
            
            nearby_cities = unique_cities
            
            for i, date in enumerate(request.travel_dates):
                
                city_index = i % len(nearby_cities)
                current_city = nearby_cities[city_index]
                
                day_plan = {
                    "day": i + 1,
                    "date": str(date),
                    "formatted_date": date.strftime('%B %d, %Y'),
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
            
            logger.info(f"✅ Generated simple fallback plan with {len(plan)} days using {len(nearby_cities)} unique cities")
            return plan
            
        except Exception as e:
            logger.error(f"Error creating simple fallback plan: {e}")
            return self._create_minimal_fallback(request, lat or 0.0, lng or 0.0)
    
    def _create_minimal_fallback(self, request, lat: float, lng: float) -> List[Dict[str, Any]]:
        """Create the most basic fallback plan possible"""
        plan = []
        for i, date in enumerate(request.travel_dates):
            day_plan = {
                "day": i + 1,
                "date": str(date),
                "formatted_date": date.strftime('%B %d, %Y'),
                "town": "Local Area",
                "place": "City Center",
                "activities": [
                    "Morning: Explore local attractions",
                    "Lunch: Try local cuisine",
                    "Afternoon: Visit cultural sites",
                    "Evening: Enjoy local atmosphere"
                ],
                "lat": lat,
                "lng": lng,
                "distance_from_start": 0.0,
                "estimated_cost": "€50-100 per person",
                "weather_note": "Check local weather conditions"
            }
            plan.append(day_plan)
        return plan
    
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
        
        try:
            if self.location_service:
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
        
        try:
            if self.weather_service:
                weather_data = await self.weather_service.get_forecast_for_dates(lat, lng, travel_dates)
                if weather_data:
                    return weather_data
        except Exception as e:
            logger.warning(f"Could not get weather data: {e}")
        
        return default_weather
    
    def _build_itinerary_prompt(self, location_info: Dict, travel_dates: List[str], 
                               preferences: Dict, radius: int, weather_data: Dict) -> str:
        """Build comprehensive prompt for LLM"""
        
       
        interests = preferences.get("interests", [])
        budget_level = preferences.get("budget", "moderate")
        group_size = preferences.get("group_size", 1)
        accommodation_type = preferences.get("accommodation", "any")
        
        main_location = location_info.get("main_location", {"city": "Unknown", "country": "Unknown"})
        nearby_cities = location_info.get("nearby_cities", [])
        
    
        weather_info = ""
        if weather_data and weather_data.get("forecast"):
            weather_info = "\n\nWeather Forecast:\n"
            for forecast in weather_data["forecast"]:
                weather_info += f"- {forecast.get('date')}: {forecast.get('description')}, {forecast.get('temperature')}°C\n"
        
        
        nearby_city_names = []
        for city in nearby_cities[:5]:
            if isinstance(city, dict):
                nearby_city_names.append(city.get('name', str(city)))
            else:
                nearby_city_names.append(str(city))
        
        prompt = f"""You are an expert travel planner. Create a detailed day-by-day itinerary for a trip with the following requirements:

LOCATION DETAILS:
- Main destination: {main_location.get('city', 'Unknown')}, {main_location.get('country', 'Unknown')}
- Coordinates: {location_info.get('coordinates', {}).get('lat', 0)}, {location_info.get('coordinates', {}).get('lng', 0)}
- Search radius: {radius}km
- Nearby cities to consider: {', '.join(nearby_city_names) if nearby_city_names else 'Local area'}
- Each destination should be unique 

TRAVEL DETAILS:
- Travel dates: {', '.join(travel_dates)}
- Duration: {len(travel_dates)} days
- Group size: {group_size} people
- Budget level: {budget_level}
- Accommodation preference: {accommodation_type}

INTERESTS AND PREFERENCES:
- Primary interests: {', '.join(interests) if interests else 'General sightseeing'}

{weather_info}

REQUIREMENTS:
1. Create a detailed day-by-day plan for each date
2. Include specific places to visit with approximate coordinates
3. Consider travel time between locations
4. Include meal recommendations
5. Account for weather conditions in activity selection
6. Provide practical information like opening hours and ticket prices
7. Optimize routes to minimize travel distance
8. Include a mix of must-see attractions and hidden gems

CRITICAL: You MUST respond with VALID JSON only. Double-check all commas, brackets, and quotation marks.

FORMAT YOUR RESPONSE AS VALID JSON with this exact structure:
{{
  "plan": [
    {{
      "day": 1,
      "date": "{travel_dates[0] if travel_dates else '2025-06-15'}",
      "formatted_date": "June 15, 2025",
      "town": "City Name",
      "place": "Main attraction/area for the day",
      "activities": [
        "Morning: Visit specific location (opening hours, estimated cost)",
        "Lunch: Restaurant recommendation with cuisine type",
        "Afternoon: Another activity with details",
        "Evening: Dinner and evening activity"
      ],
      "lat": 52.5200,
      "lng": 13.4050,
      "distance_from_start": 0.0,
      "estimated_cost": "€50-80 per person",
      "weather_note": "Perfect weather for outdoor activities"
    }}
  ],
  "summary": {{
    "total_estimated_cost": "€200-400 per person",
    "best_season": "Spring/Summer",
    "recommended_duration": "{len(travel_dates)} days",
    "difficulty_level": "Easy/Moderate/Challenging",
    "transportation_tips": "Best ways to get around",
    "cultural_notes": "Important cultural information"
  }}
}}

Ensure all coordinates are within the specified radius and activities match the stated interests. Be specific with place names, addresses where possible, and practical details."""

        return prompt
    
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
    
    def _create_fallback_itinerary(self, travel_dates: List[str]) -> Dict[str, Any]:
        """Create a basic fallback itinerary if LLM parsing fails"""
        plan = []
        for i, date in enumerate(travel_dates):
            day_plan = {
                "day": i + 1,
                "date": date,
                "formatted_date": datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y"),
                "town": "Destination",
                "place": "City Center",
                "activities": [
                    "Morning: Explore the city center and main attractions",
                    "Lunch: Try local cuisine at a recommended restaurant",
                    "Afternoon: Visit museums or cultural sites",
                    "Evening: Enjoy dinner and local nightlife"
                ],
                "lat": 0.0,
                "lng": 0.0,
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
    
    async def _enhance_itinerary(self, itinerary: Dict, lat: float, lng: float, 
                               weather_data: Dict, location_info: Dict) -> Dict[str, Any]:
        """Enhance the itinerary with additional data"""
        try:
           
            enhanced = {
                **itinerary,
                "weather": weather_data or {},
                "user_coordinates": {"lat": lat, "lng": lng},
                "nearby_cities": [city.get("name") if isinstance(city, dict) else str(city) for city in location_info.get("nearby_cities", [])],
                "generated_at": datetime.utcnow().isoformat(),
                "cache_info": {
                    "generated_fresh": True,
                    "cache_enabled": self.cache_service.cache_enabled
                }
            }
            
         
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
        
        R = 6371  
        
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