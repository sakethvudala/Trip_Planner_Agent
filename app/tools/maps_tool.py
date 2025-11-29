"""Mock implementation of maps-related tools for the Trip Planner."""
import random
from typing import Dict, List, Optional

from loguru import logger

from app.schemas import GeoPoint, POICategory, SearchPlacesInput, GetDistanceMatrixInput
from app.framework.adk_runtime import ToolDefinition, ToolResult

# Mock data for places
MOCK_PLACES = {
    "bangalore": [
        {
            "id": "place_1",
            "name": "Bangalore Palace",
            "category": "historical",
            "address": "Palace Road, Vasanth Nagar, Bengaluru, Karnataka 560052",
            "coordinates": {"lat": 12.9984, "lng": 77.5930},
            "rating": 4.2,
            "rating_count": 12500,
            "description": "A stunning royal palace with Tudor-style architecture and beautiful gardens.",
            "popular_times": {
                "Monday": [10, 15, 25, 30, 45, 60, 55, 50, 40, 30, 25, 20],
                "Tuesday": [10, 15, 20, 25, 35, 50, 60, 65, 55, 45, 35, 25],
                "Wednesday": [10, 15, 20, 30, 40, 55, 65, 70, 60, 50, 40, 30],
                "Thursday": [10, 15, 25, 35, 45, 60, 70, 75, 65, 55, 45, 35],
                "Friday": [15, 20, 30, 40, 50, 65, 75, 80, 70, 60, 50, 40],
                "Saturday": [20, 30, 45, 60, 75, 85, 90, 95, 90, 80, 65, 50],
                "Sunday": [25, 35, 50, 65, 80, 90, 95, 100, 95, 85, 70, 55],
            },
            "opening_hours": {
                "Monday": [{"open": "10:00", "close": "17:30"}],
                "Tuesday": [{"open": "10:00", "close": "17:30"}],
                "Wednesday": [{"open": "10:00", "close": "17:30"}],
                "Thursday": [{"open": "10:00", "close": "17:30"}],
                "Friday": [{"open": "10:00", "close": "17:30"}],
                "Saturday": [{"open": "10:00", "close": "17:30"}],
                "Sunday": [{"open": "10:00", "close": "17:30"}],
            },
            "price_level": 2,
            "url": "https://example.com/bangalore-palace",
            "photos": [
                "https://example.com/photos/bangalore-palace-1.jpg",
                "https://example.com/photos/bangalore-palace-2.jpg",
            ],
        },
        # Add more mock places as needed
    ],
    "mumbai": [
        {
            "id": "place_2",
            "name": "Gateway of India",
            "category": "historical",
            "address": "Apollo Bandar, Colaba, Mumbai, Maharashtra 400001",
            "coordinates": {"lat": 18.9220, "lng": 72.8347},
            "rating": 4.5,
            "rating_count": 85000,
            "description": "An iconic monument and a popular tourist attraction in Mumbai.",
        },
    ],
    "delhi": [
        {
            "id": "place_3",
            "name": "India Gate",
            "category": "historical",
            "address": "Rajpath, India Gate, New Delhi, Delhi 110001",
            "coordinates": {"lat": 28.6129, "lng": 77.2295},
            "rating": 4.6,
            "rating_count": 150000,
            "description": "A war memorial dedicated to the 82,000 soldiers of the Indian Army who died in World War I.",
        },
    ],
}

# Mock distance matrix data
MOCK_DISTANCES = {
    # Format: (origin_lat, origin_lng) -> (dest_lat, dest_lng) -> (distance_meters, duration_seconds)
    (12.9716, 77.5946): {
        (12.9984, 77.5930): (3500, 600),  # MG Road to Bangalore Palace
    },
}

# Mock travel times in seconds between points
MOCK_TRAVEL_TIMES = {
    # Format: (origin_lat, origin_lng) -> (dest_lat, dest_lng) -> (mode) -> seconds
    (12.9716, 77.5946): {
        (12.9984, 77.5930): {
            "driving": 600,
            "walking": 1800,
            "bicycling": 1200,
            "transit": 900,
        },
    },
}


