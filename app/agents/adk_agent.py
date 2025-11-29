"""
Google ADK Agent implementation with a safe fallback.
If Google ADK libraries are unavailable, we provide a minimal fallback agent
so the server can start and the chat endpoint remains functional.
"""
from typing import Any, Dict, Optional

from app.framework.adk_runtime import ADKRuntime
import os
from app.logging_config import get_logger

logger = get_logger(__name__)

# Try to import Google ADK; fall back if not available. Also allow explicit disable via env.
_ADK_AVAILABLE = os.getenv("ENABLE_ADK", "false").lower() == "true"
try:
    if _ADK_AVAILABLE:
        from google.adk import Agent as _AdkAgent, Runner  # type: ignore
        from google.adk.sessions import InMemorySessionService  # type: ignore
        from google.genai import types  # type: ignore
except Exception as _e:  # pragma: no cover - environment-dependent
    _ADK_AVAILABLE = False
    logger.warning("Google ADK not available, using fallback agent", error=str(_e))


if _ADK_AVAILABLE:
    class TripPlannerAgent(_AdkAgent):
        """Main agent class for the Trip Planner using Google ADK."""

        def __init__(self, runtime: ADKRuntime):
            super().__init__(name="trip_planner_agent")
            # Avoid Pydantic BaseModel attribute restrictions
            object.__setattr__(self, "runtime", runtime)
            object.__setattr__(self, "session_service", InMemorySessionService())

        async def process_message(
            self,
            user_message: str,
            user_id: str = "anonymous",
            session_id: Optional[str] = None,
            **kwargs,
        ) -> Dict[str, Any]:
            try:
                user_msg = types.Content(role="user", parts=[types.Part(text=user_message)])
                runner = Runner(agent=self, session_service=self.session_service)
                response_text = "No response generated"
                for event in runner.run(
                    user_id=user_id,
                    session_id=session_id or str(id(self)),
                    new_message=user_msg,
                ):
                    if event.is_final_response() and event.content and event.content.parts:
                        response_text = event.content.parts[0].text
                        break
                return {
                    "response": response_text,
                    "session_id": session_id or str(id(self)),
                    "status": "success",
                }
            except Exception as e:  # pragma: no cover
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                return {
                    "response": "Sorry, I encountered an error processing your request.",
                    "error": str(e),
                    "status": "error",
                }
else:
    class TripPlannerAgent:
        """Fallback agent when Google ADK is unavailable.

        Provides a minimal interface compatible with the server code.
        """

        def __init__(self, runtime: ADKRuntime):
            self.runtime = runtime

        async def process_message(
            self,
            user_message: str,
            user_id: str = "anonymous",
            session_id: Optional[str] = None,
            **kwargs,
        ) -> Dict[str, Any]:
            """Generate a simple day-wise itinerary in the required JSON format.

            Output schema:
            {
              "response": "<human readable itinerary text>",
              "session_id": "<copy of session_id or 'unknown'>",
              "status": "success"
            }
            """
            import re

            text = (user_message or "").strip()
            sid = session_id or "unknown"

            # Heuristics to extract destination and days
            # Find number of days
            days = 3
            m = re.search(r"(\d+)\s*days?", text, flags=re.IGNORECASE)
            if m:
                try:
                    days = max(1, min(10, int(m.group(1))))
                except Exception:
                    days = 3

            # Destination extraction: take last word(s) around 'to <dest>' or after 'trip to'
            dest = "your destination"
            m = re.search(r"to\s+([a-zA-Z\s,&-]+)", text, flags=re.IGNORECASE)
            if m:
                dest = m.group(1).strip().strip(",.")
            else:
                # fallback: first place-like token
                tokens = re.findall(r"[A-Za-z][A-Za-z\-]+", text)
                if tokens:
                    dest = tokens[-1]

            # Build a naive itinerary
            lines = []
            lines.append(f"Trip Plan: {dest.title()} ({days} day{'s' if days != 1 else ''})")
            lines.append("")
            for d in range(1, days + 1):
                lines.append(f"Day {d}:")
                lines.append(f"  Morning: Explore a popular landmark in {dest.title()}.")
                lines.append(f"  Afternoon: Visit a museum/market; enjoy local snacks.")
                lines.append(f"  Evening: Walk around a scenic area; dinner at a recommended spot.")
                lines.append("")

            # Add stay and food suggestions
            lines.append("Stay Suggestions (choose 1):")
            lines.append(f"  - Mid-range hotel near city center in {dest.title()}")
            lines.append(f"  - Budget stay/hostel in {dest.title()} (clean, well-reviewed)")
            lines.append("")
            lines.append("Food Suggestions:")
            lines.append(f"  - Try a famous local restaurant serving regional cuisine in {dest.title()}")
            lines.append("  - Street food crawl one evening (hygiene-first)")

            reply = "\n".join(lines)

            return {
                "response": reply,
                "session_id": sid,
                "status": "success",
            }


# Singleton instance of the agent
_agent_instance = None

def get_agent(runtime: Optional[ADKRuntime] = None) -> TripPlannerAgent:
    """Get or create the singleton instance of the TripPlannerAgent."""
    global _agent_instance
    if _agent_instance is None:
        if runtime is None:
            runtime = ADKRuntime()
        _agent_instance = TripPlannerAgent(runtime)
    return _agent_instance
