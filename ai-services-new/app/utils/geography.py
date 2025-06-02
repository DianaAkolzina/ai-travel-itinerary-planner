import math

# -----------------------------------------------------------------------------------------
# Haversine Formula - Explained
#
# This function calculates the great-circle distance between two points on a sphere
# (Earth) using the Haversine formula.
#
# Inputs:
#   coord1: tuple of (latitude, longitude) in degrees for point 1
#   coord2: tuple of (latitude, longitude) in degrees for point 2
#
# Output:
#   Distance in kilometers between the two coordinates along the Earth's surface
#
# Formula Derivation:
# -------------------
# Let:
#   φ1, λ1 = latitude and longitude of point 1 (in radians)
#   φ2, λ2 = latitude and longitude of point 2 (in radians)
#   Δφ = φ2 - φ1
#   Δλ = λ2 - λ1
#
# The Haversine formula is:
#
#   a = sin²(Δφ / 2) + cos(φ1) * cos(φ2) * sin²(Δλ / 2)
#   c = 2 * arcsin(√a)
#   d = R * c
#
# Where:
#   - a is the square of half the chord length between the points
#   - c is the angular distance in radians
#   - R is Earth's radius (~6371 km)
#
# This formula avoids floating-point precision issues and works well for small and large distances.
# Does not exchange for the google api distances which
# are provided through google api in the itinerary service 
# -----------------------------------------------------------------------------------------


def calculate_distance_km(coord1, coord2):
    
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return c * 6371  
