import json
import re
from typing import List 
from datetime import date  
from app.external.llm_client import LLMClient
from app.utils.json_repair import JSONRepairer
from app.utils.validators import validate_parsed_plan
from app.services.location_service import LocationService

class LLMService:
    """Service for handling LLM operations"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.json_repairer = JSONRepairer()
        self.location_service = LocationService()
    
    async def generate_plan(self, request, nearby_cities: list) -> list:
        """Generate travel plan using LLM"""
       
        prompt = self._create_prompt(request, nearby_cities)
        print("🧠 Sending prompt to LLM...")
        
        try:
       
            response_json = await self.llm_client.generate(prompt)
            print("📨 Raw LLM Response received")
            
          
            raw_plan = self._parse_llm_response(response_json, request)
            return raw_plan
            
        except Exception as e:
            print(f"❌ LLM request failed: {e}")
            return None
        
    async def generate_plan_for_dates(self, request, nearby_cities: list, travel_dates: List[date]) -> list:
    
        prompt = self._create_prompt_for_dates(request, nearby_cities, travel_dates)
        print("🧠 Sending date-based prompt to LLM...")
        
        try:
            response_json = await self.llm_client.generate(prompt)
            print("📨 Raw LLM Response received")
            raw_plan = self._parse_llm_response(response_json, request)
            return raw_plan
        except Exception as e:
            print(f"❌ LLM request failed: {e}")
            return None

    def _create_prompt_for_dates(self, request, nearby_cities: list, travel_dates: List[date]) -> str:
        """Create enhanced prompt for LLM with specific dates"""
        location_context = self.location_service.get_location_context(request.destination)
        
        formatted_dates = [d.strftime('%B %d, %Y (%A)') for d in travel_dates]
        
        prompt = f"""You are a local travel expert. Plan a detailed itinerary for specific travel dates near coordinates {request.destination} (STRICTLY within {request.radius} km radius).

        TRAVEL DATES:
    {chr(10).join([f"Day {i+1}: {date}" for i, date in enumerate(formatted_dates)])}

    LOCATION CONTEXT:
    {location_context}

    TRAVELER PREFERENCES:
    - Interested in: {', '.join(request.preferences.interests)}
    - Travel dates: {len(travel_dates)} specific days
    - Maximum travel radius: {request.radius} km

    REQUIREMENTS:
    1. Plan activities for each specific date listed above
    2. Suggest REAL, SPECIFIC places with actual names
    3. Consider day of the week (some attractions may be closed on certain days)
    4. All locations must be within {request.radius} km of the coordinates
    5. Provide 2-4 specific activities per day

    EXAMPLE FORMAT:
    [
    {{
        "day": 1,
        "town": "Łowicz",
        "place": "Łowicz Cathedral and Museum Complex",
        "activities": [
        "Visit the stunning Baroque Łowicz Cathedral with its ornate interior",
        "Explore the Museum of Łowicz Region showcasing traditional folk costumes",
        "Walk through the historic Market Square with colorful townhouses"
        ]
    }}
    ]

    Respond ONLY with valid JSON. Use REAL place names, not generic descriptions."""
        
        return prompt
    
    async def generate_fallback_plan(self, request, lat: float, lng: float, nearby_cities: list) -> list:
        """Generate fallback plan when LLM fails"""
        print("🔄 Generating fallback itinerary...")
        
        fallback_places = [
            {"town": "City Center", "place": "Main Square", "activities": ["Walking tour", "Local exploration"]},
            {"town": "Historic District", "place": "Old Town", "activities": ["Architecture viewing", "Photography"]},
            {"town": "Cultural Area", "place": "Local Museum", "activities": ["Museum visit", "Cultural exploration"]},
            {"town": "Nature Spot", "place": "City Park", "activities": ["Nature walk", "Relaxation"]},
            {"town": "Shopping Area", "place": "Main Street", "activities": ["Shopping", "Local cuisine"]},
        ]
        
        plan = []
        for i in range(len(request.travel_dates)):
            place = fallback_places[i % len(fallback_places)]
            plan.append({
                "day": i + 1,
                "town": nearby_cities[i % len(nearby_cities)] if nearby_cities else place["town"],
                "place": place["place"],
                "activities": place["activities"]
            })
        
        return plan
    
    def _create_prompt(self, request, nearby_cities: list) -> str:
        """Create enhanced prompt for LLM"""
      
        location_context = self.location_service.get_location_context(request.destination)
        
       
        prompt = f"""You are a local travel expert. Plan a detailed {len(request.travel_dates)}-day trip near coordinates {request.destination} (STRICTLY within {request.radius} km radius).

