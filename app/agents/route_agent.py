"""Route Agent for the Trip Planner system.

This agent is responsible for:
- Optimizing travel routes between locations
- Calculating travel times and distances
- Recommending transportation options
- Managing the daily itinerary
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from app.agents.base_agent import BaseAgent
from app.agents.base import AgentCard, AgentMessage, AgentContext
from app.schemas import (
    TripPlan, DayPlan, Stop, TransportationMode, 
    TransportationOption, RouteLeg, Route
)
from app.framework.adk_runtime import ToolResult

class RouteAgent(BaseAgent):
    """Agent responsible for route planning and optimization."""
    
    def __init__(
        self,
        llm_client,
        adk_runtime,
        logger=None,
    ):
        """Initialize the Route Agent."""
        card = AgentCard(
            name="RouteAgent",
            description="Optimizes travel routes and transportation options",
            tools=[],  # Tools will be registered in the base class
            llm_model="gemini-1.5-flash",
        )
        
        super().__init__(card, llm_client, adk_runtime, logger)
        
        # Default transportation preferences
        self.default_transportation = [
            {"mode": "walking", "max_distance_km": 1.5},
            {"mode": "bicycling", "max_distance_km": 5},
            {"mode": "transit", "max_distance_km": 50},
            {"mode": "driving"},  # No max distance for driving
        ]
    
    def get_tools(self) -> list:
        """Get the list of tools available to this agent."""
        return [
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
                        "departure_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Desired time of departure"
                        },
                        "arrival_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Desired time of arrival"
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
                "name": "maps.directions",
                "description": "Get detailed directions between locations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "Origin address or place ID"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination address or place ID"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["driving", "walking", "bicycling", "transit"],
                            "default": "driving",
                            "description": "Travel mode"
                        },
                        "waypoints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of waypoint addresses or place IDs"
                        },
                        "alternatives": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to return multiple route alternatives"
                        },
                        "departure_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Desired time of departure"
                        },
                        "arrival_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Desired time of arrival"
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
                    "required": ["origin", "destination"]
                }
            },
            {
                "name": "maps.elevation",
                "description": "Get elevation data for locations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "locations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "lat": {"type": "number"},
                                    "lng": {"type": "number"}
                                },
                                "required": ["lat", "lng"]
                            },
                            "description": "List of locations to get elevation data for"
                        }
                    },
                    "required": ["locations"]
                }
            },
            {
                "name": "maps.timezone",
                "description": "Get timezone information for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lng": {"type": "number"}
                            },
                            "required": ["lat", "lng"]
                        },
                        "timestamp": {
                            "type": "integer",
                            "description": "Timestamp in seconds since midnight, January 1, 1970 UTC"
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code for the timezone name"
                        }
                    },
                    "required": ["location"]
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
            
            if action == "optimize_itinerary":
                return await self._optimize_itinerary(message, context)
            elif action == "get_directions":
                return await self._get_directions(message, context)
            elif action == "calculate_route":
                return await self._calculate_route(message, context)
            else:
                return self.create_error_response(
                    ValueError(f"Unknown action: {action}"),
                    recipient=message.sender,
                )
        except Exception as e:
            self.logger.error(
                f"Error in RouteAgent: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": action},
            )
    
    async def _optimize_itinerary(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Optimize the daily itinerary with efficient routes and transportation."""
        try:
            # Extract trip plan from message
            trip_plan_data = message.content.get("trip_plan") if isinstance(message.content, dict) else {}
            if not trip_plan_data:
                raise ValueError("No trip plan provided")
            
            # Convert to TripPlan object
            trip_plan = TripPlan(**trip_plan_data)
            
            # Optimize each day's itinerary
            optimized_days = []
            for day_plan in trip_plan.days:
                if not day_plan.stops:
                    optimized_days.append(day_plan)
                    continue
                
                # Optimize the order of stops
                optimized_stops = await self._optimize_stops_order(day_plan.stops, context)
                
                # Add transportation between stops
                transportation = await self._plan_transportation(optimized_stops, context)
                
                # Create optimized day plan
                optimized_day = DayPlan(
                    date=day_plan.date,
                    stops=optimized_stops,
                    transportation=transportation,
                    notes=day_plan.notes,
                )
                
                optimized_days.append(optimized_day)
            
            # Update the trip plan with optimized days
            trip_plan.days = optimized_days
            
            return self.create_response(
                content={
                    "status": "success",
                    "optimized_itinerary": {
                        "days": [day.dict() for day in optimized_days],
                        "summary": self._generate_itinerary_summary(optimized_days),
                    }
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error optimizing itinerary: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "optimize_itinerary"},
            )
    
    async def _get_directions(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Get detailed directions between two or more points."""
        try:
            # Extract parameters
            params = message.content if isinstance(message.content, dict) else {}
            
            # Call the directions API
            result = await self.execute_tool(
                tool_name="maps.directions",
                tool_args={
                    "origin": params.get("origin"),
                    "destination": params.get("destination"),
                    "waypoints": params.get("waypoints", []),
                    "mode": params.get("mode", "driving"),
                    "alternatives": params.get("alternatives", False),
                    "departure_time": params.get("departure_time"),
                    "arrival_time": params.get("arrival_time"),
                    "avoid": params.get("avoid", []),
                    "units": params.get("units", "metric"),
                },
                context=context,
            )
            
            if not result.success:
                raise ValueError(f"Failed to get directions: {result.error}")
            
            return self.create_response(
                content={
                    "status": "success",
                    "routes": result.data.get("routes", []),
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error getting directions: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "get_directions"},
            )
    
    async def _calculate_route(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Calculate a route between multiple points with detailed information."""
        try:
            # Extract parameters
            params = message.content if isinstance(message.content, dict) else {}
            
            # Get the distance matrix for all points
            distance_result = await self.execute_tool(
                tool_name="maps.distance_matrix",
                tool_args={
                    "origins": params.get("waypoints", []),
                    "destinations": params.get("waypoints", []),
                    "mode": params.get("mode", "driving"),
                    "departure_time": params.get("departure_time"),
                    "arrival_time": params.get("arrival_time"),
                    "avoid": params.get("avoid", []),
                    "units": params.get("units", "metric"),
                },
                context=context,
            )
            
            if not distance_result.success:
                raise ValueError(f"Failed to calculate distances: {distance_result.error}")
            
            # Process the distance matrix to create a route
            route = self._create_route_from_distance_matrix(
                waypoints=params.get("waypoints", []),
                distance_matrix=distance_result.data,
                mode=params.get("mode", "driving"),
            )
            
            return self.create_response(
                content={
                    "status": "success",
                    "route": route.dict(),
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error calculating route: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "calculate_route"},
            )
    
    async def _optimize_stops_order(
        self,
        stops: List[Stop],
        context: AgentContext,
    ) -> List[Stop]:
        """Optimize the order of stops to minimize travel time."""
        if len(stops) <= 1:
            return stops
        
        # Get place IDs for distance matrix
        place_ids = [stop.id for stop in stops]
        
        # Get distance matrix for all stops
        result = await self.execute_tool(
            tool_name="maps.distance_matrix",
            tool_args={
                "origins": place_ids,
                "destinations": place_ids,
                "mode": "driving",  # Use driving as the base mode for optimization
            },
            context=context,
        )
        
        if not result.success or "rows" not in result.data:
            self.logger.warning(
                "Failed to get distance matrix, returning original order",
                correlation_id=context.correlation_id,
                error=result.error if hasattr(result, 'error') else "Unknown error",
            )
            return stops
        
        # Extract distance matrix
        distance_matrix = result.data["rows"]
        
        # Simple nearest neighbor algorithm for optimization
        # In a production system, you might want to use a more sophisticated algorithm
        # like the Lin-Kernighan heuristic or a genetic algorithm
        
        # Start with the first stop
        optimized_order = [0]
        unvisited = set(range(1, len(stops)))
        
        while unvisited:
            last = optimized_order[-1]
            # Find the nearest unvisited stop
            nearest = min(
                unvisited,
                key=lambda i: self._get_travel_time(distance_matrix, last, i),
            )
            optimized_order.append(nearest)
            unvisited.remove(nearest)
        
        # Reorder stops
        return [stops[i] for i in optimized_order]
    
    async def _plan_transportation(
        self,
        stops: List[Stop],
        context: AgentContext,
    ) -> List[TransportationOption]:
        """Plan transportation between stops."""
        if len(stops) < 2:
            return []
        
        transportation = []
        
        # Plan transportation between each pair of consecutive stops
        for i in range(len(stops) - 1):
            origin = stops[i]
            destination = stops[i + 1]
            
            # Calculate distance between stops
            distance_result = await self.execute_tool(
                tool_name="maps.distance_matrix",
                tool_args={
                    "origins": [origin.id],
                    "destinations": [destination.id],
                    "mode": "driving",
                },
                context=context,
            )
            
            if not distance_result.success or not distance_result.data.get("rows"):
                self.logger.warning(
                    f"Failed to get distance between {origin.id} and {destination.id}",
                    correlation_id=context.correlation_id,
                    error=distance_result.error if hasattr(distance_result, 'error') else "Unknown error",
                )
                continue
            
            # Get distance in kilometers
            distance_km = distance_result.data["rows"][0]["elements"][0].get("distance", {}).get("value", 0) / 1000
            
            # Determine the best transportation mode
            best_mode = self._select_transportation_mode(distance_km)
            
            # Get detailed directions for the selected mode
            directions_result = await self.execute_tool(
                tool_name="maps.directions",
                tool_args={
                    "origin": origin.id,
                    "destination": destination.id,
                    "mode": best_mode,
                },
                context=context,
            )
            
            if not directions_result.success or not directions_result.data.get("routes"):
                self.logger.warning(
                    f"Failed to get directions from {origin.id} to {destination.id}",
                    correlation_id=context.correlation_id,
                    error=directions_result.error if hasattr(directions_result, 'error') else "Unknown error",
                )
                continue
            
            # Create transportation option
            route = directions_result.data["routes"][0]
            legs = [
                RouteLeg(
                    origin=leg["start_address"],
                    destination=leg["end_address"],
                    distance={
                        "value": leg["distance"]["value"],
                        "text": leg["distance"]["text"],
                    },
                    duration={
                        "value": leg["duration"]["value"],
                        "text": leg["duration"]["text"],
                    },
                    steps=[
                        {
                            "instruction": step["html_instructions"],
                            "distance": step["distance"],
                            "duration": step["duration"],
                            "travel_mode": step["travel_mode"],
                        }
                        for step in leg["steps"]
                    ],
                )
                for leg in route["legs"]
            ]
            
            transportation_option = TransportationOption(
                mode=TransportationMode(best_mode),
                legs=legs,
                total_distance={
                    "value": sum(leg.distance["value"] for leg in legs),
                    "text": f"{sum(leg.distance['value'] for leg in legs) / 1000:.1f} km",
                },
                total_duration={
                    "value": sum(leg.duration["value"] for leg in legs),
                    "text": self._format_duration(sum(leg.duration['value'] for leg in legs)),
                },
                estimated_cost=self._estimate_transportation_cost(best_mode, distance_km),
            )
            
            transportation.append(transportation_option)
        
        return transportation
    
    def _select_transportation_mode(self, distance_km: float) -> str:
        """Select the best transportation mode based on distance and preferences."""
        for option in self.default_transportation:
            max_distance = option.get("max_distance_km", float('inf'))
            if distance_km <= max_distance:
                return option["mode"]
        
        # Default to driving if no suitable mode found
        return "driving"
    
    def _estimate_transportation_cost(
        self,
        mode: str,
        distance_km: float,
    ) -> Dict[str, Any]:
        """Estimate the cost of transportation."""
        # These are rough estimates and should be replaced with more accurate data
        cost_per_km = {
            "walking": 0,
            "bicycling": 0.1,  # Bike rental cost
            "transit": 0.2,    # Public transit fare
            "driving": 0.5,    # Fuel + maintenance
        }
        
        cost = cost_per_km.get(mode, 0.5) * distance_km
        
        return {
            "amount": round(cost, 2),
            "currency": "USD",  # Should be based on location
            "per_km": cost_per_km.get(mode, 0.5),
            "notes": "Estimated cost based on average rates. Actual costs may vary.",
        }
    
    def _create_route_from_distance_matrix(
        self,
        waypoints: List[str],
        distance_matrix: Dict,
        mode: str = "driving",
    ) -> Route:
        """Create a Route object from a distance matrix result."""
        if not waypoints or not distance_matrix.get("rows"):
            return Route(
                waypoints=[],
                legs=[],
                total_distance={"value": 0, "text": "0 km"},
                total_duration={"value": 0, "text": "0 mins"},
                mode=mode,
            )
        
        legs = []
        total_distance = 0
        total_duration = 0
        
        # Create legs between consecutive waypoints
        for i in range(len(waypoints) - 1):
            origin = waypoints[i]
            destination = waypoints[i + 1]
            
            # Get distance and duration from the matrix
            element = distance_matrix["rows"][i]["elements"][i + 1]
            
            leg = RouteLeg(
                origin=origin,
                destination=destination,
                distance={
                    "value": element["distance"]["value"],
                    "text": element["distance"]["text"],
                },
                duration={
                    "value": element["duration"]["value"],
                    "text": element["duration"]["text"],
                },
                steps=[],  # Detailed steps not available from distance matrix
            )
            
            legs.append(leg)
            total_distance += element["distance"]["value"]
            total_duration += element["duration"]["value"]
        
        return Route(
            waypoints=waypoints,
            legs=legs,
            total_distance={
                "value": total_distance,
                "text": f"{total_distance / 1000:.1f} km",
            },
            total_duration={
                "value": total_duration,
                "text": self._format_duration(total_duration),
            },
            mode=mode,
        )
    
    def _generate_itinerary_summary(self, days: List[DayPlan]) -> Dict[str, Any]:
        """Generate a summary of the optimized itinerary."""
        total_stops = sum(len(day.stops) for day in days)
        total_duration = sum(
            sum(leg.duration["value"] for leg in day.transportation)
            for day in days
            if day.transportation
        )
        
        return {
            "total_days": len(days),
            "total_stops": total_stops,
            "total_transportation_time": self._format_duration(total_duration),
            "transportation_modes": list(set(
                leg.mode.value
                for day in days
                if day.transportation
                for leg in day.transportation
            )),
        }
    
    @staticmethod
    def _get_travel_time(distance_matrix: List[Dict], origin: int, destination: int) -> int:
        """Get travel time in seconds between two points from a distance matrix."""
        try:
            return distance_matrix[origin]["elements"][destination]["duration"]["value"]
        except (IndexError, KeyError, TypeError):
            return float('inf')
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format a duration in seconds to a human-readable string."""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        parts = []
        if hours > 0:
            parts.append(f"{int(hours)} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{int(minutes)} minute{'s' if minutes > 1 else ''}")
        
        return " ".join(parts) if parts else "Less than a minute"
