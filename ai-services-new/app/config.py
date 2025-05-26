from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    google_maps_api_key: Optional[str] = None
    rapidapi_key: Optional[str] = None
    openweather_api_key: Optional[str] = None
    llm_endpoint: str = "http://localhost:11434/api/generate"
    llm_model: str = "llama3"
    
    class Config:
        env_file = ".env"

settings = Settings()