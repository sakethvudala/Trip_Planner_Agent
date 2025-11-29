"""Mock implementation of review-related tools for the Trip Planner."""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger

from app.schemas import GetReviewsInput
from app.framework.adk_runtime import ToolDefinition, ToolResult

# Mock review data
MOCK_REVIEWS = {
    "hotel_1": [
        {
            "id": "review_1",
            "author": "Traveler123",
            "rating": 5,
            "title": "Exceptional Service",
            "text": "The staff went above and beyond to make our stay memorable. The rooms were spacious and the food was delicious.",
            "date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "trip_type": "couple",
            "stay_date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m"),
            "response": {
                "text": "Thank you for your kind words! We're delighted you enjoyed your stay with us.",
                "date": (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d"),
                "manager": "Hotel Manager"
            }
        },
        {
            "id": "review_2",
            "author": "BusinessTraveler",
            "rating": 4,
            "title": "Great for business stays",
            "text": "Excellent business facilities and convenient location. The rooms are comfortable and the internet is fast.",
            "date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"),
            "trip_type": "business",
            "stay_date": (datetime.now() - timedelta(days=60)).strftime("%Y-%m"),
        },
        {
            "id": "review_3",
            "author": "FamilyOfFour",
            "rating": 5,
            "title": "Perfect family vacation",
            "text": "The kids loved the pool and the staff was very accommodating to our family's needs. The family suite was spacious and clean.",
            "date": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
            "trip_type": "family",
            "stay_date": (datetime.now() - timedelta(days=75)).strftime("%Y-%m"),
            "response": {
                "text": "We're so happy your family enjoyed their stay! We look forward to welcoming you back.",
                "date": (datetime.now() - timedelta(days=58)).strftime("%Y-%m-%d"),
                "manager": "Guest Relations"
            }
        },
        {
            "id": "review_4",
            "author": "SoloExplorer",
            "rating": 3,
            "title": "Good but could be better",
            "text": "The location is great and the room was clean, but the walls were quite thin. I could hear my neighbors clearly.",
            "date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
            "trip_type": "solo",
            "stay_date": (datetime.now() - timedelta(days=20)).strftime("%Y-%m"),
        },
        {
            "id": "review_5",
            "author": "LuxuryLover",
            "rating": 5,
            "title": "Absolutely luxurious!",
            "text": "From the moment we arrived, we were treated like royalty. The spa was incredible and the dining options were top-notch.",
            "date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "trip_type": "couple",
            "stay_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m"),
            "response": {
                "text": "Thank you for your wonderful review! We're thrilled you enjoyed the luxury experience we aim to provide.",
                "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
                "manager": "Guest Experience Manager"
            }
        }
    ],
    "hotel_2": [
        {
            "id": "review_6",
            "author": "FoodieTraveler",
            "rating": 4,
            "title": "Amazing dining options",
            "text": "The restaurants in this hotel are exceptional. The breakfast buffet had so many options and everything was delicious.",
            "date": (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d"),
            "trip_type": "business",
            "stay_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m"),
        },
        {
            "id": "review_7",
            "author": "WeekendGetaway",
            "rating": 5,
            "title": "Perfect weekend stay",
            "text": "We had a wonderful weekend here. The room was comfortable, the staff was friendly, and the location was perfect for exploring the city.",
            "date": (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d"),
            "trip_type": "couple",
            "stay_date": (datetime.now() - timedelta(days=40)).strftime("%Y-%m"),
        }
    ],
    "hotel_3": [
        {
            "id": "review_8",
            "author": "BusinessPro",
            "rating": 5,
            "title": "Top-notch business facilities",
            "text": "The business center and meeting rooms are excellent. High-speed internet throughout the property made working easy.",
            "date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            "trip_type": "business",
            "stay_date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m"),
        },
        {
            "id": "review_9",
            "author": "LuxurySeeker",
            "rating": 4,
            "title": "Luxurious but pricey",
            "text": "The hotel is beautiful and the service is impeccable, but be prepared to pay premium prices for everything.",
            "date": (datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d"),
            "trip_type": "couple",
            "stay_date": (datetime.now() - timedelta(days=35)).strftime("%Y-%m"),
        },
        {
            "id": "review_10",
            "author": "SpaEnthusiast",
            "rating": 5,
            "title": "Best spa experience ever!",
            "text": "The spa treatments were absolutely divine. The therapists were skilled and the facilities were spotless.",
            "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "trip_type": "solo",
            "stay_date": (datetime.now() - timedelta(days=8)).strftime("%Y-%m"),
            "response": {
                "text": "We're thrilled you enjoyed our spa! Our therapists will be delighted to hear your feedback.",
                "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
                "manager": "Spa Manager"
            }
        }
    ]
}

# Common review aspects and their sentiment scores
REVIEW_ASPECTS = {
    "staff": {
        "positive": ["friendly", "helpful", "attentive", "professional", "welcoming", "accommodating"],
        "negative": ["rude", "unhelpful", "slow", "inattentive", "unprofessional"]
    },
    "room": {
        "positive": ["clean", "spacious", "comfortable", "modern", "well-appointed", "quiet"],
        "negative": ["dirty", "small", "uncomfortable", "outdated", "noisy"]
    },
    "food": {
        "positive": ["delicious", "tasty", "fresh", "varied", "well-prepared"],
        "negative": ["bland", "overpriced", "limited", "cold", "undercooked"]
    },
    "location": {
        "positive": ["convenient", "central", "accessible", "picturesque", "vibrant"],
        "negative": ["remote", "inconvenient", "noisy", "unsafe", "hard to find"]
    },
    "amenities": {
        "positive": ["well-maintained", "modern", "plentiful", "high-quality", "accessible"],
        "negative": ["limited", "outdated", "broken", "dirty", "crowded"]
    },
    "value": {
        "positive": ["affordable", "worth it", "reasonable", "fair", "budget-friendly"],
        "negative": ["overpriced", "expensive", "not worth it", "rip-off"]
    }
}

def analyze_sentiment(text: str) -> dict:
    """Perform simple sentiment analysis on review text."""
    text_lower = text.lower()
    
    # Initialize aspect scores
    aspect_scores = {aspect: 0 for aspect in REVIEW_ASPECTS}
    
    # Check for positive and negative mentions of each aspect
    for aspect, terms in REVIEW_ASPECTS.items():
        # Check positive terms
        for term in terms["positive"]:
            if term in text_lower:
                aspect_scores[aspect] += 1
                
        # Check negative terms
        for term in terms["negative"]:
            if term in text_lower:
                aspect_scores[aspect] -= 1
    
    # Calculate overall sentiment
    total_score = sum(aspect_scores.values())
    if total_score > 0:
        sentiment = "positive"
    elif total_score < 0:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Get top aspects mentioned
    mentioned_aspects = {k: v for k, v in aspect_scores.items() if v != 0}
    sorted_aspects = sorted(mentioned_aspects.items(), key=lambda x: abs(x[1]), reverse=True)
    
    return {
        "sentiment": sentiment,
        "score": total_score,
        "aspects": {k: "positive" if v > 0 else "negative" for k, v in sorted_aspects[:3]}
    }

