from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def root():
    return {"message": "AI Travel Planner API is running!", "status": "healthy"}

@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "ai-travel-planner"}