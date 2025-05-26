import requests
from app.config import settings
from typing import Optional, Tuple

class GoogleMapsClient:
    """Client for Google Maps API services"""
    
    def __init__(self):
        self.api_key = settings.google_maps_api_key
        self.base_url = "https://maps.googleapis.com/maps/api"
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[dict]:
        """Get location information from coordinates using Google Geocoding API"""
        if not self.api_key:
            return None
        
        url = f"{self.base_url}/geocode/json"
        params = {
            "latlng": f"{lat},{lng}",
            "key": self.api_key,
            "result_type": "locality|administrative_area_level_1|country"
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data['status'] == 'OK' and data['results']:
                    # Extract location components
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
    
    def geocode(self, town: str, place: str) -> Optional[Tuple[float, float]]:
        """Try to geocode a location"""
        if not self.api_key:
            return None
            
        query = f"{place}, {town}".strip(", ")
        if not query:
            return None
            
        url = f"{self.base_url}/geocode/json"
        params = {"address": query, "key": self.api_key}
        
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