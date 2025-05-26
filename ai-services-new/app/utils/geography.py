import math
import random

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