def get_places_by_location(location: str) -> List[Dict]:
    """Get mock places for a location."""
    location_lower = location.lower()
    
    # Try to match the location
    for key in MOCK_PLACES:
        if key in location_lower:
            return MOCK_PLACES[key]
    
    # Default to Bangalore if no match
    return MOCK_PLACES["bangalore"]


async def search_places(payload: Dict, context: Dict) -> ToolResult:
    """Mock implementation of the search_places tool.
    
    Args:
        payload: The input parameters for the tool
        context: Context information including correlation_id and caller_agent
        
    Returns:
        ToolResult containing the search results
    """
    try:
        # Parse and validate input
        input_data = SearchPlacesInput(**payload)
        
        # Log the request
        logger.info(
            f"Searching for places with query: {input_data.query}",
            correlation_id=context.get("correlation_id"),
            caller_agent=context.get("caller_agent"),
            tool_name="search_places",
            location=input_data.location,
            category=input_data.category,
            limit=input_data.limit,
        )
        
        # Get places for the location
        places = get_places_by_location(input_data.location or input_data.query)
        
        # Filter by category if specified
        if input_data.category:
            places = [p for p in places if p["category"] == input_data.category.value]
        
        # Apply limit
        results = places[:input_data.limit]
        
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
            f"Error in search_places: {str(e)}",
            correlation_id=context.get("correlation_id"),
            caller_agent=context.get("caller_agent"),
            tool_name="search_places",
            error=str(e),
            exc_info=True,
        )
        return ToolResult(
            success=False,
            error=f"Failed to search places: {str(e)}",
        )


