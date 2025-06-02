import requests
from app.config import settings

class GeoDBClient:
    """Client for GeoDB API services"""
    
    def __init__(self):
        self.api_key = settings.rapidapi_key
        self.base_url = "https://wft-geo-db.p.rapidapi.com/v1/geo"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "wft-geo-db.p.rapidapi.com"
        }
    
    def get_nearby_cities(self, lat: float, lng: float, radius: int) -> list[str]:
        """Get nearby cities using RapidAPI GeoDB"""
        if not self.api_key:
            print(" No RAPIDAPI_KEY found, skipping nearby cities")
            return []
        
        formatted_coords = f"{lat:.4f}{lng:+.4f}" 
        
        url = f"{self.base_url}/locations/{formatted_coords}/nearbyCities"
        params = {"radius": radius, "limit": 10, "minPopulation": 1000}
        
        try:
            print(f"Calling GeoDB API with coordinates: {formatted_coords}, radius: {radius}km")
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    cities = [c["city"] for c in data["data"]]
                    print(f"Found {len(cities)} nearby cities:", cities)
                    return cities
                else:
                    print("GeoDB API returned no cities")
                    return []
            elif response.status_code == 400:
                print(f"GeoDB API error 400 - Bad request. Trying alternative format...")
               
                return self._get_nearby_cities_fallback(lat, lng, radius)
            elif response.status_code == 429:
                print("GeoDB API rate limit exceeded")
                return []
            else:
                print(f"GeoDB API returned status {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            print(f"Error calling GeoDB API: {e}")
            return []
    
    def _get_nearby_cities_fallback(self, lat: float, lng: float, radius: int) -> list[str]:
        """Fallback method for getting nearby cities"""
        try:
         
            url = f"{self.base_url}/cities"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "limit": 5,
                "minPopulation": 1000
            }
            
            print(f"Trying fallback GeoDB API call...")
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    cities = [c["city"] for c in data["data"]]
                    print(f"🌆 Fallback found {len(cities)} cities:", cities)
                    return cities
            
            print("Fallback GeoDB API also failed")
            return []
            
        except Exception as e:
            print(f"Fallback GeoDB API error: {e}")
            return []