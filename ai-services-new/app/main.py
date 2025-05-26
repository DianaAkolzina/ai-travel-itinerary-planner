from fastapi import FastAPI
from app.api.middleware import setup_middleware
from app.api.routes import health, itinerary
from app.config import settings
import uvicorn

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="AI Travel Planner",
        version="1.0.0",
        description="AI-powered travel itinerary generator"
    )
    
    # Setup middleware (CORS, etc.)
    setup_middleware(app)
    
    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(itinerary.router, tags=["itinerary"])
    
    return app

# Create the app instance - THIS IS WHAT UVICORN LOOKS FOR
app = create_app()

if __name__ == "__main__":
    print("🚀 Starting AI Travel Planner API...")
    print(f"🔑 Google API Key: {'✅ Set' if settings.google_maps_api_key else '❌ Missing'}")
    print(f"🔑 RapidAPI Key: {'✅ Set' if settings.rapidapi_key else '❌ Missing'}")
    print(f"🔑 OpenWeather API Key: {'✅ Set' if settings.openweather_api_key else '❌ Missing'}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )