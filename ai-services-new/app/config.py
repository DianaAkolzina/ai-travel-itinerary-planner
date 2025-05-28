from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    google_maps_api_key: str
    rapidapi_key: str
    openweather_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"

settings = Settings()

GOOGLE_MAPS_API_KEY = settings.google_maps_api_key
RAPIDAPI_KEY = settings.rapidapi_key
OPENWEATHER_API_KEY = settings.openweather_api_key
