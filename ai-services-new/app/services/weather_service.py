from datetime import date, datetime, timedelta
from typing import List, Optional
from app.external.weather_api import WeatherAPIClient

class WeatherService:
    """Service for handling weather data"""
    
    def __init__(self):
        self.weather_client = WeatherAPIClient()
    
    async def get_forecast_for_dates(self, lat: float, lng: float, travel_dates: List[date]) -> Optional[dict]:
        """Get weather forecast for specific dates"""
        try:
           
            weather_data = self.weather_client.get_forecast(lat, lng)
            
            if not weather_data or not weather_data.get('forecast'):
                print("⚠️ No weather forecast available")
                return None
            
           
            filtered_forecasts = []
            available_dates = set()
            
            for forecast_item in weather_data['forecast']:
                forecast_date_str = forecast_item['date']
                try:
                    
                    forecast_date = datetime.strptime(forecast_date_str, '%Y-%m-%d').date()
                    available_dates.add(forecast_date)
                    
                    if forecast_date in travel_dates:
                        filtered_forecasts.append({
                            **forecast_item,
                            'travel_day': travel_dates.index(forecast_date) + 1
                        })
                except ValueError:
                    continue
            
            missing_dates = [d for d in travel_dates if d not in available_dates]
            
            if missing_dates:
                print(f"⚠️ Weather forecast not available for dates: {missing_dates}")
            
            if filtered_forecasts:
                return {
                    "location": weather_data.get("location", "Unknown"),
                    "country": weather_data.get("country", ""),
                    "current": weather_data.get("current"),
                    "forecast": filtered_forecasts,
                    "missing_dates": [str(d) for d in missing_dates]
                }
            else:
                print("⚠️ No weather forecasts available for any of the requested dates")
                return None
                
        except Exception as e:
            print(f"⚠️ Error getting weather forecast: {e}")
            return None