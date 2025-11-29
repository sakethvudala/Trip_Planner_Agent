"""Planner Agent for the Trip Planner system.

This agent is responsible for high-level trip planning, including:
- Understanding user preferences and constraints
- Coordinating with specialized agents
- Creating an initial trip itinerary
- Handling changes and updates to the plan
"""
from typing import Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.agents.base import AgentCard, AgentMessage, AgentContext
from app.schemas import TripRequest, TripPlan, DayPlan, Stop, HotelOption
from app.framework.adk_runtime import ToolResult

class PlannerAgent(BaseAgent):
    """Agent responsible for high-level trip planning."""
    
    def __init__(
        self,
        llm_client,
        adk_runtime,
        location_agent=None,
        route_agent=None,
        budget_agent=None,
        stay_agent=None,
        logger=None,
    ):
        """Initialize the Planner Agent."""
        card = AgentCard(
            name="PlannerAgent",
            description="Coordinates trip planning by delegating to specialized agents",
            tools=[],  # This agent doesn't directly use tools
            llm_model="gemini-1.5-flash",
        )
        
        super().__init__(card, llm_client, adk_runtime, logger)
        
        # References to other agents
        self.location_agent = location_agent
        self.route_agent = route_agent
        self.budget_agent = budget_agent
        self.stay_agent = stay_agent
    
    def get_tools(self) -> list:
        """Get the list of tools available to this agent."""
        return []  # Planner agent doesn't directly use tools
    
    async def _process_message(
        self, 
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Process an incoming message and return a response."""
        # Extract the trip request from the message
        trip_request = self._extract_trip_request(message, context)
        if not trip_request:
            return self.create_error_response(
                ValueError("Could not extract trip request from message"),
                recipient=message.sender,
            )
        
        # Store the trip request in the context
        context.trip_request = trip_request
        
        # Create an initial trip plan
        trip_plan = TripPlan(
            destination=trip_request.location.base_city,
            country=trip_request.location.country or "",
            start_date=trip_request.location.start_date,
            end_date=trip_request.location.end_date,
            days=[],
            hotels=[],
            estimated_total_cost=0,
            currency=trip_request.budget.currency,
        )
        
        # Store the trip plan in the context
        context.trip_plan = trip_plan
        
        # Check if we have a result from a previous step
        if isinstance(message.content, dict) and "last_step_result" in message.content:
            last_result = message.content["last_step_result"]
            last_agent = message.content.get("last_agent")
            
            if last_agent == "location":
                 self._update_plan_with_locations(
                    trip_plan, 
                    last_result.get("recommendations", [])
                )
            elif last_agent == "stay":
                self._update_plan_with_hotels(
                    trip_plan, 
                    last_result.get("hotels", [])
                )
            elif last_agent == "route":
                self._update_plan_with_routes(
                    trip_plan, 
                    last_result.get("optimized_itinerary", {})
                )
            elif last_agent == "budget":
                self._update_plan_with_budget(
                    trip_plan, 
                    last_result.get("budget_adjustments", {})
                )
        
        # Check state and decide next step
        try:
            # 1. Check if we have location recommendations
            if not trip_plan.days:
                return self.create_response(
                    content={
                        "target_agent": "location",
                        "action": "get_recommendations",
                        "parameters": {"trip_request": trip_request.dict()}
                    },
                    recipient=message.sender
                )
            
            # 2. Check if we have hotel recommendations
            if not trip_plan.hotels:
                return self.create_response(
                    content={
                        "target_agent": "stay",
                        "action": "find_accommodations",
                        "parameters": {"trip_request": trip_request.dict()}
                    },
                    recipient=message.sender
                )
            
            # 3. Check if routes are optimized (check if transportation is set for first day)
            if trip_plan.days and not trip_plan.days[0].transportation:
                 return self.create_response(
                    content={
                        "target_agent": "route",
                        "action": "optimize_itinerary",
                        "parameters": {"trip_plan": trip_plan.dict()}
                    },
                    recipient=message.sender
                )

            # 4. Check budget (check if estimated cost is calculated)
            if trip_plan.estimated_total_cost == 0:
                 return self.create_response(
                    content={
                        "target_agent": "budget",
                        "action": "check_budget",
                        "parameters": {
                            "trip_plan": trip_plan.dict(),
                            "budget": trip_request.budget.dict()
                        }
                    },
                    recipient=message.sender
                )
            
            # If all steps are done, return the final plan
            return self.create_response(
                content={
                    "action": "finish",
                    "status": "success",
                    "trip_plan": trip_plan.dict(),
                    "summary": self._generate_trip_summary(trip_plan),
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error in PlannerAgent: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"trip_request": trip_request.dict() if trip_request else None},
            )
    
    def _extract_trip_request(self, message: AgentMessage, context: AgentContext):
        """Extract a TripRequest from the message."""
        try:
            if isinstance(message.content, dict) and "trip_request" in message.content:
                return TripRequest(**message.content["trip_request"])
            elif hasattr(context, "trip_request") and context.trip_request:
                return context.trip_request
            else:
                # Try to parse the message content as a trip request
                return TripRequest(**message.content)
        except Exception as e:
            self.logger.error(
                f"Error extracting trip request: {str(e)}",
                correlation_id=context.correlation_id,
                message_content=message.content,
                error=str(e),
            )
            return None
    
    def _update_plan_with_locations(self, trip_plan: TripPlan, locations: List[Dict]):
        """Update the trip plan with location recommendations."""
        if not locations:
            return
        
        # Create a day plan for each day of the trip
        num_days = (trip_plan.end_date - trip_plan.start_date).days + 1
        
        for day_num in range(num_days):
            current_date = trip_plan.start_date + timedelta(days=day_num)
            
            # Create stops for this day (simplified example)
            stops = []
            for i, location in enumerate(locations[:3]):  # Max 3 locations per day
                stop = Stop(
                    id=f"stop_{day_num}_{i}",
                    name=location.get("name", f"Attraction {i+1}"),
                    category=location.get("category", "attraction"),
                    description=location.get("description", ""),
                    estimated_duration_minutes=120,  # Default 2 hours per location
                    coordinates=location.get("coordinates"),
                )
                stops.append(stop)
            
            # Create a day plan
            day_plan = DayPlan(
                date=current_date,
                stops=stops,
                notes=f"Day {day_num + 1} of your trip to {trip_plan.destination}",
            )
            
            trip_plan.days.append(day_plan)
    
    def _update_plan_with_hotels(self, trip_plan: TripPlan, hotels: List[Dict]):
        """Update the trip plan with hotel recommendations."""
        if not hotels:
            return
        
        # Convert hotel dictionaries to HotelOption objects
        hotel_options = []
        for hotel_data in hotels[:5]:  # Limit to top 5 hotels
            try:
                hotel = HotelOption(**hotel_data)
                hotel_options.append(hotel)
            except Exception as e:
                self.logger.error(
                    f"Error creating HotelOption: {str(e)}",
                    hotel_data=hotel_data,
                    error=str(e),
                )
        
        # Update the trip plan
        trip_plan.hotels = hotel_options
        
        # Select the top-rated hotel as recommended
        if hotel_options:
            trip_plan.recommended_hotel = hotel_options[0]
    
    def _update_plan_with_routes(self, trip_plan: TripPlan, optimized_routes: Dict):
        """Update the trip plan with optimized routes."""
        if not optimized_routes or not trip_plan.days:
            return
        
        # Update each day's plan with optimized routes
        for day_plan in trip_plan.days:
            day_key = day_plan.date.isoformat()
            if day_key in optimized_routes:
                day_plan.transportation = optimized_routes[day_key].get("transportation", [])
                day_plan.notes = optimized_routes[day_key].get("notes", day_plan.notes)
    
    def _update_plan_with_budget(self, trip_plan: TripPlan, budget_adjustments: Dict):
        """Update the trip plan with budget adjustments."""
        if not budget_adjustments:
            return
        
        # Update the trip plan with budget information
        if "estimated_total_cost" in budget_adjustments:
            trip_plan.estimated_total_cost = budget_adjustments["estimated_total_cost"]
        
        if "budget_status" in budget_adjustments:
            trip_plan.budget_status = budget_adjustments["budget_status"]
        
        if "budget_remaining" in budget_adjustments:
            trip_plan.budget_remaining = budget_adjustments["budget_remaining"]
        
        # Apply any cost-saving recommendations
        if "recommendations" in budget_adjustments:
            if not hasattr(trip_plan, "budget_recommendations"):
                trip_plan.budget_recommendations = []
            
            trip_plan.budget_recommendations.extend(budget_adjustments["recommendations"])
    
    def _generate_trip_summary(self, trip_plan: TripPlan) -> Dict:
        """Generate a summary of the trip plan."""
        if not trip_plan:
            return {}
        
        return {
            "destination": f"{trip_plan.destination}, {trip_plan.country}",
            "duration": f"{(trip_plan.end_date - trip_plan.start_date).days + 1} days",
            "total_stops": sum(len(day.stops) for day in trip_plan.days),
            "recommended_hotel": trip_plan.recommended_hotel.name if trip_plan.recommended_hotel else "None",
            "estimated_cost": f"{trip_plan.estimated_total_cost} {trip_plan.currency}",
            "budget_status": getattr(trip_plan, "budget_status", "Not calculated"),
        }
