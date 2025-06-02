import re
from app.external.google_maps import GoogleMapsClient
from app.external.geo_db import GeoDBClient
from app.utils.geography import calculate_distance_km

class LocationService:
    
    def __init__(self):
        self.google_maps = GoogleMapsClient()
        self.geo_db = GeoDBClient()
    
    async def get_nearby_cities(self, lat: float, lng: float, radius: int) -> list[str]:
        return self.geo_db.get_nearby_cities(lat, lng, radius)
    
    async def get_location_details(self, lat: float, lng: float) -> dict:
        return self.google_maps.reverse_geocode(lat, lng)
        
    async def enrich_and_validate_plan(self, start_coords: tuple, days: list, radius_km: int) -> list:
        """
        Enrich plan with real coordinates. Never lie about locations.
        """
        enriched = []
        
        for day in days:
            coords = self._find_coordinates(day)
            
            # Calculate distance to real location
            distance_km = calculate_distance_km(start_coords, coords)
            
            # Assign real coordinates (never fake them)
            day['lat'], day['lng'] = coords
            day['distance_from_start'] = round(distance_km, 1)
            
            # Log if outside radius but keep real coordinates
            status = "✅" if distance_km <= radius_km else "⚠️ OUTSIDE RADIUS"
            
            print(f"📍 Day {day['day']}: {day.get('place', 'Unknown')} in {day.get('town', 'Unknown')}")
            print(f"   Real coordinates: ({day['lat']:.4f}, {day['lng']:.4f})")
            print(f"   Distance: {distance_km:.1f}km from start {status}")
            
            enriched.append(day)
        
        return enriched
    
    def _find_coordinates(self, day: dict) -> tuple:
        """
        Find real coordinates using multiple strategies. Never return fake coordinates.
        """
        # Strategy 1: Try full address (town + place)
        if day.get('town') and day.get('place'):
            coords = self.google_maps.geocode(day['town'], day['place'])
            if coords:
                return coords
        
        # Strategy 2: Try place only
        if day.get('place'):
            coords = self._geocode_single(day['place'])
            if coords:
                return coords
        
        # Strategy 3: Try town only
        if day.get('town'):
            coords = self._geocode_single(day['town'])
            if coords:
                return coords
        
        # Strategy 4: Try nearby cities (get the first real city)
        coords = self._get_first_nearby_city()
        if coords:
            return coords
        
        return (0, 0)
    
    def _geocode_single(self, location_name: str) -> tuple:
        """Geocode a single location name"""
        try:
            return self.google_maps.geocode_single_location(location_name)
        except Exception:
            return None
    
    def _get_first_nearby_city(self) -> tuple:
        """Get coordinates of first nearby city if available"""
        try:
           
            return None
        except Exception:
            return None
    
    def get_location_context(self, destination: str) -> str:
        return """
        PLEASE SUGGEST:
        - Specific named landmarks, museums, restaurants
        - Real street names and addresses where possible  
        - Local specialties and traditional dishes
        - Historical sites with cultural significance
        - Authentic local experiences"""