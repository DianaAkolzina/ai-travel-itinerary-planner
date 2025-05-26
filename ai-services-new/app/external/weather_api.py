import requests
from app.config import settings

class WeatherAPIClient:
    """Client for weather API services"""
    
    def __init__(self):
        self.openweather_api_key = settings.openweather_api_key
    
    def get_forecast(self, lat: float, lng: float) -> dict:
        """Get weather forecast for the location"""
        if not self.openweather_api_key:
            print("⚠️ No OPENWEATHER_API_KEY found, trying free Open-Meteo API...")
            return self._get_weather_forecast_free(lat, lng)
        
        try:
       
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                "lat": lat,
                "lon": lng,
                "appid": self.openweather_api_key,
                "units": "metric",  
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
                return self._get_weather_forecast_free(lat, lng)
                
        except Exception as e:
            print(f"⚠️ Error getting weather data: {e}")
            return self._get_weather_forecast_free(lat, lng)

    def _get_weather_forecast_free(self, lat: float, lng: float) -> dict:
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