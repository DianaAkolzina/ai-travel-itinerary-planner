import re
import requests
import json
import os
import random
import math
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def create_prompt(req, nearby):
    """Create enhanced prompt for LLM"""

    location_context = get_location_context(req.destination)
    
    prompt = f"""You are a local travel expert. Plan a detailed {req.days}-day trip near coordinates {req.destination} (STRICTLY within {req.radius} km radius).

LOCATION CONTEXT:
{location_context}

TRAVELER PREFERENCES:
- Interested in: {', '.join(req.preferences.interests)}
- Trip duration: {req.days} days
- Maximum travel radius: {req.radius} km

REQUIREMENTS:
1. Suggest REAL, SPECIFIC places with actual names (not generic like "Local Museum" or "Main Square")
2. Include famous landmarks, specific restaurants, actual street names, real attraction names
3. For each place, mention WHY it's worth visiting and what makes it special
4. All locations must be within {req.radius} km of the coordinates
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

def get_location_context(destination):
    """Get geographical and cultural context for the location"""

    match = re.search(r"Lat:\s*([0-9\.-]+),\s*Lng:\s*([0-9\.-]+)", destination)
    if not match:
        return "Location coordinates not available."
    
    lat, lng = map(float, match.groups())
    
    context = []
    
    if 49.0 <= lat <= 55.0 and 14.0 <= lng <= 24.0:
        context.append("Region: Central/Eastern Poland")
        context.append("Cultural context: Rich medieval history, traditional Polish architecture, religious sites")
        context.append("Typical attractions: Gothic churches, market squares, folk museums, traditional restaurants")
    elif 45.0 <= lat <= 49.0 and 16.0 <= lng <= 23.0:
        context.append("Region: Central Europe (Hungary/Slovakia area)")
        context.append("Cultural context: Habsburg heritage, thermal baths, medieval castles")
        context.append("Typical attractions: Historic castles, thermal spas, wine regions, traditional markets")
    elif 47.0 <= lat <= 51.0 and 2.0 <= lng <= 8.0:
        context.append("Region: France/Western Europe")
        context.append("Cultural context: French culture, cuisine, historic châteaux")
        context.append("Typical attractions: Historic châteaux, vineyards, cathedrals, museums")
    elif 50.0 <= lat <= 55.0 and 3.0 <= lng <= 15.0:
        context.append("Region: Germany/Central Europe")
        context.append("Cultural context: Germanic heritage, medieval towns, beer culture")
        context.append("Typical attractions: Medieval old towns, breweries, castles, Christmas markets")
    elif 41.0 <= lat <= 47.0 and 12.0 <= lng <= 19.0:
        context.append("Region: Italy/Southern Europe")
        context.append("Cultural context: Roman heritage, Renaissance art, Mediterranean cuisine")
        context.append("Typical attractions: Ancient ruins, Renaissance palaces, piazzas, authentic trattorias")
    else:
        context.append(f"Coordinates: {lat:.4f}, {lng:.4f}")
        context.append("Cultural context: Local regional attractions and landmarks")
        context.append("Focus on: Local history, traditional architecture, regional cuisine")
    
    context.append("\nPLEASE SUGGEST:")
    context.append("- Specific named landmarks, churches, museums, restaurants")
    context.append("- Real street names and addresses where possible")
    context.append("- Local specialties and traditional dishes to try")
    context.append("- Historical sites with actual historical significance")
    context.append("- Authentic local experiences, not tourist traps")
    
    return "\n".join(context)

def reverse_geocode_location(lat, lng):
    """Get location information from coordinates using Google Geocoding API"""
    if not GOOGLE_API_KEY:
        return None
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": GOOGLE_API_KEY,
        "result_type": "locality|administrative_area_level_1|country"
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data['status'] == 'OK' and data['results']:
               
                result = data['results'][0]
                components = result.get('address_components', [])
                
                location_info = {}
                for comp in components:
                    types = comp.get('types', [])
                    if 'locality' in types:
                        location_info['city'] = comp['long_name']
                    elif 'administrative_area_level_1' in types:
                        location_info['region'] = comp['long_name']
                    elif 'country' in types:
                        location_info['country'] = comp['long_name']
                
                return location_info
    except Exception as e:
        print(f"⚠️ Reverse geocoding error: {e}")
    
    return None

def get_nearby_cities(lat, lng, radius):
    """Get nearby cities using RapidAPI GeoDB"""
    if not RAPIDAPI_KEY:
        print("⚠️ No RAPIDAPI_KEY found, skipping nearby cities")
        return []
    
    formatted_coords = f"{lat:.4f}{lng:+.4f}"  
    
    url = f"https://wft-geo-db.p.rapidapi.com/v1/geo/locations/{formatted_coords}/nearbyCities"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "wft-geo-db.p.rapidapi.com"
    }
    params = {"radius": radius, "limit": 10, "minPopulation": 1000}
    
    try:
        print(f"🌐 Calling GeoDB API with coordinates: {formatted_coords}, radius: {radius}km")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                cities = [c["city"] for c in data["data"]]
                print(f"🌆 Found {len(cities)} nearby cities:", cities)
                return cities
            else:
                print("⚠️ GeoDB API returned no cities")
                return []
        elif response.status_code == 400:
            print(f"⚠️ GeoDB API error 400 - Bad request. Trying alternative format...")
          
            return get_nearby_cities_fallback(lat, lng, radius)
        elif response.status_code == 429:
            print("⚠️ GeoDB API rate limit exceeded")
            return []
        else:
            print(f"⚠️ GeoDB API returned status {response.status_code}: {response.text}")
            return []
            
    except Exception as e:
        print(f"⚠️ Error calling GeoDB API: {e}")
        return []

def get_nearby_cities_fallback(lat, lng, radius):
    """Fallback method for getting nearby cities"""
    try:
      
        url = f"https://wft-geo-db.p.rapidapi.com/v1/geo/cities"
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "wft-geo-db.p.rapidapi.com"
        }
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "limit": 5,
            "minPopulation": 1000
        }
        
        print(f"🔄 Trying fallback GeoDB API call...")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                cities = [c["city"] for c in data["data"]]
                print(f"🌆 Fallback found {len(cities)} cities:", cities)
                return cities
        
        print("⚠️ Fallback GeoDB API also failed")
        return []
        
    except Exception as e:
        print(f"⚠️ Fallback GeoDB API error: {e}")
        return []

def parse_llm_response(response_json, req):
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
    
    for attempt in range(5):
        try:
            if attempt == 0:
            
                raw_plan = json.loads(json_str)
                print("✅ JSON parsed successfully on first attempt")
            elif attempt == 1:
           
                repaired = smart_comma_repair(json_str)
                raw_plan = json.loads(repaired)
                print("✅ JSON parsed successfully after smart comma repair")
            elif attempt == 2:
              
                repaired = repair_json_basic(json_str)
                raw_plan = json.loads(repaired)
                print("✅ JSON parsed successfully after basic repair")
            elif attempt == 3:
             
                repaired = repair_json_aggressive(json_str)
                raw_plan = json.loads(repaired)
                print("✅ JSON parsed successfully after aggressive repair")
            else:
               
                repaired = character_level_repair(json_str)
                raw_plan = json.loads(repaired)
                print("✅ JSON parsed successfully after character-level repair")
            
            if validate_parsed_plan(raw_plan, req.days):
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

def smart_comma_repair(json_str):
    """Smart comma repair focusing on common LLM JSON issues"""
    print("🔧 Applying smart comma repair...")
    
    lines = json_str.split('\n')
    repaired_lines = []
    
    for i, line in enumerate(lines):
        current_line = line.rstrip()
        
        next_line = None
        for j in range(i + 1, len(lines)):
            if lines[j].strip():
                next_line = lines[j].strip()
                break
        
        if next_line:
          
            needs_comma = False
            
            if (current_line.endswith('"') and next_line.startswith('"') and 
                ':' in next_line and not current_line.endswith(',"')):
                needs_comma = True
            
            if (current_line.endswith(']') and next_line.startswith('"') and 
                ':' in next_line and not current_line.endswith('],')):
                needs_comma = True
            
            if (current_line.endswith('}') and next_line.startswith('{') and 
                not current_line.endswith('},')):
                needs_comma = True
            
            if (current_line.endswith('}') and next_line.startswith('"') and 
                ':' in next_line and not current_line.endswith('},')):
                needs_comma = True
            
            if needs_comma:
                current_line += ','
                print(f"🔧 Added comma to line {i + 1}")
        
        repaired_lines.append(current_line)
    
    repaired_json = '\n'.join(repaired_lines)
    print("🔧 Smart comma repair completed")
    return repaired_json

def character_level_repair(json_str):
    """Character-by-character JSON repair for stubborn cases"""
    print("🔧 Applying character-level repair...")
    
    try:
        json.loads(json_str)
        return json_str  
    except json.JSONDecodeError as e:
        error_pos = getattr(e, 'pos', 0)
        print(f"🔧 JSON error at position {error_pos}")
        
        start = max(0, error_pos - 50)
        end = min(len(json_str), error_pos + 50)
        context = json_str[start:end]
        print(f"🔧 Error context: ...{context}...")
        
        repaired = json_str
        
        if error_pos < len(json_str):
            json_str[error_pos]
            
            for i in range(error_pos - 1, -1, -1):
                char = json_str[i]
                if char in '"]}':
                    
                    next_meaningful = None
                    for j in range(error_pos, len(json_str)):
                        if json_str[j] not in ' \t\n\r':
                            next_meaningful = json_str[j]
                            break
                    
                    if next_meaningful in '"{':
                        
                        repaired = json_str[:i+1] + ',' + json_str[i+1:]
                        print(f"🔧 Inserted comma at position {i+1}")
                        break
                elif not char.isspace():
                    break
        
        return repaired

def optimize_travel_route(start_coords, days):
    """Optimize the order of days to minimize total travel distance"""
    if len(days) <= 1:
        return days
    
    remaining = days.copy()
    current_location = start_coords
    optimized_route = []
    
    print(f"🚀 Starting route optimization from {start_coords}")
    
    while remaining:
      
        closest_day = min(remaining, key=lambda day: 
            calculate_distance_km(current_location, (day['lat'], day['lng'])))
        
        travel_distance = calculate_distance_km(current_location, (closest_day['lat'], closest_day['lng']))
        
        closest_day['travel_distance_km'] = round(travel_distance, 1) if optimized_route else 0
        
        optimized_route.append(closest_day)
        remaining.remove(closest_day)
        current_location = (closest_day['lat'], closest_day['lng'])
        
        print(f"📍 Added Day {len(optimized_route)}: {closest_day['place']} "
              f"[{closest_day['distance_from_start']}km from USER coordinates, "
              f"{closest_day['travel_distance_km']}km travel from previous location]")
    
    total_travel_distance = 0
    for i, day in enumerate(optimized_route):
        day['day'] = i + 1
        day['route'] = [{'lat': d['lat'], 'lng': d['lng']} for d in optimized_route[:i+1]]
        
        if i > 0:
            total_travel_distance += day['travel_distance_km']
    
    print(f"🎯 Route optimized! Total travel distance: {total_travel_distance:.1f}km")
    
    return optimized_route


def generate_fallback_plan(req, lat, lng, nearby):
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
    for i in range(req.days):
        place = fallback_places[i % len(fallback_places)]
        plan.append({
            "day": i + 1,
            "town": nearby[i % len(nearby)] if nearby else place["town"],
            "place": place["place"],
            "activities": place["activities"]
        })
    
    return {
        "plan": enrich_and_validate_plan((lat, lng), plan, req.radius),
        "nearby_cities": nearby,
        "user_coordinates": {"lat": lat, "lng": lng},
        "search_radius": req.radius
    }

def enrich_and_validate_plan(start_coords, days, radius_km):
    """Add coordinates, validate radius, and optimize route order"""
    enriched = []
    
    for day in days:
        
        coords = geocode_location(day['town'], day['place'])
        
        if not coords:
           
            coords = generate_random_coordinates_in_radius(start_coords[0], start_coords[1], radius_km)
        
        distance_km = calculate_distance_km(start_coords, coords)
        if distance_km > radius_km:
            coords = generate_random_coordinates_in_radius(start_coords[0], start_coords[1], radius_km)
            distance_km = calculate_distance_km(start_coords, coords)
        
        day['lat'], day['lng'] = coords
        day['distance_from_start'] = round(distance_km, 1)
        enriched.append(day)
        
        print(f"✅ Day {day['day']}: {day['place']} -> ({day['lat']:.4f}, {day['lng']:.4f}) "
              f"[{distance_km:.1f}km from USER coordinates {start_coords[0]:.4f}, {start_coords[1]:.4f}]")
    
    if len(enriched) <= 1:
        return enriched
    
    print("🗺️ Optimizing travel route...")
    optimized = optimize_travel_route(start_coords, enriched)
    
    return optimized

def repair_json_aggressive(json_str):
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
    
def repair_json_basic(json_str):
    """Basic JSON repair for common issues"""
    print("🔧 Applying basic JSON repairs...")
    
    json_str = re.sub(r'("\s*)\n(\s*")', r'\1,\n\2', json_str)
    json_str = re.sub(r'(\]\s*)\n(\s*")', r'\1,\n\2', json_str)
    json_str = re.sub(r'(\}\s*)\n(\s*")', r'\1,\n\2', json_str)
    
    json_str = re.sub(r'(\})\s*\n\s*(\{)', r'\1,\n  \2', json_str)
    
  
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    return json_str


def geocode_location(town, place):
    """Try to geocode a location"""
    if not GOOGLE_API_KEY:
        return None
        
    query = f"{place}, {town}".strip(", ")
    if not query:
        return None
        
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": query, "key": GOOGLE_API_KEY}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data['status'] == 'OK' and data['results']:
                loc = data['results'][0]['geometry']['location']
                return loc['lat'], loc['lng']
    except Exception as e:
        print(f"⚠️ Geocoding error for {query}: {e}")
    
    return None



def validate_parsed_plan(plan, expected_days):
    """Validate that the parsed plan is reasonable"""
    if not isinstance(plan, list):
        print("⚠️ Plan is not a list")
        return False
    
    if len(plan) == 0:
        print("⚠️ Plan is empty")
        return False
    
    if len(plan) > expected_days * 2:  
        print(f"⚠️ Too many days in plan: {len(plan)} (expected around {expected_days})")
        return False
  
    for i, day in enumerate(plan):
        if not isinstance(day, dict):
            print(f"⚠️ Day {i+1} is not a dictionary")
            return False
        
        required_fields = ['town', 'place', 'activities']
        for field in required_fields:
            if field not in day:
                print(f"⚠️ Day {i+1} missing field: {field}")
                return False
        
        if not isinstance(day['activities'], list):
            print(f"⚠️ Day {i+1} activities is not a list")
            return False
    
    print(f"✅ Plan validation passed: {len(plan)} days")
    return True


def repair_json_aggressive(json_str):
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
    
def calculate_distance_km(coord1, coord2):
    """Calculate distance using Haversine formula"""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return c * 6371  



def generate_random_coordinates_in_radius(center_lat, center_lng, radius_km):
    """Generate random coordinates within radius"""
    radius_deg = radius_km / 111.0  
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius_deg)
    
    lat_offset = distance * math.cos(angle)
    lng_offset = distance * math.sin(angle)
    
    return center_lat + lat_offset, center_lng + lng_offset