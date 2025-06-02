import requests

def test_ollama_model():
    url = "http://localhost:11434/api/generate"

    main_location = {"city": "Berlin", "country": "Germany"}
    location_info = {"coordinates": {"lat": 52.52, "lng": 13.405}}
    nearby_city_names = ["Potsdam", "Leipzig", "Dresden"]
    travel_dates = ["2025-06-15", "2025-06-16", "2025-06-17"]
    group_size = 2
    budget_level = "moderate"
    accommodation_type = "hotel"
    interests = ["museums", "historic sites", "local cuisine"]
    weather_info = """Weather Forecast:
- 2025-06-15: Sunny, 25°C
- 2025-06-16: Cloudy, 22°C
- 2025-06-17: Rainy, 19°C"""

    prompt = f"""
You are an expert travel planner. Create a detailed day-by-day itinerary for a trip with the following requirements:

LOCATION DETAILS:
- Main destination: {main_location['city']}, {main_location['country']}
- Coordinates: {location_info['coordinates']['lat']}, {location_info['coordinates']['lng']}
- Search radius: 5km
- Nearby cities to consider: {', '.join(nearby_city_names)}
- Each destination should be unique 

TRAVEL DETAILS:
- Travel dates: {', '.join(travel_dates)}
- Duration: {len(travel_dates)} days
- Group size: {group_size} people
- Budget level: {budget_level}
- Accommodation preference: {accommodation_type}

INTERESTS AND PREFERENCES:
- Primary interests: {', '.join(interests)}

{weather_info}

REQUIREMENTS:
1. Create a detailed day-by-day plan for each date
2. Include specific places to visit with approximate coordinates
3. Consider travel time between locations
4. Include meal recommendations
5. Account for weather conditions in activity selection
6. Provide practical information like opening hours and ticket prices
7. Optimize routes to minimize travel distance
8. Include a mix of must-see attractions and hidden gems

FORMAT YOUR RESPONSE AS A VALID JSON with this exact structure and be careful with the commas separators:
{{
  "plan": [
    {{
      "day": 1,
      "date": "{travel_dates[0]}",
      "formatted_date": "June 15, 2025",
      "town": "City Name",
      "place": "Main attraction/area for the day",
      "activities": [
        "Morning: Visit specific location (opening hours, estimated cost)",
        "Lunch: Restaurant recommendation with cuisine type",
        "Afternoon: Another activity with details",
        "Evening: Dinner and evening activity"
      ],
      "lat": 52.5200,
      "lng": 13.4050,
      "distance_from_start": 0.0,
      "estimated_cost": "€50-80 per person",
      "weather_note": "Perfect weather for outdoor activities"
    }}
  ],
  "summary": {{
    "total_estimated_cost": "€200-400 per person",
    "best_season": "Spring/Summer",
    "recommended_duration": "{len(travel_dates)} days",
    "difficulty_level": "Easy/Moderate/Challenging",
    "transportation_tips": "Best ways to get around",
    "cultural_notes": "Important cultural information"
  }}
}}

Ensure all coordinates are within the specified radius and activities match the stated interests. Be specific with place names, addresses where possible, and practical details.
"""

    payload = {
        "model": "llama3",  
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1500
        }
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print("✅ Response from LLM:\n")
        print(result.get("response", "No response text found"))

    except Exception as e:
        print(f"❌ LLM test failed: {e}")

if __name__ == "__main__":
    test_ollama_model()
