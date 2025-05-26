from fastapi import APIRouter, HTTPException, Depends
from app.models.requests import ItineraryRequest
from app.services.itinerary_service import ItineraryService

router = APIRouter()

def get_itinerary_service() -> ItineraryService:
    """Dependency to get itinerary service instance"""
    return ItineraryService()

@router.post("/generate-itinerary")
async def generate_itinerary(
    request: ItineraryRequest,
    service: ItineraryService = Depends(get_itinerary_service)
):
    """Generate travel itinerary based on user preferences"""
    print(f"🗕️ Received Request: destination='{request.destination}' travel_dates={request.travel_dates} preferences={request.preferences} radius={request.radius}")
    
    try:
        result = await service.generate_itinerary(request)
        return result
    except ValueError as e:
        print(f"❌ Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")