async def get_reviews(payload: Dict, context: Dict) -> ToolResult:
    """Mock implementation of the get_reviews tool."""
    try:
        # Parse and validate input
        input_data = GetReviewsInput(**payload)
        
        # Log the request
        logger.info(
            f"Fetching reviews for place_id: {input_data.place_id}",
            correlation_id=context.get("correlation_id"),
            caller_agent=context.get("caller_agent"),
            tool_name="get_reviews",
            limit=input_data.limit,
        )
        
        # Get reviews for the place
        reviews = MOCK_REVIEWS.get(input_data.place_id, [])
        
        # Apply limit
        reviews = reviews[:input_data.limit]
        
        # Add sentiment analysis to each review
        for review in reviews:
            analysis = analyze_sentiment(review["text"])
            review["sentiment"] = analysis
        
        # Calculate overall rating stats if we have reviews
        if reviews:
            ratings = [r["rating"] for r in reviews]
            rating_stats = {
                "average_rating": sum(ratings) / len(ratings),
                "total_reviews": len(ratings),
                "rating_distribution": {
                    "5_star": len([r for r in ratings if r == 5]),
                    "4_star": len([r for r in ratings if r == 4]),
                    "3_star": len([r for r in ratings if r == 3]),
                    "2_star": len([r for r in ratings if r == 2]),
                    "1_star": len([r for r in ratings if r == 1]),
                }
            }
            
            # Get common aspects from all reviews
            all_aspects = {}
            for review in reviews:
                for aspect, sentiment in review["sentiment"]["aspects"].items():
                    if aspect not in all_aspects:
                        all_aspects[aspect] = {"positive": 0, "negative": 0}
                    all_aspects[aspect][sentiment] += 1
            
            # Sort aspects by total mentions
            sorted_aspects = sorted(
                all_aspects.items(), 
                key=lambda x: sum(x[1].values()), 
                reverse=True
            )
            
            rating_stats["common_aspects"] = [
                {
                    "aspect": aspect,
                    "positive_mentions": counts["positive"],
                    "negative_mentions": counts["negative"],
                    "sentiment": "positive" if counts["positive"] > counts["negative"] else 
                                "negative" if counts["negative"] > counts["positive"] else 
                                "neutral"
                }
                for aspect, counts in sorted_aspects[:5]  # Top 5 aspects
            ]
        else:
            rating_stats = None
        
        # Return the results
        return ToolResult(
            success=True,
            data={
                "reviews": reviews,
                "count": len(reviews),
                "place_id": input_data.place_id,
                "rating_stats": rating_stats,
            }
        )
        
    except Exception as e:
        logger.error(
            f"Error in get_reviews: {str(e)}",
            correlation_id=context.get("correlation_id"),
            caller_agent=context.get("caller_agent"),
            tool_name="get_reviews",
            error=str(e),
            exc_info=True,
        )
        return ToolResult(
            success=False,
            error=f"Failed to fetch reviews: {str(e)}",
        )

# Tool definitions
TOOLS = [
    ToolDefinition(
        name="reviews.get",
        description="Get reviews for a specific place (hotel, restaurant, etc.) with sentiment analysis",
        input_schema=GetReviewsInput.schema(),
        output_schema={
            "type": "object",
            "properties": {
                "reviews": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "author": {"type": "string"},
                            "rating": {"type": "number"},
                            "title": {"type": "string"},
                            "text": {"type": "string"},
                            "date": {"type": "string"},
                            "trip_type": {"type": "string"},
                            "stay_date": {"type": "string"},
                            "response": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "date": {"type": "string"},
                                    "manager": {"type": "string"}
                                }
                            },
                            "sentiment": {
                                "type": "object",
                                "properties": {
                                    "sentiment": {"type": "string"},
                                    "score": {"type": "number"},
                                    "aspects": {"type": "object"}
                                }
                            }
                        },
                    },
                },
                "count": {"type": "integer"},
                "place_id": {"type": "string"},
                "rating_stats": {
                    "type": "object",
                    "properties": {
                        "average_rating": {"type": "number"},
                        "total_reviews": {"type": "integer"},
                        "rating_distribution": {
                            "type": "object",
                            "properties": {
                                "5_star": {"type": "integer"},
                                "4_star": {"type": "integer"},
                                "3_star": {"type": "integer"},
                                "2_star": {"type": "integer"},
                                "1_star": {"type": "integer"}
                            }
                        },
                        "common_aspects": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "aspect": {"type": "string"},
                                    "positive_mentions": {"type": "integer"},
                                    "negative_mentions": {"type": "integer"},
                                    "sentiment": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            },
        },
        handler=get_reviews,
    )
]
