from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
import re
import requests
import os
from dotenv import load_dotenv
from helpers import create_prompt, reverse_geocode_location, get_nearby_cities
from helpers import  enrich_and_validate_plan, generate_fallback_plan
from helpers import parse_llm_response
load_dotenv()


GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
app = FastAPI(title="AI Travel Planner", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Preferences(BaseModel):
    interests: List[str]

class ItineraryRequest(BaseModel):
    destination: str
    days: int
    preferences: Preferences
    radius: int

@app.get("/")
def root():
    return {"message": "AI Travel Planner API is running!", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ai-travel-planner"}

@app.post("/generate-itinerary")
def generate_itinerary(req: ItineraryRequest):
    print(f"🗕️ Received Request: destination='{req.destination}' days={req.days} preferences={req.preferences} radius={req.radius}")

    if not req.destination:
        raise HTTPException(status_code=400, detail="Destination must be provided.")

    match = re.search(r"Lat:\s*([0-9\.-]+),\s*Lng:\s*([0-9\.-]+)", req.destination)
    if not match:
        print("❌ Invalid coordinates format")
        return {"plan": []}

    lat, lng = map(float, match.groups())
    print(f"🌍 Coordinates: {lat}, {lng}")

    nearby = get_nearby_cities(lat, lng, req.radius)
   
    location_details = reverse_geocode_location(lat, lng)
    if location_details:
        print(f"📍 Location details: {location_details}")
        nearby.extend([location_details.get('city', ''), location_details.get('region', '')])
        nearby = [city for city in nearby if city] 
    
    print("🏙️ Enhanced location context:", nearby)

    prompt = create_prompt(req, nearby)
    print("🧠 Sending prompt to LLM...")

    try:
        llm_response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }, timeout=30)
        
        if llm_response.status_code != 200:
            print(f"❌ LLM request failed with status {llm_response.status_code}")
            return generate_fallback_plan(req, lat, lng, nearby)
            
        response_json = llm_response.json()
        print("📨 Raw LLM Response received")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ LLM connection failed: {e}")
        return generate_fallback_plan(req, lat, lng, nearby)

    raw_plan = parse_llm_response(response_json, req)
    if not raw_plan:
        return generate_fallback_plan(req, lat, lng, nearby)

    enriched = enrich_and_validate_plan((lat, lng), raw_plan, req.radius)
    print("✅ Final Enriched Plan:", enriched)
    
    weather_data = get_weather_forecast(lat, lng)

    return {
        "plan": enriched,
        "nearby_cities": nearby,
        "user_coordinates": {"lat": lat, "lng": lng},
        "search_radius": req.radius,
        "weather": weather_data
    }


def fix_missing_commas(json_str):
    """Specifically fix missing comma issues"""
    print("🔧 Fixing missing commas...")
    
    lines = json_str.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        fixed_lines.append(line)
        
        if i < len(lines) - 1:
            current_line = lines[i].strip()
            next_line = lines[i + 1].strip()
            
            if (current_line.endswith('"') or current_line.endswith(']') or current_line.endswith('}')) and next_line.startswith('"'):
                if not current_line.endswith(','):
                    fixed_lines[-1] = line + ','
            
            if current_line.endswith('}') and next_line.startswith('{'):
                if not current_line.endswith(','):
                    fixed_lines[-1] = line + ','
    
    return '\n'.join(fixed_lines)