LOCATION CONTEXT:
{location_context}

TRAVELER PREFERENCES:
- Interested in: {', '.join(request.preferences.interests)}
- Trip duration: {len(request.travel_dates)} days
- Maximum travel radius: {request.radius} km

REQUIREMENTS:
1. Suggest REAL, SPECIFIC places with actual names (not generic like "Local Museum" or "Main Square")
2. Include famous landmarks, specific restaurants, actual street names, real attraction names
3. For each place, mention WHY it's worth visiting and what makes it special
4. All locations must be within {request.radius} km of the coordinates
5. Provide 2-4 specific activities per day, mentioning actual things to see/do

EXAMPLE FORMAT (use real place names):
[
  {{
    "day": 1,
    "town": "Łowicz",
    "place": "Łowicz Cathedral and Museum Complex",
    "activities": [
      "Visit the stunning Baroque Łowicz Cathedral with its ornate interior",
      "Explore the Museum of Łowicz Region showcasing traditional folk costumes",
      "Walk through the historic Market Square with colorful townhouses"
    ]
  }}
]

Respond ONLY with valid JSON. Use REAL place names, not generic descriptions."""
        
        return prompt
    
    def _parse_llm_response(self, response_json: dict, request) -> list:
        """Parse LLM response with comprehensive error handling"""
        output = response_json.get("response", "").strip()
        
  
        output = re.sub(r"```(?:json)?", "", output).strip()
        output = re.sub(r"```", "", output).strip()
        
        print("🔍 Raw LLM output preview:", output[:300] + "..." if len(output) > 300 else output)

   
        match = re.search(r"\[\s*{.*?}\s*\]", output, re.DOTALL)
        if not match:
            print("⚠️ Could not extract itinerary JSON from LLM output")
            print("🔍 Full LLM output:", output)
            return None

        json_str = match.group()
        print("🔍 Extracted JSON string length:", len(json_str))
        print("🔍 First 500 chars of JSON:", json_str[:500] + "..." if len(json_str) > 500 else json_str)
        
        expected_days = len(request.travel_dates)
        
        for attempt in range(5):
            try:
                if attempt == 0:
                    raw_plan = json.loads(json_str)
                    print("✅ JSON parsed successfully on first attempt")
                elif attempt == 1:
                    repaired = self.json_repairer.smart_comma_repair(json_str)
                    raw_plan = json.loads(repaired)
                    print("✅ JSON parsed successfully after smart comma repair")
                elif attempt == 2:
                    repaired = self.json_repairer.repair_json_basic(json_str)
                    raw_plan = json.loads(repaired)
                    print("✅ JSON parsed successfully after basic repair")
                elif attempt == 3:
                    repaired = self.json_repairer.repair_json_aggressive(json_str)
                    raw_plan = json.loads(repaired)
                    print("✅ JSON parsed successfully after aggressive repair")
                else:
                    repaired = self.json_repairer.character_level_repair(json_str)
                    raw_plan = json.loads(repaired)
                    print("✅ JSON parsed successfully after character-level repair")
                
             
                if isinstance(raw_plan, list) and len(raw_plan) > expected_days:
                    print(f"🔧 Truncating plan from {len(raw_plan)} days to {expected_days} days")
                    raw_plan = raw_plan[:expected_days]
               
                    for i, day in enumerate(raw_plan):
                        if isinstance(day, dict):
                            day['day'] = i + 1
                
                if validate_parsed_plan(raw_plan, expected_days):
                    return raw_plan
                else:
                    print("⚠️ Parsed plan failed validation")
                    continue
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing attempt {attempt + 1} failed: {e}")
                print(f"Error at line {getattr(e, 'lineno', 'unknown')}, column {getattr(e, 'colno', 'unknown')}")
                if attempt < 4:
                    continue
        
        print("❌ All JSON parsing attempts failed")
        return None