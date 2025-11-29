"""Pydantic models for the Trip Planner API."""
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union

from pydantic import BaseModel, Field, validator, HttpUrl

# Enums for constrained choices
class BudgetFlexibility(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class AccommodationType(str, Enum):
    HOTEL = "hotel"
    HOSTEL = "hostel"
    APARTMENT = "apartment"
    RESORT = "resort"
    VILLA = "villa"
    BED_AND_BREAKFAST = "bed_and_breakfast"

class TransportationMode(str, Enum):
    WALKING = "walking"
    DRIVING = "driving"
    BICYCLING = "bicycling"
    TRANSIT = "transit"
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    TAXI = "taxi"
    RIDE_SHARING = "ride_sharing"

class POICategory(str, Enum):
    ATTRACTION = "attraction"
    LANDMARK = "landmark"
    RESTAURANT = "restaurant"
    SHOPPING = "shopping"
    NIGHTLIFE = "nightlife"
    OUTDOOR = "outdoor"
    CULTURAL = "cultural"
    HISTORICAL = "historical"
    RELIGIOUS = "religious"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    ADVENTURE = "adventure"
    LEISURE = "leisure"
    EDUCATION = "education"
    OTHER = "other"

# Core POI model used by LocationAgent and others
class POI(BaseModel):
    """Point of Interest with optional rich metadata."""
    id: Optional[str] = Field(None, description="Unique identifier (e.g., place_id)")
    name: str
    category: POICategory
    address: Optional[str] = None
    location: Optional[Dict[str, float]] = Field(
        default=None,
        description="Coordinates as {'lat': float, 'lng': float}"
    )
    rating: Optional[float] = Field(None, ge=0, le=5)
    user_ratings_total: Optional[int] = Field(None, ge=0)
    price_level: Optional[int] = Field(None, ge=0, le=4)
    photo_url: Optional[HttpUrl] = None
    opening_hours: Optional[List[str]] = None
    is_open_now: Optional[bool] = None
    website: Optional[HttpUrl] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    reviews: Optional[List[Dict[str, Any]]] = None

# Request Models
class LocationPreference(BaseModel):
    """User's location preferences for trip planning."""
    base_city: str = Field(..., description="The main city or destination")
    country: Optional[str] = Field(None, description="Country of the destination")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    interests: List[str] = Field(
        default_factory=list,
        description="List of interests (e.g., beaches, museums, hiking)"
    )
    
    @validator('end_date')
    def validate_dates(cls, end_date, values):
        if 'start_date' in values and end_date < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return end_date

class BudgetStatus(str, Enum):
    """Status of the budget tracking."""
    ON_TRACK = "on_track"
    WARNING = "warning"
    EXCEEDED = "exceeded"
    UNDER_BUDGET = "under_budget"

class BudgetCategory(str, Enum):
    """Categories for budget tracking."""
    ACCOMMODATION = "accommodation"
    FOOD = "food"
    TRANSPORTATION = "transportation"
    ACTIVITIES = "activities"
    SHOPPING = "shopping"
    SIGHTSEEING = "sightseeing"
    ENTERTAINMENT = "entertainment"
    EMERGENCIES = "emergencies"
    OTHER = "other"

class BudgetItem(BaseModel):
    """An individual budget line item."""
    id: str
    category: BudgetCategory
    description: str
    amount: float = Field(..., ge=0)
    currency: str = "USD"
    date: Optional[date] = None
    is_estimated: bool = True
    status: BudgetStatus = BudgetStatus.ON_TRACK
    notes: Optional[str] = None

class BudgetPreference(BaseModel):
    """User's budget preferences for the trip."""
    total_budget: float = Field(..., ge=0, description="Total budget for the trip")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code (e.g., USD, EUR)")
    flexibility: BudgetFlexibility = Field(
        default=BudgetFlexibility.MEDIUM,
        description="How flexible the budget is (low, medium, high)"
    )
    breakdown: Optional[Dict[BudgetCategory, float]] = Field(
        default_factory=dict,
        description="Budget allocation by category"
    )
    items: List[BudgetItem] = Field(
        default_factory=list,
        description="Detailed budget items"
    )

class StayPreference(BaseModel):
    """User's accommodation preferences."""
    accommodation_type: AccommodationType = Field(
        default=AccommodationType.HOTEL,
        description="Type of accommodation preferred"
    )
    min_rating: float = Field(
        default=3.0,
        ge=0,
        le=5.0,
        description="Minimum acceptable rating (0-5)"
    )
    max_price_per_night: Optional[float] = Field(
        None,
        ge=0,
        description="Maximum price per night in the specified currency"
    )
    preferred_areas: Optional[List[str]] = Field(
        None,
        description="List of preferred areas/neighborhoods"
    )
    amenities: List[str] = Field(
        default_factory=list,
        description="List of desired amenities (e.g., wifi, pool, gym)"
    )

class TransportationPreference(BaseModel):
    """User's transportation preferences."""
    preferred_modes: List[TransportationMode] = Field(
        default_factory=lambda: [TransportationMode.WALKING, TransportationMode.TRANSIT],
        description="Preferred modes of transportation"
    )
    max_walking_distance_meters: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Maximum walking distance in meters"
    )
    max_driving_time_minutes: int = Field(
        default=60,
        ge=5,
        le=240,
        description="Maximum driving time in minutes between locations"
    )