async def get_distance_matrix(payload: Dict, context: Dict) -> ToolResult:
    """Mock implementation of the distance_matrix tool.
    
    Args:
        payload: The input parameters for the tool
        context: Context information including correlation_id and caller_agent
        
    Returns:
        ToolResult containing the distance matrix
    """
    try:
        # Parse and validate input
        input_data = GetDistanceMatrixInput(**payload)
        
        # Log the request
        logger.info(
            "Calculating distance matrix",
            correlation_id=context.get("correlation_id"),
            caller_agent=context.get("caller_agent"),
            tool_name="distance_matrix",
            origin_count=len(input_data.origins),
            destination_count=len(input_data.destinations),
            mode=input_data.mode,
        )
        
        # Initialize results
        rows = []
        
        # For each origin
        for origin in input_data.origins:
            origin_key = (origin.lat, origin.lng)
            row = {"elements": []}
            
            # For each destination
            for dest in input_data.destinations:
                dest_key = (dest.lat, dest.lng)
                
                # Try to get from mock data
                distance_m = None
                duration_s = None
                
                # Check exact match first
                if (origin_key in MOCK_DISTANCES and 
                    dest_key in MOCK_DISTANCES[origin_key]):
                    distance_m, duration_s = MOCK_DISTANCES[origin_key][dest_key]
                # Check reverse direction
                elif (dest_key in MOCK_DISTANCES and 
                      origin_key in MOCK_DISTANCES[dest_key]):
                    distance_m, duration_s = MOCK_DISTANCES[dest_key][origin_key]
                # Try to get travel time from mock data
                elif (origin_key in MOCK_TRAVEL_TIMES and 
                      dest_key in MOCK_TRAVEL_TIMES[origin_key] and 
                      input_data.mode.value in MOCK_TRAVEL_TIMES[origin_key][dest_key]):
                    duration_s = MOCK_TRAVEL_TIMES[origin_key][dest_key][input_data.mode.value]
                    # Generate a reasonable distance based on mode and time
                    speed_kmh = {
                        "walking": 5,
                        "bicycling": 15,
                        "driving": 30,
                        "transit": 20,
                        "flight": 800,
                        "train": 80,
                        "bus": 50,
                        "taxi": 30,
                        "ride_sharing": 30,
                    }.get(input_data.mode.value, 30)
                    
                    distance_km = (speed_kmh * duration_s) / 3600  # km = km/h * s / (s/h)
                    distance_m = int(distance_km * 1000)
                
                # If no mock data, generate random but reasonable values
                if distance_m is None or duration_s is None:
                    # Generate random distance between 500m and 20km
                    distance_m = random.randint(500, 20000)
                    # Generate duration based on mode and distance
                    base_speed_mps = {
                        "walking": 1.4,      # ~5 km/h
                        "bicycling": 4.0,     # ~14 km/h
                        "driving": 13.9,      # ~50 km/h
                        "transit": 8.3,       # ~30 km/h
                        "flight": 200,        # ~720 km/h
                        "train": 27.8,        # ~100 km/h
                        "bus": 13.9,          # ~50 km/h
                        "taxi": 13.9,         # ~50 km/h
                        "ride_sharing": 13.9, # ~50 km/h
                    }.get(input_data.mode.value, 13.9)  # Default to driving speed
                    
                    # Add some random factor (0.7x to 1.3x)
                    speed_factor = 0.7 + 0.6 * random.random()
                    duration_s = int((distance_m / 1000) / (base_speed_mps * speed_factor / 1000) * 1.2)  # Add 20% buffer
                
                # Add to row
                row["elements"].append({
                    "distance": {"value": distance_m, "text": f"{distance_m/1000:.1f} km"},
                    "duration": {"value": duration_s, "text": f"{duration_s//60} mins"},
                    "status": "OK",
                })
            
            rows.append(row)
        
        # Return the results
        return ToolResult(
            success=True,
            data={
                "origin_addresses": [f"Origin {i+1}" for i in range(len(input_data.origins))],
                "destination_addresses": [f"Destination {i+1}" for i in range(len(input_data.destinations))],
                "rows": rows,
            }
        )
        
    except Exception as e:
        logger.error(
            f"Error in get_distance_matrix: {str(e)}",
            correlation_id=context.get("correlation_id"),
            caller_agent=context.get("caller_agent"),
            tool_name="distance_matrix",
            error=str(e),
            exc_info=True,
        )
        return ToolResult(
            success=False,
            error=f"Failed to calculate distance matrix: {str(e)}",
        )


# Tool definitions
TOOLS = [
    ToolDefinition(
        name="maps.search_places",
        description="Search for points of interest (POIs) in a specific location",
        input_schema=SearchPlacesInput.schema(),
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
                            "category": {"type": "string"},
                            "address": {"type": "string"},
                            "coordinates": {
                                "type": "object",
                                "properties": {
                                    "lat": {"type": "number"},
                                    "lng": {"type": "number"},
                                },
                            },
                            "rating": {"type": "number"},
                            "rating_count": {"type": "integer"},
                            "description": {"type": "string"},
                        },
                    },
                },
                "count": {"type": "integer"},
                "query": {"type": "object"},
            },
        },
        handler=search_places,
    ),
    ToolDefinition(
        name="maps.distance_matrix",
        description="Calculate distances and travel times between multiple origins and destinations",
        input_schema=GetDistanceMatrixInput.schema(),
        output_schema={
            "type": "object",
            "properties": {
                "origin_addresses": {"type": "array", "items": {"type": "string"}},
                "destination_addresses": {"type": "array", "items": {"type": "string"}},
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "elements": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "distance": {
                                            "type": "object",
                                            "properties": {
                                                "value": {"type": "number"},
                                                "text": {"type": "string"},
                                            },
                                        },
                                        "duration": {
                                            "type": "object",
                                            "properties": {
                                                "value": {"type": "number"},
                                                "text": {"type": "string"},
                                            },
                                        },
                                        "status": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        handler=get_distance_matrix,
    ),
]
