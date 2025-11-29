"""Mock implementation of hotel-related tools for the Trip Planner."""
import random
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from loguru import logger

from app.schemas import (
    Address, 
    GeoPoint, 
    HotelOption, 
    AccommodationType,
    SearchHotelsInput,
)
from app.framework.adk_runtime import ToolDefinition, ToolResult

# Mock data for hotels
MOCK_HOTELS = {
    "bangalore": [
        {
            "id": "hotel_1",
            "name": "Taj West End",
            "type": "hotel",
            "address": {
                "street": "23, Race Course Road, High Grounds",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560001",
                "country": "India",
                "formatted": "23, Race Course Road, High Grounds, Bengaluru, Karnataka 560001, India",
                "coordinates": {"lat": 12.9716, "lng": 77.5946}
            },
            "rating": 4.7,
            "review_count": 4280,
            "price_per_night": 15000,
            "currency": "INR",
            "amenities": [
                "free_wifi", "pool", "spa", "fitness_center", "restaurant", 
                "bar", "room_service", "concierge", "business_center", "parking"
            ]
        },
        {
            "id": "hotel_2",
            "name": "ITC Gardenia",
            "type": "hotel",
            "address": {
                "street": "Residency Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560025",
                "country": "India",
                "formatted": "Residency Road, Bengaluru, Karnataka 560025, India",
                "coordinates": {"lat": 12.9716, "lng": 77.5946}
            },
            "rating": 4.6,
            "review_count": 3850,
            "price_per_night": 12000,
            "currency": "INR",
            "amenities": [
                "free_wifi", "pool", "spa", "fitness_center", "restaurant", 
                "bar", "room_service", "concierge", "business_center", "parking"
            ]
        },
        {
            "id": "hotel_3",
            "name": "The Oberoi Bengaluru",
            "type": "hotel",
            "address": {
                "street": "37-39, MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560001",
                "country": "India",
                "formatted": "37-39, MG Road, Bengaluru, Karnataka 560001, India",
                "coordinates": {"lat": 12.9754, "lng": 77.6109}
            },
            "rating": 4.8,
            "review_count": 2760,
            "price_per_night": 18000,
            "currency": "INR",
            "amenities": [
                "free_wifi", "pool", "spa", "fitness_center", "restaurant", 
                "bar", "room_service", "concierge", "business_center", "parking"
            ]
        }
    ]
}

# Mock review data
MOCK_REVIEWS = {
    "hotel_1": [
        {
            "id": "review_1",
            "author": "Traveler123",
            "rating": 5,
            "title": "Exceptional Service",
            "text": "The staff went above and beyond to make our stay memorable.",
            "date": "2023-10-15",
            "trip_type": "couple"
        },
        {
            "id": "review_2",
            "author": "BusinessTraveler",
            "rating": 4,
            "title": "Great for business stays",
            "text": "Excellent business facilities and convenient location.",
            "date": "2023-09-28",
            "trip_type": "business"
        }
    ],
    "hotel_2": [
        {
            "id": "review_3",
            "author": "FamilyTraveler",
            "rating": 5,
            "title": "Perfect family getaway",
            "text": "The kids loved the pool and the staff was very accommodating.",
            "date": "2023-11-05",
            "trip_type": "family"
        }
    ]
}

def get_hotels_by_location(location: str) -> List[Dict]:
    """Get mock hotels for a location."""
    location_lower = location.lower()
    
    # Try to match the location
    for key in MOCK_HOTELS:
        if key in location_lower:
            return MOCK_HOTELS[key]
    
    # Default to Bangalore if no match
    return MOCK_HOTELS["bangalore"]

async def search_hotels(payload: Dict, context: Dict) -> ToolResult:
    """Mock implementation of the search_hotels tool."""
    try:
        # Parse and validate input
        input_data = SearchHotelsInput(**payload)
        
        # Log the request
        logger.info(
            f"Searching for hotels in {input_data.location}",
            correlation_id=context.get("correlation_id"),
            caller_agent=context.get("caller_agent"),
            tool_name="search_hotels",
            check_in=input_data.check_in,
            check_out=input_data.check_out,
            guests=input_data.guests,
            min_rating=input_data.min_rating,
            max_price=input_data.max_price,
        )
        
        # Get hotels for the location
        hotels = get_hotels_by_location(input_data.location)
        
        # Apply filters
        filtered_hotels = []
        
        for hotel in hotels:
            # Filter by rating
            if hotel["rating"] < input_data.min_rating:
                continue
                
            # Filter by price if specified
            if input_data.max_price is not None and hotel["price_per_night"] > input_data.max_price:
                continue
                
            # Filter by amenities if specified
            if input_data.amenities:
                if not all(amenity in hotel["amenities"] for amenity in input_data.amenities):
                    continue
            
            # Calculate total price for the stay
            nights = (input_data.check_out - input_data.check_in).days
            total_price = hotel["price_per_night"] * nights
            
            # Add to results
            filtered_hotels.append({
                **hotel,
                "total_price": total_price,
                "nights": nights,
            })
        
        # Sort by rating (highest first) and then by price (lowest first)
        filtered_hotels.sort(key=lambda x: (-x["rating"], x["price_per_night"]))
        
        # Limit results
        results = filtered_hotels[:10]
        
        # Return the results
        return ToolResult(
            success=True,
            data={
                "results": results,
                "count": len(results),
                "query": input_data.dict(),
            }
        )
        
    except Exception as e:
        logger.error(
            f"Error in search_hotels: {str(e)}",
            correlation_id=context.get("correlation_id"),
            caller_agent=context.get("caller_agent"),
            tool_name="search_hotels",
            error=str(e),
            exc_info=True,
        )
        return ToolResult(
            success=False,
            error=f"Failed to search hotels: {str(e)}",
        )

# Tool definitions
TOOLS = [
    ToolDefinition(
        name="hotels.search",
        description="Search for hotels in a specific location with various filters",
        input_schema=SearchHotelsInput.schema(),
        output_schema={
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "address": {"type": "object"},
                            "rating": {"type": "number"},
                            "review_count": {"type": "integer"},
                            "price_per_night": {"type": "number"},
                            "currency": {"type": "string"},
                            "amenities": {"type": "array", "items": {"type": "string"}},
                            "total_price": {"type": "number"},
                            "nights": {"type": "integer"}
                        },
                    },
                },
                "count": {"type": "integer"},
                "query": {"type": "object"},
            },
        },
        handler=search_hotels,
    )
]
