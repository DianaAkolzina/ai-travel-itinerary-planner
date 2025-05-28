from pydantic import BaseModel
from typing import List
from datetime import date

class Preferences(BaseModel):
    interests: List[str]

class ItineraryRequest(BaseModel):
    destination: str
    travel_dates: List[date]  
    preferences: Preferences
    radius: int