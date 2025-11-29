"""
Main server entry point for the Trip Planner Agent.
"""
import os
import json
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import logging
import uuid
from pathlib import Path

"""LangWatch (optional) instrumentation setup.
If the package or API key is missing, we fall back to no-op to avoid crashes.
"""
try:
    import langwatch  # type: ignore
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor  # type: ignore
    _LW_IMPORTED = True
except Exception:
    langwatch = None  # type: ignore
    GoogleADKInstrumentor = None  # type: ignore
    _LW_IMPORTED = False

LANGWATCH_API_KEY = os.getenv("LANGWATCH_API_KEY")

class _NoopLangwatch:
    def span(self, *_args, **_kwargs):
        def decorator(func):
            return func
        return decorator
    def trace(self, *_args, **_kwargs):
        def decorator(func):
            return func
        return decorator
    def get_current_trace(self):
        return None
    class middleware:  # noqa: N801 - mimic structure
        class FastAPIMiddleware:  # placeholder for middleware type
            pass

if _LW_IMPORTED and LANGWATCH_API_KEY:
    # Safe setup when API key is available
    try:
        langwatch.setup(
            instrumentors=[GoogleADKInstrumentor()],
            api_key=LANGWATCH_API_KEY,
        )
    except Exception:
        # Fall back to no-op if setup fails for any reason
        langwatch = _NoopLangwatch()  # type: ignore
else:
    # No package or no API key -> use no-op
    langwatch = _NoopLangwatch()  # type: ignore

# Import agents
from app.agents.adk_agent import get_agent
from app.agents.trip_super_agent import TripSuperAgent

# Import settings and utilities
from app.config import get_settings
from app.logging_config import get_logger

# Load settings instance
settings = get_settings()

# Initialize logger
logger = get_logger("server")

# Initialize agents
agent = get_agent()  # ADK (fallback) agent
try:
    super_agent = TripSuperAgent()
    _SUPER_AGENT_OK = True
except Exception as _e:
    logger.opt(exception=_e).warning("TripSuperAgent initialization failed; falling back to ADK agent")
    super_agent = None
    _SUPER_AGENT_OK = False

# Request and Response Models
class MessageRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    """Deprecated; kept for reference. Chat now returns the agent JSON directly."""
    response: Dict[str, Any]
    response_text: str
    conversation_id: str
    metadata: Dict[str, Any] = {}

