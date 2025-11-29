"""Location Agent for the Trip Planner system.

This agent is responsible for:
- Finding points of interest (POIs) based on user preferences
- Recommending attractions, restaurants, and activities
- Providing location-specific information and details
"""
from typing import Dict, List, Optional, Any

from app.agents.base_agent import BaseAgent
from app.agents.base import AgentCard, AgentMessage, AgentContext
from app.schemas import LocationPreference, POICategory, POI
from app.framework.adk_runtime import ToolResult

class LocationAgent(BaseAgent):
    """Agent responsible for location-based recommendations."""
    
    def __init__(
        self,
        llm_client,
        adk_runtime,
        logger=None,
    ):
        """Initialize the Location Agent."""
        card = AgentCard(
            name="LocationAgent",
            description="Finds and recommends points of interest based on user preferences",
            tools=[],  # Tools will be registered in the base class
            llm_model="gemini-1.5-flash",
        )
        
        super().__init__(card, llm_client, adk_runtime, logger)
    
    def get_tools(self) -> list:
        """Get the list of tools available to this agent."""
        return [
            {
                "name": "maps.search_places",
                "description": "Search for places (attractions, restaurants, etc.) in a specific location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g., 'museums', 'italian restaurants', 'hiking trails')"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location to search in (city, country, or address)"
                        },
                        "radius": {
                            "type": "number",
                            "description": "Search radius in meters (default: 5000)",
                            "default": 5000
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)",
                            "default": 10
                        },
                        "min_rating": {
                            "type": "number",
                            "description": "Minimum rating (1-5) to filter results",
                            "minimum": 1,
                            "maximum": 5
                        },
                        "open_now": {
                            "type": "boolean",
                            "description": "Whether to only return places that are currently open"
                        },
                        "price_level": {
                            "type": "integer",
                            "description": "Price level (1-4, where 1 is least expensive and 4 is most expensive)",
                            "minimum": 1,
                            "maximum": 4
                        },
                        "type": {
                            "type": "string",
                            "description": "Type of place (e.g., 'restaurant', 'museum', 'park')",
                            "enum": [
                                "accounting", "airport", "amusement_park", "aquarium", "art_gallery",
                                "atm", "bakery", "bank", "bar", "beauty_salon", "bicycle_store",
                                "book_store", "bowling_alley", "bus_station", "cafe", "campground",
                                "car_dealer", "car_rental", "car_repair", "car_wash", "casino",
                                "cemetery", "church", "city_hall", "clothing_store", "convenience_store",
                                "courthouse", "dentist", "department_store", "doctor", "electrician",
                                "electronics_store", "embassy", "fire_station", "florist", "funeral_home",
                                "furniture_store", "gas_station", "gym", "hair_care", "hardware_store",
                                "hindu_temple", "home_goods_store", "hospital", "insurance_agency",
                                "jewelry_store", "laundry", "lawyer", "library", "light_rail_station",
                                "liquor_store", "local_government_office", "locksmith", "lodging",
                                "meal_delivery", "meal_takeaway", "mosque", "movie_rental",
                                "movie_theater", "moving_company", "museum", "night_club", "painter",
                                "park", "parking", "pet_store", "pharmacy", "physiotherapist", "plumber",
                                "police", "post_office", "primary_school", "real_estate_agency",
                                "restaurant", "roofing_contractor", "rv_park", "school", "secondary_school",
                                "shoe_store", "shopping_mall", "spa", "stadium", "storage", "store",
                                "subway_station", "supermarket", "synagogue", "taxi_stand", "tourist_attraction",
                                "train_station", "transit_station", "travel_agency", "university",
                                "veterinary_care", "zoo"
                            ]
                        }
                    },
                    "required": ["query", "location"]
                }
            },
            {
                "name": "maps.distance_matrix",
                "description": "Calculate travel distance and time between multiple origins and destinations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origins": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of origin addresses or place IDs"
                        },
                        "destinations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of destination addresses or place IDs"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["driving", "walking", "bicycling", "transit"],
                            "default": "driving",
                            "description": "Travel mode"
                        },
                        "avoid": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["tolls", "highways", "ferries", "indoor"]},
                            "description": "Features to avoid during routing"
                        },
                        "units": {
                            "type": "string",
                            "enum": ["metric", "imperial"],
                            "default": "metric",
                            "description": "Unit system for displaying distances"
                        }
                    },
                    "required": ["origins", "destinations"]
                }
            },
            {
                "name": "reviews.get",
                "description": "Get reviews for a specific place (hotel, restaurant, etc.) with sentiment analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "place_id": {
                            "type": "string",
                            "description": "The ID of the place to get reviews for"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of reviews to return (default: 5)",
                            "default": 5
                        }
                    },
                    "required": ["place_id"]
                }
            }
        ]
    
    async def _process_message(
        self, 
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Process an incoming message and return a response."""
        try:
            action = message.content.get("action") if isinstance(message.content, dict) else None
            
            if action == "get_recommendations":
                return await self._get_location_recommendations(message, context)
            elif action == "get_poi_details":
                return await self._get_poi_details(message, context)
            else:
                return self.create_error_response(
                    ValueError(f"Unknown action: {action}"),
                    recipient=message.sender,
                )
        except Exception as e:
            self.logger.error(
                f"Error in LocationAgent: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"message_content": message.content},
            )
    
    async def _get_location_recommendations(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Get location recommendations based on trip request."""
        try:
            # Extract trip request from message
            trip_request = message.content.get("trip_request") if isinstance(message.content, dict) else {}
            if not trip_request:
                raise ValueError("No trip request provided")
            
            location_prefs = trip_request.get("location", {})
            base_city = location_prefs.get("base_city")
            if not base_city:
                raise ValueError("No base city provided in trip request")
            
            # Get user preferences for activities and interests
            interests = location_prefs.get("interests", [])
            activities = location_prefs.get("activities", [])
            
            # Generate search queries based on interests and activities
            search_queries = self._generate_search_queries(interests, activities)
            
            # Search for places based on the generated queries
            all_places = []
            for query in search_queries:
                result = await self.execute_tool(
                    tool_name="maps.search_places",
                    tool_args={
                        "query": query,
                        "location": base_city,
                        "max_results": 5,  # Limit to 5 results per query
                    },
                    context=context,
                )
                
                if result.success and "results" in result.data:
                    all_places.extend(result.data["results"])
            
            # Remove duplicates by place_id
            unique_places = {}
            for place in all_places:
                place_id = place.get("place_id")
                if place_id and place_id not in unique_places:
                    unique_places[place_id] = place
            
            # Convert to list of POI objects
            recommendations = []
            for place in unique_places.values():
                try:
                    poi = self._create_poi_from_place(place)
                    recommendations.append(poi.dict())
                except Exception as e:
                    self.logger.warning(
                        f"Error creating POI from place: {str(e)}",
                        place=place,
                        error=str(e),
                    )
            
            # Sort by rating (highest first)
            recommendations.sort(key=lambda x: x.get("rating", 0), reverse=True)
            
            # Limit to top recommendations
            max_recommendations = 15
            if len(recommendations) > max_recommendations:
                recommendations = recommendations[:max_recommendations]
            
            return self.create_response(
                content={
                    "status": "success",
                    "recommendations": recommendations,
                    "count": len(recommendations),
                },
                recipient=message.sender,
            )
        except Exception as e:
            self.logger.error(
                f"Error getting location recommendations: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "get_location_recommendations"},
            )
    
    async def _get_poi_details(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Get detailed information about a specific POI."""
        try:
            # Extract place_id from message
            place_id = None
            if isinstance(message.content, dict):
                place_id = message.content.get("place_id")
            
            if not place_id:
                raise ValueError("No place_id provided")
            
            # Get place details
            place_result = await self.execute_tool(
                tool_name="maps.search_places",
                tool_args={
                    "place_id": place_id,
                    "fields": ["all"],
                },
                context=context,
            )
            
            if not place_result.success or "result" not in place_result.data:
                raise ValueError(f"Failed to get details for place_id: {place_id}")
            
            place = place_result.data["result"]
            poi = self._create_poi_from_place(place)
            
            # Get reviews if available
            reviews_result = await self.execute_tool(
                tool_name="reviews.get",
                tool_args={
                    "place_id": place_id,
                    "limit": 3,  # Get top 3 reviews
                },
                context=context,
            )
            
            if reviews_result.success and "reviews" in reviews_result.data:
                poi.reviews = reviews_result.data["reviews"]
            
            return self.create_response(
                content={
                    "status": "success",
                    "poi": poi.dict(),
                },
                recipient=message.sender,
            )
        except Exception as e:
            self.logger.error(
                f"Error getting POI details: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "get_poi_details"},
            )
    
    def _generate_search_queries(
        self,
        interests: List[str],
        activities: List[str],
    ) -> List[str]:
        """Generate search queries based on user interests and activities."""
        queries = []
        
        # Add queries based on interests
        interest_queries = [
            f"top {interest} in area" for interest in interests
        ]
        
        # Add queries based on activities
        activity_queries = []
        for activity in activities:
            if activity in ["sightseeing", "landmarks"]:
                activity_queries.extend([
                    "top tourist attractions",
                    "famous landmarks",
                    "must-see places",
                ])
            elif activity == "dining":
                activity_queries.extend([
                    "best restaurants",
                    "local cuisine",
                    "highly rated cafes",
                ])
            elif activity == "shopping":
                activity_queries.extend([
                    "shopping malls",
                    "local markets",
                    "boutique shops",
                ])
            elif activity == "nightlife":
                activity_queries.extend([
                    "best bars",
                    "nightclubs",
                    "live music venues",
                ])
            elif activity == "outdoors":
                activity_queries.extend([
                    "parks and nature reserves",
                    "hiking trails",
                    "scenic viewpoints",
                ])
            elif activity == "culture":
                activity_queries.extend([
                    "museums",
                    "art galleries",
                    "historical sites",
                ])
        
        # Combine and deduplicate queries
        all_queries = list(set(interest_queries + activity_queries))
        return all_queries
    
    def _create_poi_from_place(self, place: Dict) -> POI:
        """Create a POI object from a Google Places API result."""
        # Map Google Place types to our POI categories
        place_types = place.get("types", [])
        category = self._map_place_types_to_category(place_types)
        
        # Get the primary photo URL if available
        photo_url = None
        if "photos" in place and place["photos"]:
            # In a real implementation, you would generate a photo URL using the photo reference
            # photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={place['photos'][0]['photo_reference']}&key=YOUR_API_KEY"
            pass
        
        # Create the POI object
        poi = POI(
            id=place.get("place_id"),
            name=place.get("name"),
            category=category,
            address=place.get("formatted_address", ""),
            location={
                "lat": place["geometry"]["location"]["lat"],
                "lng": place["geometry"]["location"]["lng"],
            } if "geometry" in place and "location" in place["geometry"] else None,
            rating=place.get("rating"),
            user_ratings_total=place.get("user_ratings_total"),
            price_level=place.get("price_level"),
            photo_url=photo_url,
            opening_hours=place.get("opening_hours", {}).get("weekday_text"),
            is_open_now=place.get("opening_hours", {}).get("open_now"),
            website=place.get("website"),
            phone=place.get("formatted_phone_number"),
            description=place.get("editorial_summary", {}).get("overview"),
            tags=place.get("types", []),
        )
        
        return poi

    def _map_place_types_to_category(self, place_types: List[str]) -> POICategory:
        """Map Google Place types to our POI categories."""
        if not place_types:
            return POICategory.OTHER
            
        place_types = set(place_types)
        
        # Check for specific categories
        if any(t in place_types for t in ["restaurant", "food", "cafe", "bar", "bakery"]):
            return POICategory.RESTAURANT
            
        if any(t in place_types for t in ["hotel", "lodging", "accommodation"]):
            return POICategory.HOTEL
            
        if any(t in place_types for t in ["museum", "art_gallery", "aquarium", "zoo"]):
            return POICategory.MUSEUM
            
        if any(t in place_types for t in ["park", "amusement_park", "tourist_attraction"]):
            return POICategory.PARK
            
        if any(t in place_types for t in ["shopping_mall", "clothing_store", "store"]):
            return POICategory.SHOPPING
            
        return POICategory.OTHER
        
    def handle_maps_search_places(self, query: str, location: str, radius: int = 5000, 
                                max_results: int = 10, min_rating: float = None, 
                                open_now: bool = None, price_level: int = None, 
                                type: str = None) -> Dict[str, Any]:
        """Handle the maps.search_places tool call.
        
        Args:
            query: Search query (e.g., 'museums', 'italian restaurants', 'hiking trails')
            location: Location to search in (city, country, or address)
            radius: Search radius in meters (default: 5000)
            max_results: Maximum number of results to return (default: 10)
            min_rating: Minimum rating (1-5) to filter results
            open_now: Whether to only return places that are currently open
            price_level: Price level (1-4, where 1 is least expensive and 4 is most expensive)
            type: Type of place (e.g., 'restaurant', 'museum', 'park')
            
        Returns:
            Dict containing the search results
        """
        try:
            # Call the actual maps API through the ADK runtime
            tool_result = self.adk_runtime.call_tool(
                "maps.search_places",
                {
                    "query": query,
                    "location": location,
                    "radius": radius,
                    "max_results": max_results,
                    "min_rating": min_rating,
                    "open_now": open_now,
                    "price_level": price_level,
                    "type": type
                }
            )
            
            if not tool_result.success:
                self.logger.error(f"Failed to search places: {tool_result.error}")
                return {"success": False, "error": tool_result.error}
                
            # Process and return the results
            return {
                "success": True,
                "results": tool_result.data.get("results", [])
            }
            
        except Exception as e:
            self.logger.exception("Error in handle_maps_search_places")
            return {"success": False, "error": str(e)}


    def handle_maps_distance_matrix(self, origins: List[str], destinations: List[str], 
                                  mode: str = "driving", avoid: List[str] = None, 
                                  units: str = "metric") -> Dict[str, Any]:
        """Handle the maps.distance_matrix tool call."""
        try:
            tool_result = self.adk_runtime.call_tool(
                "maps.distance_matrix",
                {
                    "origins": origins,
                    "destinations": destinations,
                    "mode": mode,
                    "avoid": avoid,
                    "units": units
                }
            )
            
            if not tool_result.success:
                self.logger.error(f"Failed to get distance matrix: {tool_result.error}")
                return {"success": False, "error": tool_result.error}
                
            return {
                "success": True,
                "matrix": tool_result.data.get("matrix", {})
            }
        except Exception as e:
            self.logger.exception("Error in handle_maps_distance_matrix")
            return {"success": False, "error": str(e)}

    def handle_reviews_get(self, place_id: str, limit: int = 5) -> Dict[str, Any]:
        """Handle the reviews.get tool call."""
        try:
            tool_result = self.adk_runtime.call_tool(
                "reviews.get",
                {
                    "place_id": place_id,
                    "limit": limit
                }
            )
            
            if not tool_result.success:
                self.logger.error(f"Failed to get reviews: {tool_result.error}")
                return {"success": False, "error": tool_result.error}
                
            return {
                "success": True,
                "reviews": tool_result.data.get("reviews", [])
            }
        except Exception as e:
            self.logger.exception("Error in handle_reviews_get")
            return {"success": False, "error": str(e)}
