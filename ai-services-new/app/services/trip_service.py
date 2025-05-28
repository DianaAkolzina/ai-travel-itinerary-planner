# ai-services-new/app/services/trip_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.database_models import Trip, DailyPlan, Destination, DateRange, TripPreferences, TripMetadata
import logging

logger = logging.getLogger(__name__)


class TripService:
    async def create_trip(self, user_id: str, trip_data: Dict[str, Any]) -> Trip:
        """Create a new trip"""
        
        # Parse coordinates from destination if needed
        coordinates = {"lat": 0.0, "lng": 0.0}
        if trip_data["destination"].startswith('Lat:'):
            try:
                lat_str = trip_data["destination"].split('Lat: ')[1].split(',')[0]
                lng_str = trip_data["destination"].split('Lng: ')[1]
                coordinates = {"lat": float(lat_str), "lng": float(lng_str)}
            except (IndexError, ValueError):
                logger.warning(f"Could not parse coordinates from: {trip_data['destination']}")
        
        # Calculate total days
        start_date = datetime.fromisoformat(trip_data["start_date"])
        end_date = datetime.fromisoformat(trip_data["end_date"])
        total_days = (end_date - start_date).days + 1
        
        trip = Trip(
            user_id=user_id,
            title=trip_data["title"],
            destination=Destination(
                name=trip_data["destination"],
                coordinates=coordinates
            ),
            date_range=DateRange(
                start_date=start_date,
                end_date=end_date
            ),
            preferences=TripPreferences(
                interests=[interest.value if hasattr(interest, 'value') else interest for interest in trip_data["interests"]],
                radius=trip_data.get("radius", 50),
                budget={
                    "amount": trip_data.get("budget"),
                    "currency": trip_data.get("budget_currency", "USD")
                } if trip_data.get("budget") else None
            ),
            metadata=TripMetadata(total_days=total_days)
        )
        
        await trip.insert()
        logger.info(f"Trip created: {trip.title} for user {user_id}")
        return trip
    
    async def get_trip(self, trip_id: str, user_id: str) -> Optional[Trip]:
        """Get a specific trip"""
        try:
            trip = await Trip.get(trip_id)
            if trip and trip.user_id == user_id:
                return trip
            return None
        except Exception as e:
            logger.error(f"Error getting trip {trip_id}: {str(e)}")
            return None
    
    async def get_user_trips(
        self, 
        user_id: str, 
        page: int = 1, 
        limit: int = 10, 
        status: Optional[str] = None
    ) -> List[Trip]:
        """Get user's trips with pagination"""
        
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        skip = (page - 1) * limit
        
        trips = await Trip.find(query).skip(skip).limit(limit).sort("-created_at").to_list()
        return trips
    
    async def update_trip(self, trip_id: str, user_id: str, update_data: Dict[str, Any]) -> Optional[Trip]:
        """Update a trip"""
        trip = await self.get_trip(trip_id, user_id)
        if not trip:
            return None
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(trip, field):
                setattr(trip, field, value)
        
        trip.updated_at = datetime.now()
        await trip.save()
        
        logger.info(f"Trip updated: {trip_id}")
        return trip
    
    async def delete_trip(self, trip_id: str, user_id: str) -> bool:
        """Delete a trip and its daily plans"""
        trip = await self.get_trip(trip_id, user_id)
        if not trip:
            return False
        
        # Delete associated daily plans
        await DailyPlan.find(DailyPlan.trip_id == trip_id).delete()
        
        # Delete trip
        await trip.delete()
        
        logger.info(f"Trip deleted: {trip_id}")
        return True
    
    async def create_daily_plans(self, trip_id: str, plans_data: List[Dict[str, Any]]) -> List[DailyPlan]:
        """Create daily plans for a trip"""
        
        # Delete existing plans
        await DailyPlan.find(DailyPlan.trip_id == trip_id).delete()
        
        daily_plans = []
        for plan_data in plans_data:
            daily_plan = DailyPlan(
                trip_id=trip_id,
                day=plan_data["day"],
                date=datetime.fromisoformat(plan_data["date"]),
                formatted_date=plan_data.get("formatted_date", plan_data["date"]),
                location=plan_data["location"],
                activities=plan_data.get("activities", []),
                weather=plan_data.get("weather"),
                notes=plan_data.get("notes")
            )
            await daily_plan.insert()
            daily_plans.append(daily_plan)
        
        logger.info(f"Created {len(daily_plans)} daily plans for trip {trip_id}")
        return daily_plans
    
    async def get_daily_plans(self, trip_id: str) -> List[DailyPlan]:
        """Get daily plans for a trip"""
        plans = await DailyPlan.find(DailyPlan.trip_id == trip_id).sort("day").to_list()
        return plans
    
    async def update_trip_status(self, trip_id: str, status: str) -> bool:
        """Update trip status"""
        try:
            trip = await Trip.get(trip_id)
            if trip:
                trip.status = status
                trip.updated_at = datetime.now()
                
                if status == "generated":
                    trip.metadata.last_generated = datetime.now()
                    trip.metadata.generation_count += 1
                
                await trip.save()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating trip status {trip_id}: {str(e)}")
            return False