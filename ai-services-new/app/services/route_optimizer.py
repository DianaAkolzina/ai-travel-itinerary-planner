from app.utils.geography import calculate_distance_km

class RouteOptimizer:
    """Service for optimizing travel routes"""
    
    def optimize_route(self, start_coords: tuple, days: list) -> list:
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