class TripRequest(BaseModel):
    """Complete trip planning request from the user."""
    location: LocationPreference
    budget: BudgetPreference
    stay: StayPreference
    transportation: Optional[TransportationPreference] = None
    travelers: int = Field(1, ge=1, description="Number of travelers")
    notes: Optional[str] = Field(
        None,
        description="Additional notes or special requirements"
    )
    preferences: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional preferences in key-value format"
    )

# Internal Models
class GeoPoint(BaseModel):
    """Geographical coordinates (latitude, longitude)."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")

class Address(BaseModel):
    """Structured address information."""
    street: Optional[str] = None
    city: str
    state: Optional[str] = None
    country: str
    postal_code: Optional[str] = None
    formatted: Optional[str] = None
    coordinates: Optional[GeoPoint] = None

class TimeRange(BaseModel):
    """A time range with start and end times."""
    start: datetime
    end: datetime
    
    @validator('end')
    def validate_times(cls, end, values):
        if 'start' in values and end < values['start']:
            raise ValueError('End time must be after start time')
        return end

class Activity(BaseModel):
    """An activity that can be part of a trip."""
    id: str
    name: str
    category: POICategory
    description: Optional[str] = None
    duration_minutes: int = Field(60, ge=1, description="Duration in minutes")
    cost: float = Field(0, ge=0, description="Cost per person in the trip's currency")
    address: Optional[Address] = None
    booking_url: Optional[HttpUrl] = None
    is_booked: bool = False
    booking_reference: Optional[str] = None
    notes: Optional[str] = None

class Stop(BaseModel):
    """A point of interest or stop in the itinerary."""
    id: str = Field(..., description="Unique identifier for the stop")
    name: str = Field(..., description="Name of the place")
    category: POICategory = Field(..., description="Category of the place")
    address: Optional[Address] = None
    coordinates: Optional[GeoPoint] = None
    description: Optional[str] = None
    estimated_duration_minutes: int = Field(
        default=60,
        ge=5,
        le=480,
        description="Estimated time to spend at this location in minutes"
    )
    cost: Optional[float] = Field(
        None,
        ge=0,
        description="Estimated cost per person in the trip's currency"
    )
    booking_url: Optional[HttpUrl] = None
    image_url: Optional[HttpUrl] = None
    opening_hours: Optional[Dict[str, List[TimeRange]]] = None
    tips: Optional[List[str]] = None

class TransportationOption(BaseModel):
    """A transportation option between two points."""
    mode: TransportationMode
    duration_minutes: int = Field(..., ge=0, description="Total duration in minutes")
    distance_meters: Optional[int] = Field(None, ge=0, description="Distance in meters")
    cost: Optional[float] = Field(None, ge=0, description="Estimated cost in the trip's currency")
    provider: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional provider-specific details")

class RouteLeg(TransportationOption):
    """A segment of a route between two stops."""
    from_stop_id: str
    to_stop_id: str
    mode: TransportationMode
    instructions: Optional[str] = None
    waypoints: Optional[List[Dict[str, float]]] = None

class Route(BaseModel):
    """A complete route consisting of multiple legs."""
    legs: List[RouteLeg]
    total_duration_minutes: float = Field(..., ge=0)
    total_distance_meters: float = Field(..., ge=0)
    total_cost: Optional[float] = Field(None, ge=0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    summary: Optional[str] = None

class DayPlan(BaseModel):
    """Plan for a single day of the trip."""
    date: date
    stops: List[Stop] = Field(default_factory=list)
    transportation: List[RouteLeg] = Field(default_factory=list)
    notes: Optional[str] = None
    
    @property
    def estimated_total_duration_minutes(self) -> int:
        """Calculate total estimated duration including travel time."""
        stop_duration = sum(stop.estimated_duration_minutes for stop in self.stops)
        travel_duration = sum(leg.duration_minutes for leg in self.transportation)
        return stop_duration + travel_duration
    
    @property
    def estimated_total_cost(self) -> float:
        """Calculate total estimated cost for the day."""
        stop_costs = sum(stop.cost for stop in self.stops if stop.cost is not None)
        travel_costs = sum(leg.cost for leg in self.transportation if leg.cost is not None)
        return stop_costs + travel_costs

class HotelOption(BaseModel):
    """Accommodation option for the trip."""
    id: str
    name: str
    type: AccommodationType
    address: Address
    coordinates: GeoPoint
    rating: float = Field(..., ge=0, le=5)
    review_count: int = Field(..., ge=0)
    price_per_night: float = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    amenities: List[str] = Field(default_factory=list)
    images: List[HttpUrl] = Field(default_factory=list)
    booking_url: Optional[HttpUrl] = None
    summary: Optional[str] = None
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    distance_from_center_km: Optional[float] = Field(None, ge=0)

class TripPlan(BaseModel):
    """Complete trip plan with all details."""
    destination: str
    country: str
    start_date: date
    end_date: date
    days: List[DayPlan] = Field(default_factory=list)
    hotels: List[HotelOption] = Field(default_factory=list)
    recommended_hotel: Optional[HotelOption] = None
    estimated_total_cost: float = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    budget_remaining: Optional[float] = None
    budget_status: Optional[str] = None
    weather_forecast: Optional[Dict[date, Dict[str, Any]]] = None
    packing_suggestions: Optional[List[str]] = None
    local_tips: Optional[List[str]] = None
    emergency_contacts: Optional[Dict[str, str]] = None

# Response Models
class TripResponse(BaseModel):
    """API response for a trip planning request."""
    success: bool = True
    plan: TripPlan
    correlation_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    correlation_id: str
    details: Optional[Dict[str, Any]] = None

# ---------------------------------------------------------------------
# Placeholder models to satisfy StayAgent and related imports
# ---------------------------------------------------------------------

class RoomType(str, Enum):
    STANDARD = "standard"
    DELUXE = "deluxe"
    SUITE = "suite"

class Amenity(str, Enum):
    WIFI = "wifi"
    POOL = "pool"
    GYM = "gym"
    PARKING = "parking"

class Location(BaseModel):
    city: str
    country: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None

class PriceRange(BaseModel):
    min_price: float
    max_price: float
    currency: str = "USD"

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class CancellationPolicy(BaseModel):
    free_cancellation_until: Optional[str] = None
    cancellation_fee_after: Optional[str] = None

class Review(BaseModel):
    author: str
    rating: float
    comment: Optional[str] = None
    date: Optional[datetime] = None

class Accommodation(BaseModel):
    id: str
    name: str
    type: AccommodationType = AccommodationType.HOTEL
    location: Location
    rating: Optional[float] = None
    price_per_night: Optional[float] = None
    currency: str = "USD"
    amenities: List[Amenity] = Field(default_factory=list)

# Tool-specific Models
class SearchPlacesInput(BaseModel):
    """Input for the search_places tool."""
    query: str = Field(..., description="Search query")
    location: Optional[str] = Field(None, description="Location to search around")
    radius: Optional[int] = Field(5000, ge=100, le=50000, description="Search radius in meters")
    category: Optional[POICategory] = None
    limit: int = Field(5, ge=1, le=20, description="Maximum number of results")

class SearchHotelsInput(BaseModel):
    """Input for the search_hotels tool."""
    location: str
    check_in: date
    check_out: date
    guests: int = Field(2, ge=1, le=10)
    min_rating: float = Field(3.0, ge=0, le=5.0)
    max_price: Optional[float] = None
    amenities: Optional[List[str]] = None

class GetReviewsInput(BaseModel):
    """Input for the get_reviews tool."""
    place_id: str
    limit: int = Field(5, ge=1, le=20)

class GetDistanceMatrixInput(BaseModel):
    """Input for the distance_matrix tool."""
    origins: List[GeoPoint]
    destinations: List[GeoPoint]
    mode: TransportationMode = TransportationMode.DRIVING
