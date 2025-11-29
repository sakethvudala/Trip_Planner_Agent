"""Stay Agent for the Trip Planner system.

This agent is responsible for:
- Finding and recommending accommodations (hotels, vacation rentals, etc.)
- Managing booking information and availability
- Providing details about amenities and room options
- Handling special requests and preferences
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from app.agents.base_agent import BaseAgent
from app.agents.base import AgentCard, AgentMessage, AgentContext
from app.schemas import (
    Accommodation, RoomType, Amenity, Location, PriceRange,
    BookingStatus, CancellationPolicy, Review, StayPreference
)
from app.framework.adk_runtime import ToolResult

class StayAgent(BaseAgent):
    """Agent responsible for handling accommodations and lodging."""
    
    def __init__(
        self,
        llm_client,
        adk_runtime,
        logger=None,
    ):
        """Initialize the Stay Agent."""
        card = AgentCard(
            name="StayAgent",
            description="Finds and manages accommodations for the trip",
            tools=[],  # Tools will be registered in the base class
            llm_model="gemini-1.5-flash",
        )
        
        super().__init__(card, llm_client, adk_runtime, logger)
        
        # Mock data for demonstration
        self.mock_hotels = self._initialize_mock_hotels()
    
    def get_tools(self) -> list:
        """Get the list of tools available to this agent."""
        return [
            {
                "name": "hotels.search",
                "description": "Search for hotels and accommodations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City, address, or coordinates to search near"
                        },
                        "check_in": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-in date (YYYY-MM-DD)"
                        },
                        "check_out": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-out date (YYYY-MM-DD)"
                        },
                        "guests": {
                            "type": "integer",
                            "description": "Number of guests",
                            "default": 2
                        },
                        "rooms": {
                            "type": "integer",
                            "description": "Number of rooms needed",
                            "default": 1
                        },
                        "price_min": {
                            "type": "number",
                            "description": "Minimum price per night"
                        },
                        "price_max": {
                            "type": "number",
                            "description": "Maximum price per night"
                        },
                        "stars": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 1, "maximum": 5},
                            "description": "Filter by star rating"
                        },
                        "amenities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of required amenities"
                        },
                        "free_cancellation": {
                            "type": "boolean",
                            "description": "Only show properties with free cancellation"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10
                        }
                    },
                    "required": ["location", "check_in", "check_out"]
                }
            },
            {
                "name": "hotels.get_details",
                "description": "Get detailed information about a specific hotel",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hotel_id": {
                            "type": "string",
                            "description": "ID of the hotel to get details for"
                        },
                        "check_in": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-in date (YYYY-MM-DD)"
                        },
                        "check_out": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-out date (YYYY-MM-DD)"
                        },
                        "guests": {
                            "type": "integer",
                            "description": "Number of guests",
                            "default": 2
                        },
                        "rooms": {
                            "type": "integer",
                            "description": "Number of rooms needed",
                            "default": 1
                        }
                    },
                    "required": ["hotel_id"]
                }
            },
            {
                "name": "hotels.check_availability",
                "description": "Check room availability for specific dates",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hotel_id": {
                            "type": "string",
                            "description": "ID of the hotel to check"
                        },
                        "room_type_id": {
                            "type": "string",
                            "description": "ID of the room type to check"
                        },
                        "check_in": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-in date (YYYY-MM-DD)"
                        },
                        "check_out": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-out date (YYYY-MM-DD)"
                        },
                        "guests": {
                            "type": "integer",
                            "description": "Number of guests",
                            "default": 2
                        },
                        "rooms": {
                            "type": "integer",
                            "description": "Number of rooms needed",
                            "default": 1
                        }
                    },
                    "required": ["hotel_id", "room_type_id", "check_in", "check_out"]
                }
            },
            {
                "name": "hotels.book",
                "description": "Book a hotel room",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hotel_id": {
                            "type": "string",
                            "description": "ID of the hotel to book"
                        },
                        "room_type_id": {
                            "type": "string",
                            "description": "ID of the room type to book"
                        },
                        "check_in": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-in date (YYYY-MM-DD)"
                        },
                        "check_out": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-out date (YYYY-MM-DD)"
                        },
                        "guests": {
                            "type": "integer",
                            "description": "Number of guests",
                            "default": 2
                        },
                        "rooms": {
                            "type": "integer",
                            "description": "Number of rooms to book",
                            "default": 1
                        },
                        "guest_name": {
                            "type": "string",
                            "description": "Name of the primary guest"
                        },
                        "email": {
                            "type": "string",
                            "format": "email",
                            "description": "Email address for booking confirmation"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Phone number for booking confirmation"
                        },
                        "special_requests": {
                            "type": "string",
                            "description": "Any special requests for the booking"
                        },
                        "payment_method": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["credit_card", "debit_card", "paypal", "other"],
                                    "description": "Type of payment method"
                                },
                                "card_number": {
                                    "type": "string",
                                    "description": "Card number (for credit/debit cards)"
                                },
                                "expiry_date": {
                                    "type": "string",
                                    "description": "Card expiry date (MM/YY)"
                                },
                                "cvv": {
                                    "type": "string",
                                    "description": "Card CVV"
                                },
                                "name_on_card": {
                                    "type": "string",
                                    "description": "Name as it appears on the card"
                                }
                            },
                            "required": ["type"]
                        }
                    },
                    "required": [
                        "hotel_id", "room_type_id", "check_in", "check_out",
                        "guest_name", "email", "phone", "payment_method"
                    ]
                }
            },
            {
                "name": "hotels.cancel_booking",
                "description": "Cancel a hotel booking",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "booking_id": {
                            "type": "string",
                            "description": "ID of the booking to cancel"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for cancellation"
                        }
                    },
                    "required": ["booking_id"]
                }
            },
            {
                "name": "hotels.get_booking_details",
                "description": "Get details of a specific booking",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "booking_id": {
                            "type": "string",
                            "description": "ID of the booking to retrieve"
                        },
                        "email": {
                            "type": "string",
                            "format": "email",
                            "description": "Email address associated with the booking"
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Last name of the primary guest"
                        }
                    },
                    "required": ["booking_id"]
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
            
            if action == "search_accommodations":
                return await self._search_accommodations(message, context)
            elif action == "get_accommodation_details":
                return await self._get_accommodation_details(message, context)
            elif action == "book_accommodation":
                return await self._book_accommodation(message, context)
            elif action == "cancel_booking":
                return await self._cancel_booking(message, context)
            elif action == "get_booking_details":
                return await self._get_booking_details(message, context)
            else:
                return self.create_error_response(
                    ValueError(f"Unknown action: {action}"),
                    recipient=message.sender,
                )
        except Exception as e:
            self.logger.error(
                f"Error in StayAgent: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": action},
            )
    
    async def _search_accommodations(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Search for accommodations based on criteria."""
        try:
            content = message.content if isinstance(message.content, dict) else {}
            
            # Extract search parameters
            location = content.get("location")
            check_in = content.get("check_in")
            check_out = content.get("check_out")
            guests = content.get("guests", 2)
            rooms = content.get("rooms", 1)
            price_min = content.get("price_min")
            price_max = content.get("price_max")
            stars = content.get("stars", [])
            amenities = content.get("amenities", [])
            free_cancellation = content.get("free_cancellation", False)
            limit = min(content.get("limit", 10), 50)  # Cap at 50 results
            
            if not all([location, check_in, check_out]):
                raise ValueError("Missing required search parameters: location, check_in, or check_out")
            
            # In a real implementation, this would call the hotels.search tool
            # For now, we'll use mock data
            search_results = await self._mock_search_hotels(
                location=location,
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                rooms=rooms,
                price_min=price_min,
                price_max=price_max,
                stars=stars,
                amenities=amenities,
                free_cancellation=free_cancellation,
                limit=limit,
            )
            
            return self.create_response(
                content={
                    "status": "success",
                    "count": len(search_results),
                    "results": search_results,
                    "search_parameters": {
                        "location": location,
                        "check_in": check_in,
                        "check_out": check_out,
                        "guests": guests,
                        "rooms": rooms,
                    }
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error searching accommodations: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "search_accommodations"},
            )
    
    async def _get_accommodation_details(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Get detailed information about a specific accommodation."""
        try:
            content = message.content if isinstance(message.content, dict) else {}
            hotel_id = content.get("hotel_id")
            
            if not hotel_id:
                raise ValueError("Missing required parameter: hotel_id")
            
            # In a real implementation, this would call the hotels.get_details tool
            # For now, we'll use mock data
            hotel = next((h for h in self.mock_hotels if h["id"] == hotel_id), None)
            
            if not hotel:
                raise ValueError(f"Hotel with ID {hotel_id} not found")
            
            return self.create_response(
                content={
                    "status": "success",
                    "hotel": hotel,
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error getting accommodation details: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "get_accommodation_details"},
            )
    
    async def _book_accommodation(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Book an accommodation."""
        try:
            content = message.content if isinstance(message.content, dict) else {}
            
            # Extract booking details
            hotel_id = content.get("hotel_id")
            room_type_id = content.get("room_type_id")
            check_in = content.get("check_in")
            check_out = content.get("check_out")
            guests = content.get("guests", 2)
            rooms = content.get("rooms", 1)
            guest_name = content.get("guest_name")
            email = content.get("email")
            phone = content.get("phone")
            special_requests = content.get("special_requests")
            payment_method = content.get("payment_method", {})
            
            if not all([hotel_id, room_type_id, check_in, check_out, guest_name, email, phone, payment_method]):
                raise ValueError("Missing required booking parameters")
            
            # In a real implementation, this would call the hotels.book tool
            # For now, we'll simulate a successful booking
            booking_id = f"BOOK-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{hotel_id[:4].upper()}"
            
            # Create a mock booking confirmation
            booking_details = {
                "booking_id": booking_id,
                "status": "confirmed",
                "hotel_id": hotel_id,
                "room_type_id": room_type_id,
                "check_in": check_in,
                "check_out": check_out,
                "guests": guests,
                "rooms": rooms,
                "guest_name": guest_name,
                "email": email,
                "phone": phone,
                "special_requests": special_requests,
                "booking_date": datetime.utcnow().isoformat(),
                "cancellation_policy": {
                    "free_cancellation_until": (datetime.strptime(check_in, "%Y-%m-%d") - timedelta(days=3)).strftime("%Y-%m-%d"),
                    "cancellation_fee_after": "Full stay cost",
                },
                "total_amount": {
                    "amount": 120 * rooms * ((datetime.strptime(check_out, "%Y-%m-%d") - datetime.strptime(check_in, "%Y-%m-%d")).days),
                    "currency": "USD",
                    "breakdown": [
                        {
                            "type": "room_rate",
                            "description": f"{rooms} x {room_type_id} x {(datetime.strptime(check_out, '%Y-%m-%d') - datetime.strptime(check_in, '%Y-%m-%d')).days} nights",
                            "amount": 120 * rooms * ((datetime.strptime(check_out, "%Y-%m-%d") - datetime.strptime(check_in, "%Y-%m-%d")).days),
                            "currency": "USD"
                        },
                        {
                            "type": "taxes_and_fees",
                            "description": "Taxes and service charges",
                            "amount": 25 * rooms,
                            "currency": "USD"
                        }
                    ]
                },
                "payment_status": "paid",
                "confirmation_number": f"CNF-{booking_id}",
            }
            
            return self.create_response(
                content={
                    "status": "success",
                    "booking": booking_details,
                    "message": "Your booking has been confirmed!",
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error booking accommodation: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "book_accommodation"},
            )
    
    async def _cancel_booking(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Cancel a booking."""
        try:
            content = message.content if isinstance(message.content, dict) else {}
            booking_id = content.get("booking_id")
            reason = content.get("reason", "No reason provided")
            
            if not booking_id:
                raise ValueError("Missing required parameter: booking_id")
            
            # In a real implementation, this would call the hotels.cancel_booking tool
            # For now, we'll simulate a successful cancellation
            cancellation_details = {
                "booking_id": booking_id,
                "status": "cancelled",
                "cancellation_date": datetime.utcnow().isoformat(),
                "refund_amount": {
                    "amount": 0,  # Would be calculated based on cancellation policy
                    "currency": "USD",
                },
                "cancellation_fee": {
                    "amount": 0,  # Would be calculated based on cancellation policy
                    "currency": "USD",
                },
                "reason": reason,
            }
            
            return self.create_response(
                content={
                    "status": "success",
                    "cancellation": cancellation_details,
                    "message": "Your booking has been cancelled successfully.",
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error cancelling booking: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "cancel_booking"},
            )
    
    async def _get_booking_details(
        self,
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Get details of a specific booking."""
        try:
            content = message.content if isinstance(message.content, dict) else {}
            booking_id = content.get("booking_id")
            email = content.get("email")
            last_name = content.get("last_name")
            
            if not booking_id:
                raise ValueError("Missing required parameter: booking_id")
            
            # In a real implementation, this would call the hotels.get_booking_details tool
            # For now, we'll return a mock booking
            booking_details = {
                "booking_id": booking_id,
                "status": "confirmed",
                "hotel_name": "Grand Hotel Example",
                "room_type": "Deluxe King Room",
                "check_in": "2023-12-15",
                "check_out": "2023-12-20",
                "guests": 2,
                "rooms": 1,
                "guest_name": f"{content.get('guest_name', 'John')} {last_name or 'Doe'}",
                "email": email or "john.doe@example.com",
                "booking_date": "2023-11-01T14:30:00Z",
                "total_amount": {
                    "amount": 850,
                    "currency": "USD",
                },
                "cancellation_policy": {
                    "free_cancellation_until": "2023-12-12",
                    "cancellation_fee_after": "Full stay cost",
                },
                "amenities": ["Free WiFi", "Swimming Pool", "Fitness Center", "Restaurant"],
                "check_in_instructions": "Check-in time is 3:00 PM. Please bring a valid ID and the credit card used for booking.",
                "contact_information": {
                    "hotel_phone": "+1-555-123-4567",
                    "hotel_email": "reservations@grandhotelexample.com",
                    "hotel_address": "123 Example Street, City, Country"
                }
            }
            
            return self.create_response(
                content={
                    "status": "success",
                    "booking": booking_details,
                },
                recipient=message.sender,
            )
            
        except Exception as e:
            self.logger.error(
                f"Error getting booking details: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            return self.create_error_response(
                e,
                recipient=message.sender,
                context={"action": "get_booking_details"},
            )
    
    # Helper methods for mock data
    
    def _initialize_mock_hotels(self) -> List[Dict]:
        """Initialize mock hotel data for demonstration."""
        return [
            {
                "id": "hotel_1",
                "name": "Grand Hotel Example",
                "star_rating": 4.5,
                "address": "123 Example Street, City, Country",
                "location": {
                    "lat": 40.7128,
                    "lng": -74.0060,
                    "city": "New York",
                    "country": "United States"
                },
                "description": "A luxurious hotel in the heart of the city, offering world-class amenities and exceptional service.",
                "amenities": [
                    "Free WiFi", "Swimming Pool", "Fitness Center", "Spa", "Restaurant",
                    "Room Service", "24-Hour Front Desk", "Business Center", "Laundry Service"
                ],
                "images": [
                    "https://example.com/hotel1_1.jpg",
                    "https://example.com/hotel1_2.jpg"
                ],
                "room_types": [
                    {
                        "id": "room_1_1",
                        "name": "Deluxe King Room",
                        "description": "Spacious room with a king-size bed and city view.",
                        "max_guests": 2,
                        "size_sqft": 350,
                        "bed_type": "King",
                        "price_per_night": 200,
                        "currency": "USD",
                        "free_cancellation": True,
                        "breakfast_included": False,
                        "images": ["https://example.com/room1_1.jpg"],
                        "amenities": ["Air Conditioning", "TV", "Minibar", "Safe", "Coffee Maker"]
                    },
                    {
                        "id": "room_1_2",
                        "name": "Executive Suite",
                        "description": "Luxurious suite with separate living area and premium amenities.",
                        "max_guests": 3,
                        "size_sqft": 600,
                        "bed_type": "King + Sofa Bed",
                        "price_per_night": 350,
                        "currency": "USD",
                        "free_cancellation": True,
                        "breakfast_included": True,
                        "images": ["https://example.com/suite1_1.jpg"],
                        "amenities": ["Air Conditioning", "TV", "Minibar", "Safe", "Coffee Maker", "Separate Living Area", "Executive Lounge Access"]
                    }
                ],
                "policies": {
                    "check_in": "15:00",
                    "check_out": "12:00",
                    "pets_allowed": True,
                    "pet_fee": 50,
                    "extra_bed_policy": "Extra bed available for $30 per night",
                    "cancellation_policy": "Free cancellation up to 3 days before check-in. After that, the first night will be charged."
                },
                "reviews": [
                    {
                        "author": "Traveler123",
                        "rating": 5,
                        "date": "2023-10-15",
                        "title": "Excellent stay!",
                        "text": "The hotel was amazing! Great location, friendly staff, and beautiful rooms.",
                        "trip_type": "couple"
                    },
                    {
                        "author": "BusinessTraveler",
                        "rating": 4,
                        "date": "2023-10-10",
                        "title": "Great business hotel",
                        "text": "Perfect for business trips. Good WiFi and workspace in the room.",
                        "trip_type": "business"
                    }
                ],
                "average_rating": 4.7,
                "review_count": 128,
                "distance_from_center_km": 0.5,
                "nearest_landmarks": [
                    {"name": "City Center", "distance_km": 0.5},
                    {"name": "Main Train Station", "distance_km": 1.2},
                    {"name": "Shopping District", "distance_km": 0.8}
                ]
            },
            {
                "id": "hotel_2",
                "name": "Seaside Resort & Spa",
                "star_rating": 4.8,
                "address": "456 Ocean View Drive, Beach City, Country",
                "location": {
                    "lat": 34.0522,
                    "lng": -118.2437,
                    "city": "Los Angeles",
                    "country": "United States"
                },
                "description": "A beautiful beachfront resort offering stunning ocean views and world-class spa facilities.",
                "amenities": [
                    "Free WiFi", "Swimming Pool", "Spa", "Restaurant", "Bar", "Beach Access",
                    "Fitness Center", "Room Service", "24-Hour Front Desk", "Concierge"
                ],
                "images": [
                    "https://example.com/resort1_1.jpg",
                    "https://example.com/resort1_2.jpg"
                ],
                "room_types": [
                    {
                        "id": "room_2_1",
                        "name": "Ocean View Room",
                        "description": "Comfortable room with a partial ocean view.",
                        "max_guests": 2,
                        "size_sqft": 400,
                        "bed_type": "Queen",
                        "price_per_night": 280,
                        "currency": "USD",
                        "free_cancellation": True,
                        "breakfast_included": False,
                        "images": ["https://example.com/room2_1.jpg"],
                        "amenities": ["Air Conditioning", "TV", "Minibar", "Safe", "Coffee Maker", "Balcony"]
                    },
                    {
                        "id": "room_2_2",
                        "name": "Beachfront Suite",
                        "description": "Luxurious suite with direct beach access and private terrace.",
                        "max_guests": 4,
                        "size_sqft": 800,
                        "bed_type": "King + Queen Sofa Bed",
                        "price_per_night": 550,
                        "currency": "USD",
                        "free_cancellation": True,
                        "breakfast_included": True,
                        "images": ["https://example.com/suite2_1.jpg"],
                        "amenities": ["Air Conditioning", "TV", "Minibar", "Safe", "Coffee Maker", "Private Terrace", "Beach Access"]
                    }
                ],
                "policies": {
                    "check_in": "16:00",
                    "check_out": "11:00",
                    "pets_allowed": False,
                    "extra_bed_policy": "Extra bed available for $40 per night",
                    "cancellation_policy": "Free cancellation up to 7 days before check-in. After that, the first night will be charged."
                },
                "reviews": [
                    {
                        "author": "BeachLover",
                        "rating": 5,
                        "date": "2023-09-25",
                        "title": "Paradise found!",
                        "text": "Absolutely stunning location right on the beach. The staff went above and beyond to make our stay special.",
                        "trip_type": "family"
                    },
                    {
                        "author": "Honeymooner",
                        "rating": 5,
                        "date": "2023-10-05",
                        "title": "Perfect honeymoon spot",
                        "text": "The beachfront suite was worth every penny. Waking up to the sound of waves was magical.",
                        "trip_type": "couple"
                    }
                ],
                "average_rating": 4.9,
                "review_count": 215,
                "distance_from_center_km": 5.0,
                "beach_distance_meters": 50,
                "nearest_landmarks": [
                    {"name": "Beach Access", "distance_km": 0.05},
                    {"name": "Downtown", "distance_km": 5.0},
                    {"name": "Golf Course", "distance_km": 2.5}
                ]
            }
        ]
    
    async def _mock_search_hotels(
        self,
        location: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
        rooms: int = 1,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        stars: List[int] = [],
        amenities: List[str] = [],
        free_cancellation: bool = False,
        limit: int = 10,
    ) -> List[Dict]:
        """Mock implementation of hotel search."""
        # In a real implementation, this would call the hotels.search tool
        # For now, we'll filter our mock data based on the search criteria
        
        filtered_hotels = []
        
        for hotel in self.mock_hotels:
            # Apply filters
            if stars and int(hotel["star_rating"]) not in stars:
                continue
                
            if price_min is not None or price_max is not None:
                min_price = min(room["price_per_night"] for room in hotel["room_types"])
                if price_min is not None and min_price < price_min:
                    continue
                if price_max is not None and min_price > price_max:
                    continue
            
            if amenities:
                hotel_amenities = set(amenity.lower() for amenity in hotel["amenities"])
                required_amenities = set(amenity.lower() for amenity in amenities)
                if not required_amenities.issubset(hotel_amenities):
                    continue
            
            if free_cancellation:
                if not all(room["free_cancellation"] for room in hotel["room_types"]):
                    continue
            
            # If we get here, the hotel matches all criteria
            filtered_hotels.append(hotel)
            
            # Stop if we've reached the limit
            if len(filtered_hotels) >= limit:
                break
        
        # Format the results
        results = []
        for hotel in filtered_hotels:
            # Find the cheapest available room
            cheapest_room = min(hotel["room_types"], key=lambda x: x["price_per_night"])
            
            results.append({
                "hotel_id": hotel["id"],
                "name": hotel["name"],
                "star_rating": hotel["star_rating"],
                "address": hotel["address"],
                "location": hotel["location"],
                "description": hotel["description"],
                "image_url": hotel["images"][0] if hotel["images"] else None,
                "price_per_night": cheapest_room["price_per_night"],
                "currency": cheapest_room["currency"],
                "free_cancellation": cheapest_room["free_cancellation"],
                "breakfast_included": cheapest_room.get("breakfast_included", False),
                "amenities": hotel["amenities"][:5],  # Show top 5 amenities
                "average_rating": hotel["average_rating"],
                "review_count": hotel["review_count"],
            })
        
        return results