def get_weather_forecast(lat, lng):
    """Get weather forecast for the location using OpenWeatherMap API"""
    if not OPENWEATHER_API_KEY:
        print("⚠️ No OPENWEATHER_API_KEY found, trying free Open-Meteo API...")
        return get_weather_forecast_free(lat, lng)
    
    try:

        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "lat": lat,
            "lon": lng,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",  # Celsius
            "cnt": 16 
        }
        
        print(f"🌤️ Getting weather forecast for coordinates: {lat}, {lng}")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            
            weather_info = {
                "location": data.get("city", {}).get("name", "Unknown"),
                "country": data.get("city", {}).get("country", ""),
                "current": None,
                "forecast": []
            }
            
         
            if data.get("list") and len(data["list"]) > 0:
                current = data["list"][0]
                weather_info["current"] = {
                    "temperature": round(current["main"]["temp"]),
                    "feels_like": round(current["main"]["feels_like"]),
                    "humidity": current["main"]["humidity"],
                    "description": current["weather"][0]["description"].title(),
                    "icon": current["weather"][0]["icon"],
                    "wind_speed": round(current["wind"]["speed"] * 3.6, 1)
                }
            
            processed_dates = set()
            for item in data.get("list", []):
                date = item["dt_txt"].split(" ")[0] 
                if date not in processed_dates and len(weather_info["forecast"]) < 5:
                    processed_dates.add(date)
                    weather_info["forecast"].append({
                        "date": date,
                        "temperature_max": round(item["main"]["temp_max"]),
                        "temperature_min": round(item["main"]["temp_min"]),
                        "description": item["weather"][0]["description"].title(),
                        "icon": item["weather"][0]["icon"],
                        "humidity": item["main"]["humidity"]
                    })
            
            print(f"🌤️ Weather data retrieved for {weather_info['location']}")
            return weather_info
            
        else:
            print(f"⚠️ OpenWeatherMap API error: {response.status_code}")
            return get_weather_forecast_free(lat, lng)
            
    except Exception as e:
        print(f"⚠️ Error getting weather data: {e}")
        return get_weather_forecast_free(lat, lng)

def get_weather_forecast_free(lat, lng):
    """Get weather forecast using free Open-Meteo API (no API key required)"""
    try:
        
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lng,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean",
            "timezone": "auto",
            "forecast_days": 7
        }
        
        print(f"🌤️ Getting free weather forecast for coordinates: {lat}, {lng}")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            weather_codes = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
                55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
                81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
                96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail"
            }
            
            weather_info = {
                "location": "Selected Location",
                "country": "",
                "current": None,
                "forecast": []
            }
            
            if data.get("current"):
                current = data["current"]
                weather_code = current.get("weather_code", 0)
                weather_info["current"] = {
                    "temperature": round(current.get("temperature_2m", 0)),
                    "feels_like": round(current.get("temperature_2m", 0)),  
                    "humidity": current.get("relative_humidity_2m", 0),
                    "description": weather_codes.get(weather_code, "Unknown"),
                    "icon": f"{weather_code:02d}d",
                    "wind_speed": round(current.get("wind_speed_10m", 0), 1)
                }
            
            if data.get("daily"):
                daily = data["daily"]
                for i in range(min(5, len(daily.get("time", [])))):
                    weather_code = daily["weather_code"][i] if i < len(daily.get("weather_code", [])) else 0
                    weather_info["forecast"].append({
                        "date": daily["time"][i],
                        "temperature_max": round(daily["temperature_2m_max"][i]),
                        "temperature_min": round(daily["temperature_2m_min"][i]),
                        "description": weather_codes.get(weather_code, "Unknown"),
                        "icon": f"{weather_code:02d}d",
                        "humidity": round(daily["relative_humidity_2m_mean"][i]) if i < len(daily.get("relative_humidity_2m_mean", [])) else 0
                    })
            
            print(f"🌤️ Free weather data retrieved successfully")
            return weather_info
            
    except Exception as e:
        print(f"⚠️ Error getting free weather data: {e}")
        return {
            "location": "Unknown",
            "country": "",
            "current": {
                "temperature": 20,
                "feels_like": 20,
                "humidity": 50,
                "description": "Weather data unavailable",
                "icon": "01d",
                "wind_speed": 0
            },
            "forecast": []
        }
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






if __name__ == "__main__":
    print("🚀 Starting AI Travel Planner API...")
    print(f"🔑 Google API Key: {'✅ Set' if GOOGLE_API_KEY else '❌ Missing'}")
    print(f"🔑 RapidAPI Key: {'✅ Set' if RAPIDAPI_KEY else '❌ Missing'}")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")