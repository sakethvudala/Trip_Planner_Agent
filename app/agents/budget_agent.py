"""Budget Agent for the Trip Planner system.

This agent is responsible for:
- Managing the trip budget
- Estimating costs for accommodations, activities, and transportation
- Providing budget optimization recommendations
- Tracking expenses against the budget
"""
from datetime import date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from app.agents.base_agent import BaseAgent
from app.agents.base import AgentCard, AgentMessage, AgentContext
from app.schemas import (
    TripPlan, BudgetPreference, BudgetCategory, BudgetItem, 
    BudgetStatus, Accommodation, Activity, TransportationOption
)
from app.framework.adk_runtime import ToolResult

class BudgetAgent(BaseAgent):
    """Agent responsible for budget management and optimization."""
    
    def __init__(
        self,
        llm_client,
        adk_runtime,
        logger=None,
    ):
        """Initialize the Budget Agent."""
        card = AgentCard(
            name="BudgetAgent",
            description="Manages trip budget and provides cost optimization recommendations",
            tools=[],  # Tools will be registered in the base class
            llm_model="gemini-1.5-flash",
        )
        
        super().__init__(card, llm_client, adk_runtime, logger)
        
        # Default cost estimates (per day unless otherwise specified)
        self.default_costs = {
            "accommodation": {
                "budget": 30,
                "midrange": 100,
                "luxury": 250,
                "ultra_luxury": 500,
            },
            "food": {
                "budget": 15,
                "midrange": 40,
                "luxury": 100,
                "ultra_luxury": 200,
            },
            "transportation": {
                "local": 10,  # Public transport, walking
                "moderate": 30,  # Occasional taxis, ride-sharing
                "premium": 75,  # Private transfers, car rental
            },
            "activities": {
                "budget": 10,
                "midrange": 30,
                "luxury": 75,
                "ultra_luxury": 150,
            },
            "souvenirs": 20,  # Per day
            "miscellaneous": 15,  # Per day
        }
    
    def get_tools(self) -> list:
        """Get the list of tools available to this agent."""
        return [
            {
                "name": "currency.convert",
                "description": "Convert between currencies",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "number",
                            "description": "Amount to convert"
                        },
                        "from_currency": {
                            "type": "string",
                            "description": "Source currency code (e.g., 'USD', 'EUR')"
                        },
                        "to_currency": {
                            "type": "string",
                            "description": "Target currency code (e.g., 'JPY', 'GBP')"
                        },
                        "date": {
                            "type": "string",
                            "format": "date",
                            "description": "Historical date for conversion rate (YYYY-MM-DD)"
                        }
                    },
                    "required": ["amount", "from_currency", "to_currency"]
                }
            },
            {
                "name": "expense_tracker.add_expense",
                "description": "Add an expense to the trip budget",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "trip_id": {
                            "type": "string",
                            "description": "ID of the trip"
                        },
                        "category": {
                            "type": "string",
                            "enum": [cat.value for cat in BudgetCategory],
                            "description": "Expense category"
                        },
                        "amount": {
                            "type": "number",
                            "description": "Amount in the trip's currency"
                        },
                        "currency": {
                            "type": "string",
                            "description": "Currency code (e.g., 'USD', 'EUR')"
                        },
                        "date": {
                            "type": "string",
                            "format": "date",
                            "description": "Date of the expense (YYYY-MM-DD)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the expense"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorizing the expense"
                        },
                        "receipt_url": {
                            "type": "string",
                            "description": "URL to the receipt image or document"
                        }
                    },
                    "required": ["trip_id", "category", "amount", "currency", "date"]
                }
            },
            {
                "name": "expense_tracker.get_expenses",
                "description": "Get expenses for a trip",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "trip_id": {
                            "type": "string",
                            "description": "ID of the trip"
                        },
                        "start_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Start date to filter expenses (inclusive)"
                        },
                        "end_date": {
                            "type": "string",
                            "format": "date",
                            "description": "End date to filter expenses (inclusive)"
                        },
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by expense categories"
                        },
                        "min_amount": {
                            "type": "number",
                            "description": "Minimum amount to filter expenses"
                        },
                        "max_amount": {
                            "type": "number",
                            "description": "Maximum amount to filter expenses"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by expense tags"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of expenses to return"
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset for pagination"
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": ["date", "amount", "category"],
                            "default": "date",
                            "description": "Field to sort expenses by"
                        },
                        "sort_order": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "default": "desc",
                            "description": "Sort order"
                        }
                    },
                    "required": ["trip_id"]
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
            
            if action == "check_budget":
                return await self._check_budget(message, context)
            elif action == "estimate_costs":
                return await self._estimate_costs(message, context)
            elif action == "track_expense":
                return await self._track_expense(message, context)
            elif action == "get_budget_summary":
                return await self._get_budget_summary(message, context)
            else:
                return self.create_error_response(
                    ValueError(f"Unknown action: {action}"),
                    recipient=message.sender,
                )
        except Exception as e:
            self.logger.error(
                f"Error in BudgetAgent: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": action},
            )
    
    async def _check_budget(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Check if the trip plan fits within the budget."""
        try:
            # Extract trip plan and budget from message
            content = message.content if isinstance(message.content, dict) else {}
            trip_plan_data = content.get("trip_plan", {})
            budget_data = content.get("budget", {})
            
            if not trip_plan_data or not budget_data:
                raise ValueError("Missing trip_plan or budget in request")
            
            trip_plan = TripPlan(**trip_plan_data)
            budget_pref = BudgetPreference(**budget_data)
            
            # Calculate total trip duration in days
            duration_days = (trip_plan.end_date - trip_plan.start_date).days + 1
            
            # Estimate costs for each category
            cost_estimates = await self._estimate_all_costs(trip_plan, budget_pref, duration_days)
            
            # Calculate total estimated cost
            total_estimated_cost = sum(
                item.estimated_amount 
                for category in cost_estimates.values() 
                for item in category.items
            )
            
            # Calculate budget status
            budget_status = self._calculate_budget_status(
                total_estimated_cost, 
                budget_pref.total_budget,
                budget_pref.currency
            )
            
            # Generate recommendations if needed
            recommendations = []
            if budget_status.status == "over_budget":
                recommendations = self._generate_cost_saving_recommendations(
                    cost_estimates, 
                    budget_status.amount_over_budget,
                    budget_pref.currency
                )
            
            # Prepare response
            response = {
                "status": "success",
                "budget_status": budget_status.dict(),
                "cost_breakdown": {
                    category: {
                        "total": sum(item.estimated_amount for item in items.items),
                        "items": [item.dict() for item in items.items]
                    }
                    for category, items in cost_estimates.items()
                },
                "total_estimated_cost": total_estimated_cost,
                "recommendations": recommendations,
            }
            
            return self.create_response(
                content=response,
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error checking budget: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "check_budget"},
            )
    
    async def _estimate_costs(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Estimate costs for a trip based on preferences."""
        try:
            content = message.content if isinstance(message.content, dict) else {}
            trip_plan_data = content.get("trip_plan", {})
            budget_pref_data = content.get("budget_preferences", {})
            
            if not trip_plan_data:
                raise ValueError("Missing trip_plan in request")
            
            trip_plan = TripPlan(**trip_plan_data)
            budget_pref = BudgetPreference(**budget_pref_data) if budget_pref_data else None
            
            # Calculate total trip duration in days
            duration_days = (trip_plan.end_date - trip_plan.start_date).days + 1
            
            # Estimate costs
            cost_estimates = await self._estimate_all_costs(trip_plan, budget_pref, duration_days)
            
            # Calculate total estimated cost
            total_estimated_cost = sum(
                item.estimated_amount 
                for category in cost_estimates.values() 
                for item in category.items
            )
            
            # Prepare response
            response = {
                "status": "success",
                "cost_estimates": {
                    category: {
                        "total": sum(item.estimated_amount for item in items.items),
                        "items": [item.dict() for item in items.items]
                    }
                    for category, items in cost_estimates.items()
                },
                "total_estimated_cost": total_estimated_cost,
                "currency": budget_pref.currency if budget_pref else "USD",
                "trip_duration_days": duration_days,
            }
            
            return self.create_response(
                content=response,
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error estimating costs: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "estimate_costs"},
            )
    
    async def _track_expense(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Track an expense for the trip."""
        try:
            content = message.content if isinstance(message.content, dict) else {}
            
            # Extract expense details
            trip_id = content.get("trip_id")
            category = content.get("category")
            amount = content.get("amount")
            currency = content.get("currency")
            expense_date = content.get("date", str(date.today()))
            description = content.get("description", "")
            tags = content.get("tags", [])
            receipt_url = content.get("receipt_url")
            
            if not all([trip_id, category, amount is not None, currency]):
                raise ValueError("Missing required fields: trip_id, category, amount, or currency")
            
            # Add the expense
            result = await self.execute_tool(
                tool_name="expense_tracker.add_expense",
                tool_args={
                    "trip_id": trip_id,
                    "category": category,
                    "amount": amount,
                    "currency": currency,
                    "date": expense_date,
                    "description": description,
                    "tags": tags,
                    "receipt_url": receipt_url,
                },
                context=context,
            )
            
            if not result.success:
                raise ValueError(f"Failed to add expense: {result.error}")
            
            # Get updated budget summary
            summary = await self._get_budget_summary_internal(trip_id, context)
            
            return self.create_response(
                content={
                    "status": "success",
                    "expense_id": result.data.get("expense_id"),
                    "budget_summary": summary,
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error tracking expense: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "track_expense"},
            )
    
    async def _get_budget_summary(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Get a summary of the trip budget."""
        try:
            content = message.content if isinstance(message.content, dict) else {}
            trip_id = content.get("trip_id")
            
            if not trip_id:
                raise ValueError("Missing trip_id in request")
            
            summary = await self._get_budget_summary_internal(trip_id, context)
            
            return self.create_response(
                content={
                    "status": "success",
                    "budget_summary": summary,
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error getting budget summary: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "get_budget_summary"},
            )
    
    async def _get_budget_summary_internal(
        self,
        trip_id: str,
        context: AgentContext,
    ) -> Dict[str, Any]:
        """Internal method to get budget summary."""
        # Get all expenses for the trip
        expenses_result = await self.execute_tool(
            tool_name="expense_tracker.get_expenses",
            tool_args={"trip_id": trip_id},
            context=context,
        )
        
        if not expenses_result.success:
            raise ValueError(f"Failed to get expenses: {expenses_result.error}")
        
        expenses = expenses_result.data.get("expenses", [])
        
        # Calculate totals by category
        category_totals = {}
        for expense in expenses:
            category = expense.get("category")
            amount = expense.get("amount", 0)
            
            if category not in category_totals:
                category_totals[category] = 0
            
            category_totals[category] += amount
        
        # Calculate overall total
        total_spent = sum(category_totals.values())
        
        # Get budget information if available
        # In a real implementation, you would fetch the trip's budget from a database
        budget = 0  # Default to 0 if no budget set
        
        return {
            "trip_id": trip_id,
            "total_budget": budget,
            "total_spent": total_spent,
            "remaining_budget": max(0, budget - total_spent) if budget > 0 else None,
            "category_breakdown": [
                {"category": cat, "amount": amt, "percentage": (amt / total_spent * 100) if total_spent > 0 else 0}
                for cat, amt in category_totals.items()
            ],
            "expense_count": len(expenses),
            "last_updated": str(datetime.utcnow()),
        }
    
    async def _estimate_all_costs(
        self,
        trip_plan: TripPlan,
        budget_pref: Optional[BudgetPreference],
        duration_days: int,
    ) -> Dict[str, BudgetCategory]:
        """Estimate costs for all categories."""
        currency = budget_pref.currency if budget_pref else "USD"
        
        # Initialize cost estimates
        cost_estimates = {
            "accommodation": BudgetCategory(
                name="Accommodation",
                items=[],
                total_estimated_amount=0,
                currency=currency,
            ),
            "food": BudgetCategory(
                name="Food & Dining",
                items=[],
                total_estimated_amount=0,
                currency=currency,
            ),
            "transportation": BudgetCategory(
                name="Transportation",
                items=[],
                total_estimated_amount=0,
                currency=currency,
            ),
            "activities": BudgetCategory(
                name="Activities & Entertainment",
                items=[],
                total_estimated_amount=0,
                currency=currency,
            ),
            "souvenirs": BudgetCategory(
                name="Souvenirs & Shopping",
                items=[],
                total_estimated_amount=0,
                currency=currency,
            ),
            "miscellaneous": BudgetCategory(
                name="Miscellaneous",
                items=[],
                total_estimated_amount=0,
                currency=currency,
            ),
        }
        
        # Estimate accommodation costs
        if trip_plan.hotels:
            for hotel in trip_plan.hotels:
                # Use actual price if available, otherwise estimate based on rating
                price_per_night = hotel.price_per_night or self._estimate_hotel_cost(
                    hotel.rating,
                    budget_pref.accommodation_comfort if budget_pref else "midrange",
                    currency
                )
                
                item = BudgetItem(
                    name=f"{hotel.name} ({hotel.room_type or 'Standard'})",
                    description=f"{hotel.rating}★ hotel in {hotel.location}",
                    estimated_amount=price_per_night * duration_days,
                    currency=currency,
                    per_unit=f"{price_per_night} {currency}/night",
                    quantity=duration_days,
                    category="accommodation",
                )
                
                cost_estimates["accommodation"].items.append(item)
                cost_estimates["accommodation"].total_estimated_amount += item.estimated_amount
        else:
            # Estimate based on preferences
            comfort = budget_pref.accommodation_comfort if budget_pref else "midrange"
            price_per_night = self._get_default_cost("accommodation", comfort, duration_days)
            
            item = BudgetItem(
                name=f"{comfort.capitalize()} Accommodation",
                description=f"Estimated cost for {comfort} accommodations",
                estimated_amount=price_per_night * duration_days,
                currency=currency,
                per_unit=f"{price_per_night} {currency}/night",
                quantity=duration_days,
                category="accommodation",
            )
            
            cost_estimates["accommodation"].items.append(item)
            cost_estimates["accommodation"].total_estimated_amount = item.estimated_amount
        
        # Estimate food costs
        food_comfort = budget_pref.food_comfort if budget_pref else "midrange"
        food_per_day = self._get_default_cost("food", food_comfort, 1)
        
        food_item = BudgetItem(
            name=f"{food_comfort.capitalize()} Dining",
            description=f"Estimated cost for {food_comfort} dining",
            estimated_amount=food_per_day * duration_days,
            currency=currency,
            per_unit=f"{food_per_day} {currency}/day",
            quantity=duration_days,
            category="food",
        )
        
        cost_estimates["food"].items.append(food_item)
        cost_estimates["food"].total_estimated_amount = food_item.estimated_amount
        
        # Estimate transportation costs
        if trip_plan.transportation:
            for transport in trip_plan.transportation:
                if hasattr(transport, 'estimated_cost') and transport.estimated_cost:
                    cost = transport.estimated_cost.get('amount', 0)
                    
                    item = BudgetItem(
                        name=f"Transport: {transport.mode}",
                        description=f"From {transport.origin} to {transport.destination}",
                        estimated_amount=cost,
                        currency=transport.estimated_cost.get('currency', currency),
                        category="transportation",
                    )
                    
                    cost_estimates["transportation"].items.append(item)
                    cost_estimates["transportation"].total_estimated_amount += cost
        else:
            # Estimate based on preferences
            transport_comfort = budget_pref.transportation_comfort if budget_pref else "moderate"
            transport_per_day = self._get_default_cost("transportation", transport_comfort, 1)
            
            item = BudgetItem(
                name=f"{transport_comfort.capitalize()} Transportation",
                description=f"Estimated cost for {transport_comfort} transportation",
                estimated_amount=transport_per_day * duration_days,
                currency=currency,
                per_unit=f"{transport_per_day} {currency}/day",
                quantity=duration_days,
                category="transportation",
            )
            
            cost_estimates["transportation"].items.append(item)
            cost_estimates["transportation"].total_estimated_amount = item.estimated_amount
        
        # Estimate activity costs
        if trip_plan.activities:
            for activity in trip_plan.activities:
                if hasattr(activity, 'cost') and activity.cost:
                    cost = activity.cost.get('amount', 0)
                    
                    item = BudgetItem(
                        name=activity.name,
                        description=activity.description or "",
                        estimated_amount=cost,
                        currency=activity.cost.get('currency', currency),
                        category="activities",
                    )
                    
                    cost_estimates["activities"].items.append(item)
                    cost_estimates["activities"].total_estimated_amount += cost
        else:
            # Estimate based on preferences
            activity_comfort = budget_pref.activity_comfort if budget_pref else "midrange"
            activities_per_day = 2  # Assume 2 activities per day
            activity_cost = self._get_default_cost("activities", activity_comfort, 1)
            total_activities = activities_per_day * duration_days
            
            item = BudgetItem(
                name=f"{activity_comfort.capitalize()} Activities",
                description=f"Estimated cost for {activity_comfort} activities",
                estimated_amount=activity_cost * total_activities,
                currency=currency,
                per_unit=f"{activity_cost} {currency}/activity",
                quantity=total_activities,
                category="activities",
            )
            
            cost_estimates["activities"].items.append(item)
            cost_estimates["activities"].total_estimated_amount = item.estimated_amount
        
        # Estimate souvenirs and miscellaneous costs
        souvenirs_per_day = self._get_default_cost("souvenirs", "", 1)
        misc_per_day = self._get_default_cost("miscellaneous", "", 1)
        
        souvenirs_item = BudgetItem(
            name="Souvenirs & Shopping",
            description="Estimated cost for souvenirs and shopping",
            estimated_amount=souvenirs_per_day * duration_days,
            currency=currency,
            per_unit=f"{souvenirs_per_day} {currency}/day",
            quantity=duration_days,
            category="souvenirs",
        )
        
        misc_item = BudgetItem(
            name="Miscellaneous Expenses",
            description="Estimated cost for miscellaneous expenses",
            estimated_amount=misc_per_day * duration_days,
            currency=currency,
            per_unit=f"{misc_per_day} {currency}/day",
            quantity=duration_days,
            category="miscellaneous",
        )
        
        cost_estimates["souvenirs"].items.append(souvenirs_item)
        cost_estimates["souvenirs"].total_estimated_amount = souvenirs_item.estimated_amount
        
        cost_estimates["miscellaneous"].items.append(misc_item)
        cost_estimates["miscellaneous"].total_estimated_amount = misc_item.estimated_amount
        
        return cost_estimates
    
    def _calculate_budget_status(
        self,
        total_estimated_cost: float,
        total_budget: float,
        currency: str,
    ) -> BudgetStatus:
        """Calculate the budget status based on estimated costs and total budget."""
        if total_budget <= 0:
            return BudgetStatus(
                status="no_budget_set",
                total_budget=total_budget,
                total_estimated_cost=total_estimated_cost,
                currency=currency,
                amount_over_budget=0,
                percentage_of_budget=0,
            )
        
        amount_over_budget = max(0, total_estimated_cost - total_budget)
        percentage_of_budget = (total_estimated_cost / total_budget) * 100
        
        if amount_over_budget > 0:
            status = "over_budget"
        elif percentage_of_budget >= 90:
            status = "close_to_budget"
        else:
            status = "within_budget"
        
        return BudgetStatus(
            status=status,
            total_budget=total_budget,
            total_estimated_cost=total_estimated_cost,
            currency=currency,
            amount_over_budget=amount_over_budget,
            percentage_of_budget=percentage_of_budget,
        )
    
    def _generate_cost_saving_recommendations(
        self,
        cost_estimates: Dict[str, BudgetCategory],
        amount_over_budget: float,
        currency: str,
    ) -> List[Dict[str, Any]]:
        """Generate recommendations to reduce costs."""
        recommendations = []
        
        # Sort categories by estimated amount (highest first)
        sorted_categories = sorted(
            cost_estimates.values(),
            key=lambda x: x.total_estimated_amount,
            reverse=True
        )
        
        # Generate recommendations for top 3 most expensive categories
        for category in sorted_categories[:3]:
            if category.total_estimated_amount <= 0:
                continue
                
            # Calculate potential savings (e.g., 10-20% of the category total)
            min_savings = category.total_estimated_amount * 0.1
            max_savings = category.total_estimated_amount * 0.2
            
            recommendations.append({
                "category": category.name,
                "current_cost": {
                    "amount": category.total_estimated_amount,
                    "currency": currency,
                },
                "potential_savings": {
                    "min": min_savings,
                    "max": max_savings,
                    "currency": currency,
                },
                "suggestions": self._get_cost_saving_suggestions(
                    category.name.lower(),
                    category.total_estimated_amount,
                    currency
                ),
            })
        
        return recommendations
    
    def _get_cost_saving_suggestions(
        self,
        category: str,
        current_cost: float,
        currency: str,
    ) -> List[str]:
        """Get cost-saving suggestions for a specific category."""
        suggestions = []
        
        if category == "accommodation":
            suggestions = [
                f"Consider staying in budget accommodations to save up to 30% on your {currency}{current_cost:.2f} accommodation cost.",
                "Look for accommodations with kitchen facilities to save on food costs by preparing some meals yourself.",
                "Consider alternative accommodations like vacation rentals or hostels which can be more affordable than hotels.",
            ]
        elif category == "food":
            suggestions = [
                f"Dine at local eateries instead of tourist restaurants to save on your {currency}{current_cost:.2f} food budget.",
                "Have breakfast included with your accommodation or prepare simple meals to reduce dining costs.",
                "Limit dining at high-end restaurants to special occasions to significantly reduce food expenses.",
            ]
        elif category == "transportation":
            suggestions = [
                f"Use public transportation instead of taxis to reduce your {currency}{current_cost:.2f} transportation costs.",
                "Consider walking or renting a bike for short distances to save on transportation.",
                "Look for transportation passes or tourist cards that offer unlimited travel for a fixed price.",
            ]
        elif category == "activities":
            suggestions = [
                f"Look for free or low-cost activities to reduce your {currency}{current_cost:.2f} activity expenses.",
                "Prioritize must-see attractions and skip those you're less interested in.",
                "Check for combination tickets or city passes that offer discounts on multiple attractions.",
            ]
        else:
            suggestions = [
                f"Review your {category} expenses to identify areas where you can cut back.",
                "Look for discounts, coupons, or special offers to reduce costs in this category.",
                "Consider if all planned expenses in this category are necessary or if some can be eliminated.",
            ]
        
        return suggestions
    
    def _estimate_hotel_cost(
        self,
        rating: float,
        comfort_level: str,
        currency: str,
    ) -> float:
        """Estimate hotel cost based on rating and comfort level."""
        # Base cost based on comfort level
        base_cost = self.default_costs["accommodation"].get(comfort_level, 100)
        
        # Adjust based on rating (higher rating = higher price)
        rating_multiplier = 1.0 + (rating - 3) * 0.2  # 20% increase per star above 3
        
        return base_cost * rating_multiplier
    
    def _get_default_cost(
        self,
        category: str,
        comfort_level: str,
        quantity: int = 1,
    ) -> float:
        """Get the default cost for a category and comfort level."""
        if category not in self.default_costs:
            return 0.0
        
        if isinstance(self.default_costs[category], dict):
            # For categories with comfort levels (accommodation, food, etc.)
            if comfort_level not in self.default_costs[category]:
                comfort_level = "midrange"  # Default to midrange if invalid comfort level
            return self.default_costs[category][comfort_level] * quantity
        else:
            # For fixed cost categories (souvenirs, miscellaneous)
            return self.default_costs[category] * quantity
