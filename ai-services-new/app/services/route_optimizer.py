from app.utils.geography import calculate_distance_km

class RouteOptimizer:
    """
    Service for optimizing the order of daily travel plans based on geographic proximity.

    This class provides functionality to reorder a list of daily travel destinations 
    such that the total distance traveled over the course of the trip is minimized. 
    It uses a greedy algorithm similar to the Nearest Neighbor heuristic from 
    the Traveling Salesperson Problem (TSP).

    Method:
    --------
    optimize_route(start_coords: tuple, days: list) -> list
        - Input:
            * start_coords: a tuple of the user's starting coordinates (latitude, longitude).
            * days: a list of dictionaries where each dictionary represents a day's plan,
              including at least 'lat' and 'lng' keys for the day's main location.

        - Process:
            1. Begins at the user's starting coordinates.
            2. Iteratively selects the "nearest" unvisited location (by great-circle distance)
               using the Haversine formula.
            3. Updates the day's 'travel_distance_km' with the distance from the previous location.
            4. Appends this day's plan to the `optimized_route` list and removes it from the pool.
            5. Repeats the process until all days are ordered.
            6. Annotates each day with:
                - `day`: the day number in the optimized sequence.
                - `route`: a cumulative route history with coordinates visited so far.
            7. Prints helpful debug output showing selection progress and final stats.

        - Output:
            * Returns a new list of day plans in the optimized order with added metadata:
                - 'day': integer representing the day's new position.
                - 'route': list of dicts representing the route path so far.
                - 'travel_distance_km': float distance from previous day's location.

    Assumptions:
    ------------
    - All entries in `days` contain valid 'lat' and 'lng' keys.
    - `calculate_distance_km()` is a utility function (using Haversine formula) 
      available in the current scope.

    Limitations:
    ------------
    - This is a greedy approximation and may not produce the globally optimal route
      for large or complex datasets, but is fast and effective for small trips (3–10 days).
    - Does not account for time windows, traffic, or transportation modes.
    """
    
    def optimize_route(self, start_coords: tuple, days: list) -> list:
        """Optimize the order of days to minimize total travel distance"""
        if len(days) <= 1:
            return days
      
        remaining = days.copy()
        current_location = start_coords
        optimized_route = []
        
        print(f"Starting route optimization from {start_coords}")
        
  
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
        
        print(f" Route optimized! Total travel distance: {total_travel_distance:.1f}km")
        
        return optimized_route