async def process_message(
    message: str, 
    user_id: str = "anonymous", 
    session_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Process a user message with tracing and monitoring.
    
    Args:
        message: The user's message
        user_id: ID of the user (default: "anonymous")
        session_id: Optional session ID for conversation history
        **kwargs: Additional arguments to pass to the agent
        
    Returns:
        Dict containing the agent's response and metadata
    """
    # Get current trace for adding metadata (no-op if LangWatch disabled)
    current_trace = langwatch.get_current_trace()
    if current_trace:
        current_trace.update(
            metadata={
                "user_id": user_id,
                "session_id": session_id or str(uuid.uuid4()),
                "agent_name": "trip_planner_agent",
                "environment": os.getenv('ENV', 'development')
            }
        )
    
    try:
        # Process the message with the ADK agent
        response = await agent.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id,
            **kwargs
        )
        
        # Add LangWatch metadata
        if current_trace:
            current_trace.update(
                metadata={
                    "status": "success",
                    "response_length": len(response.get("response", "")),
                    "model": "gemini-2.0-flash"  # Update with your model
                }
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        if current_trace:
            current_trace.record_error(e)
        raise

# Agent metadata
AGENT_METADATA = {
    "id": "trip_planner_agent",
    "name": "trip_planner_agent",
    "display_name": "Trip Planner Agent",
    "description": "AI Powered trip planning agent specializing in itinerary creation, accommodation booking, and travel recommendations.",
    "owner": "YourCompany",
    "contact": {
        "name": "Support",
        "email": "support@yourcompany.com",
        "url": "https://yourcompany.com/support"
    },
    "license_info": {
        "name": "Proprietary",
        "url": "https://yourcompany.com/terms"
    },
    "version": "1.0.0",
    "environment": "Production",
    "runtime": "uvicorn+fastapi",
    "agent_type": "SubAgent",
    "sla_uptime_target": "99.90%",
    "ontology": {
        "domain": "Travel and Hospitality",
        "sub_domain": "Trip Planning and Booking",
        "industry_standards": [
            "ISO 18513:2017 (Tourism Services)",
            "OpenTravel Alliance Standards"
        ],
        "knowledge_base": "Travel Industry Data, Destination Information, Accommodation Database",
        "terminology": {
            "standard": "Travel Industry Terms",
            "version": "v1.0"
        }
    },
    "capabilities": [
        {
            "name": "plan_trip",
            "description": "Plan a complete trip itinerary based on user preferences and constraints",
            "input_schema": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination location"
                    },
                    "dates": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "format": "date"},
                            "end": {"type": "string", "format": "date"}
                        },
                        "required": ["start", "end"]
                    },
                    "preferences": {
                        "type": "object",
                        "properties": {
                            "budget": {"type": "string", "enum": ["budget", "mid-range", "luxury"]},
                            "interests": {"type": "array", "items": {"type": "string"}},
                            "travel_style": {"type": "string", "enum": ["solo", "couple", "family", "business"]}
                        }
                    }
                },
                "required": ["destination", "dates"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "itinerary": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "day": {"type": "number"},
                                "activities": {"type": "array", "items": {"type": "string"}},
                                "accommodation": {"type": "string", "nullable": True},
                                "transportation": {"type": "string", "nullable": True}
                            }
                        }
                    },
                    "total_estimated_cost": {"type": "object"},
                    "recommendations": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    ],
    "skills": {
        "primary_skills": [
            "Itinerary Planning",
            "Accommodation Booking",
            "Travel Recommendations"
        ],
        "secondary_skills": [
            "Budget Management",
            "Local Experience Curation"
        ],
        "skill_level": "advanced"
    },
    "compliance": {
        "data_privacy": {
            "gdpr_compliant": True,
            "ccpa_compliant": True
        },
        "security_measures": [
            "API Key Authentication",
            "TLS 1.3",
            "Data Encryption"
        ]
    },
    "auth_type": "API_KEY",
    "interfaces": ["REST/JSON"],
    "input_channels": ["application/json"],
    "output_channels": ["application/json"],
    "transports_supported": ["https"],
    "change_log": "v1.0.0 - Initial release"
}

# Create FastAPI app with LangWatch middleware
app = FastAPI(
    title=AGENT_METADATA["display_name"],
    description=AGENT_METADATA["description"],
    version=AGENT_METADATA["version"],
    contact=AGENT_METADATA["contact"],
    license_info=AGENT_METADATA["license_info"],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json" if settings.API_PREFIX else "/openapi.json",
    openapi_tags=[
        {
            "name": "chat",
            "description": "Chat with the trip planning agent"
        },
        {
            "name": "conversations",
            "description": "Manage conversations with the agent"
        },
        {
            "name": "system",
            "description": "System endpoints"
        }
    ]
)

# Add LangWatch middleware if available and configured; otherwise skip
if isinstance(langwatch, _NoopLangwatch):
    pass
else:
    app.add_middleware(
        langwatch.middleware.FastAPIMiddleware,  # type: ignore[attr-defined]
        api_key=LANGWATCH_API_KEY,
        metadata={
            "environment": os.getenv('ENV', 'development'),
            "service_name": "trip-planner-agent",
            "service_version": AGENT_METADATA["version"],
        },
    )

# Add CORS middleware (after LangWatch middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: Removed undefined LangWatchTracer; use decorators above if LangWatch is enabled.

# Mount static files
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Static files and service discovery handled at the API level

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add agent metadata to OpenAPI schema
    for key, value in AGENT_METADATA.items():
        if key not in ['title', 'description', 'version', 'contact', 'license_info']:
            openapi_schema["info"][f"x-{key}"] = value
    
    # Set servers section to BASE_URL only. Do not add API prefix here because
    # routes already include it (e.g., "/api/chat"). This avoids /api/api/... in Swagger.
    base_url = settings.BASE_URL.rstrip('/')
    openapi_schema["servers"] = [
        {
            "url": base_url,
            "description": "API Server"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# API Models
class MessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    response: Dict[str, Any]
    conversation_id: str
    metadata: Dict[str, Any]

class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    user_id: Optional[str]
    created_at: str
    updated_at: str
    message_count: int
    messages: List[Dict[str, Any]]

# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    logger.opt(exception=exc).error(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "error_id": error_id
        }
    )

# API Endpoints
@app.post(f"{settings.API_PREFIX}/chat")
async def chat_endpoint(request: MessageRequest, req: Request):
    """
    Chat endpoint that processes user messages and returns agent responses.
    
    - **message**: The user's message
    - **conversation_id**: Optional ID for conversation continuity
    - **user_id**: Optional user identifier
    - **context**: Optional additional context for the agent
    """
    try:
        # Accept message either from body (preferred) or query param fallback
        message = request.message or req.query_params.get("message")
        if not message:
            raise HTTPException(status_code=400, detail={"error": "Missing 'message' in request body"})

        user_id = request.user_id or "anonymous"
        session_id = request.conversation_id

        logger.info(
            "chat_endpoint called",
            user_id=user_id,
            session_id=session_id,
        )

        # Prefer TripSuperAgent (multi-agent orchestration). Fallback to ADK agent.
        if _SUPER_AGENT_OK and super_agent is not None:
            sa_result = await super_agent.process_message(
                message=message,
                conversation_id=session_id,
                user_id=user_id,
                context=request.context or {},
            )
            # The super agent returns {"response": <content>, "metadata": {...}}
            sa_text = sa_result.get("response", "")
            if isinstance(sa_text, (dict, list)):
                sa_text = json.dumps(sa_text, ensure_ascii=False)
            agent_result = {
                "response": sa_text,
                "session_id": session_id or str(uuid.uuid4()),
                "status": "success",
            }
        else:
            # Call fallback ADK agent
            agent_result = await agent.process_message(
                user_message=message,
                user_id=user_id,
                session_id=session_id,
                context=request.context or {},
            )

        # Normalize the agent response to the required schema
        if not isinstance(agent_result, dict):
            agent_result = {
                "response": str(agent_result) if agent_result is not None else "",
                "session_id": session_id or str(uuid.uuid4()),
                "status": "success",
            }

        # Ensure EXACT keys only
        payload = {
            "response": agent_result.get("response", ""),
            "session_id": agent_result.get("session_id") or (session_id or str(uuid.uuid4())),
            "status": agent_result.get("status", "success"),
        }
        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=e).error("Error in chat endpoint")
        # Record the error in LangWatch (no-op if disabled)
        current_trace = langwatch.get_current_trace()
        if current_trace:
            current_trace.record_error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "An error occurred while processing your request",
                "error_id": str(uuid.uuid4())
            }
        )

@app.get(
    f"{settings.API_PREFIX}/conversations/{{conversation_id}}",
    response_model=ConversationHistoryResponse,
    tags=["conversations"]
)
async def get_conversation(
    conversation_id: str,
    limit: int = 20,
    offset: int = 0,
):
    """Get the conversation history for a given conversation ID."""
    try:
        # No persistence layer yet; return an empty conversation stub
        return {
            "conversation_id": conversation_id,
            "user_id": None,
            "created_at": "",
            "updated_at": "",
            "message_count": 0,
            "messages": [],
        }
    except Exception as e:
        logger.opt(exception=e).error("Error getting conversation")
        raise HTTPException(status_code=500, detail="Failed to fetch conversation")

@app.delete(
    f"{settings.API_PREFIX}/conversations/{{conversation_id}}",
    tags=["conversations"]
)
async def end_conversation(conversation_id: str):
    """End a conversation and clean up resources."""
    try:
        # Implementation will be added here
        return {"status": "success", "message": "Conversation ended"}
    except Exception as e:
        logger.error(f"Error ending conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Health Check Endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": AGENT_METADATA["version"],
        "environment": os.getenv("APP_ENV", "development")
    }


@app.get("/.well-known/agent_card.json", include_in_schema=False)
async def get_well_known_agent_card():
    """Standard agent card JSON served from .well-known path."""
    base_url = settings.BASE_URL.rstrip("/")
    return {
        "id": AGENT_METADATA.get("id"),
        "name": AGENT_METADATA.get("name"),
        "display_name": AGENT_METADATA.get("display_name"),
        "description": AGENT_METADATA.get("description"),
        "version": AGENT_METADATA.get("version"),
        "owner": AGENT_METADATA.get("owner"),
        "agent_type": AGENT_METADATA.get("agent_type"),
        "runtime": AGENT_METADATA.get("runtime"),
        "environment": AGENT_METADATA.get("environment"),
        "sla_uptime_target": AGENT_METADATA.get("sla_uptime_target"),

        # Visuals
        "logo_url": settings.AGENT_LOGO_URL,

        # Domain information
        "ontology": AGENT_METADATA.get("ontology"),
        "skills": AGENT_METADATA.get("skills"),
        "capabilities": AGENT_METADATA.get("capabilities"),
        "compliance": AGENT_METADATA.get("compliance"),

        # Contact & legal
        "contact": AGENT_METADATA.get("contact"),
        "legal": {
            "url": AGENT_METADATA.get("license_info", {}).get("url"),
            "name": AGENT_METADATA.get("license_info", {}).get("name"),
            "support_url": getattr(settings, "AGENT_SUPPORT_URL", None),
            "support_email": getattr(settings, "AGENT_SUPPORT_EMAIL", None),
        },

        # Service discovery
        "service": {
            "base_url": base_url,
            "api_prefix": settings.API_PREFIX,
            "transports_supported": AGENT_METADATA.get("transports_supported"),
            "interfaces": AGENT_METADATA.get("interfaces"),
            "input_channels": AGENT_METADATA.get("input_channels"),
            "output_channels": AGENT_METADATA.get("output_channels"),
        },

        # Helpful links
        "links": {
            "chat": f"{settings.API_PREFIX}/chat",
            "health": "/health",
            "openapi": app.openapi_url,
            "docs": "/docs",
            "redoc": "/redoc",
        },
        "change_log": AGENT_METADATA.get("change_log"),
    }


if __name__ == "__main__":
    # Run the FastAPI application
    uvicorn.run(
        "server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.APP_ENV == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
