"""
Trip Super Agent for the Trip Planner system.

This is the main orchestrator that coordinates between all specialized agents
(PlannerAgent, LocationAgent, StayAgent, RouteAgent, BudgetAgent) to provide
a seamless trip planning experience.
"""
from typing import Dict, List, Optional, Any, Union
import asyncio
import functools
import uuid
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.agents.base import AgentCard, AgentMessage, AgentContext
from app.agents.planner_agent import PlannerAgent
from app.agents.location_agent import LocationAgent
from app.agents.stay_agent import StayAgent
from app.agents.route_agent import RouteAgent
from app.agents.budget_agent import BudgetAgent
from app.llm.gemini_client import GeminiClient
from app.framework.adk_runtime import ADKRuntime
from app.config import settings
from app.logging_config import get_logger

# Optional LangWatch instrumentation
try:
    import langwatch
    import os
    
    # Only enable LangWatch if API key is configured
    if 'LANGWATCH_API_KEY' in os.environ:
        try:
            langwatch.utils.initialization.setup(debug=True)
        except:
            pass  # LangWatch setup failed, continue without it
        
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"LangWatch not available: {e}")


class TripSuperAgent:
    """
    The main orchestrator agent that coordinates between all specialized agents.
    
    This agent is responsible for:
    - Initializing and managing all specialized agents
    - Routing messages between agents as needed
    - Maintaining conversation state and context
    - Providing a unified interface for the API layer
    """
    
    def __init__(self):
        """Initialize the TripSuperAgent and all sub-agents."""
        self.logger = get_logger("trip_super_agent")
        
        # Initialize the LLM client
        self.llm_client = GeminiClient()
        
        # Initialize the ADK runtime for tool management
        self.adk_runtime = ADKRuntime()
        
        # Initialize all specialized agents
        self.agents = self._initialize_agents()
        
        # Note: Tools are automatically registered by each agent in their __init__ via BaseAgent._register_tools()
        
        # Store active conversations
        self.conversations: Dict[str, Dict] = {}
    
    def _initialize_agents(self) -> Dict[str, BaseAgent]:
        """Initialize all specialized agents."""
        agents = {}
        
        # Initialize each agent with the LLM client and ADK runtime
        agents["planner"] = PlannerAgent(
            llm_client=self.llm_client,
            adk_runtime=self.adk_runtime,
            logger=self.logger.bind(agent="planner"),
        )
        
        agents["location"] = LocationAgent(
            llm_client=self.llm_client,
            adk_runtime=self.adk_runtime,
            logger=self.logger.bind(agent="location"),
        )
        
        agents["stay"] = StayAgent(
            llm_client=self.llm_client,
            adk_runtime=self.adk_runtime,
            logger=self.logger.bind(agent="stay"),
        )
        
        agents["route"] = RouteAgent(
            llm_client=self.llm_client,
            adk_runtime=self.adk_runtime,
            logger=self.logger.bind(agent="route"),
        )
        
        agents["budget"] = BudgetAgent(
            llm_client=self.llm_client,
            adk_runtime=self.adk_runtime,
            logger=self.logger.bind(agent="budget"),
        )
        
        return agents
    
    async def process_message(
        self,
        message: Union[str, Dict],
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Process an incoming message and return a response.
        
        Args:
            message: The user's message (can be a string or a structured dict)
            conversation_id: Optional conversation ID for multi-turn conversations
            user_id: Optional user ID for personalization
            context: Additional context for the conversation
            
        Returns:
            Dict containing the response and conversation state
        """
        # Generate a new conversation ID if not provided
        if not conversation_id:
            conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        
        # Initialize or update conversation context
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "context": context or {},
                "history": [],
                "state": {},
            }
        
        conversation = self.conversations[conversation_id]
        conversation["updated_at"] = datetime.utcnow().isoformat()
        
        # Create agent context
        agent_context = AgentContext(
            conversation_id=conversation_id,
            user_id=user_id,
            correlation_id=f"{conversation_id}_{len(conversation['history'])}",
            context=conversation["context"],
            state=conversation["state"],
        )
        
        # Create the initial message
        user_message = self._create_agent_message(
            role="user",
            content=message,
            context=agent_context,
        )
        
        # Add to conversation history
        conversation["history"].append({"role": "user", "content": message})
        
        # Start a LangWatch trace
        with langwatch.trace(name="TripSuperAgent.process_message", user_id=user_id) as trace:
            trace.add_input(input={"message": message, "conversation_id": conversation_id})
            
            try:
                max_steps = 10
                current_step = 0
                final_response = None
                
                while current_step < max_steps:
                    current_step += 1
                    self.logger.info(f"Orchestration step {current_step}", conversation_id=conversation_id)
                    
                    # 1. Consult the Planner Agent to decide the next step
                    planner_agent = self.agents["planner"]
                    
                    # Prepare the message for the planner
                    if current_step == 1:
                        planner_msg_content = user_message.content
                    else:
                        # Pass the result of the last step to the planner
                        planner_msg_content = {
                            "instruction": "Continue planning based on the latest context.",
                            "last_step_result": step_response.content if 'step_response' in locals() else None,
                            "last_agent": target_agent_name if 'target_agent_name' in locals() else None
                        }
                        
                    planner_response = await planner_agent.process_message(
                        message=user_message if current_step == 1 else self._create_agent_message(
                            role="user", 
                            content=planner_msg_content, 
                            context=agent_context
                        ),
                        context=agent_context,
                    )
                    
                    # Extract the target agent and action
                    target_agent_name = planner_response.content.get("target_agent")
                    action = planner_response.content.get("action")
                    
                    # If no target agent or action is "finish", we are done
                    if not target_agent_name or action == "finish":
                        final_response = planner_response
                        break
                        
                    if target_agent_name not in self.agents:
                        raise ValueError(f"Invalid target agent: {target_agent_name}")
                    
                    # 2. Execute the step with the target agent
                    target_agent = self.agents[target_agent_name]
                    
                    # Create a message for the target agent
                    agent_message = self._create_agent_message(
                        role="assistant",
                        content={
                            "action": action,
                            **planner_response.content.get("parameters", {})
                        },
                        context=agent_context,
                    )
                    
                    # Process the message
                    step_response = await target_agent.process_message(
                        message=agent_message,
                        context=agent_context,
                    )
                    
                    # Update conversation state with any new context/state from the agent
                    if step_response.context:
                        agent_context.context.update(step_response.context)
                    
                    # Log the step
                    conversation["history"].append({
                        "role": "assistant",
                        "content": step_response.content,
                        "agent": target_agent_name,
                        "action": action,
                        "step": current_step
                    })
                    
                    # Add LangWatch span for this step (if we were doing manual spans, but the agents have their own traces/spans)
                    # We can add an event to the root trace
                    trace.add_event(
                        name=f"step_{current_step}",
                        attributes={
                            "agent": target_agent_name,
                            "action": action,
                            "response": str(step_response.content)[:100]
                        }
                    )

                if not final_response:
                    final_response = self.create_response(
                        content={"status": "error", "message": "Max steps reached without completion."},
                        recipient="user"
                    )

                # Format the final response
                response_data = {
                    "response": final_response.content,
                    "metadata": {
                        "conversation_id": conversation_id,
                        "steps": current_step,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
                
                trace.add_output(output=response_data)
                return response_data
                
            except Exception as e:
                self.logger.error(
                    f"Error processing message: {str(e)}",
                    conversation_id=conversation_id,
                    error=str(e),
                    exc_info=True,
                )
                
                error_response = {
                    "status": "error",
                    "message": "An error occurred while processing your request.",
                    "error": str(e),
                }
                
                trace.add_error(error=e)
                
                return {
                    "response": error_response,
                    "metadata": {
                        "conversation_id": conversation_id,
                        "error": True,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
    
    def _create_agent_message(
        self,
        role: str,
        content: Any,
        context: AgentContext,
        **kwargs,
    ) -> AgentMessage:
        """Create an AgentMessage with the given content and context."""
        return AgentMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            sender=role,
            recipient="",  # Will be set by the agent
            content=content,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=context.correlation_id,
            context=context.context,
            **kwargs,
        )
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict:
        """
        Get the conversation history for a given conversation ID.
        
        Args:
            conversation_id: The ID of the conversation
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            Dict containing the conversation history and metadata
        """
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation = self.conversations[conversation_id]
        messages = conversation["history"][offset:offset + limit]
        
        return {
            "conversation_id": conversation_id,
            "user_id": conversation["user_id"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "message_count": len(conversation["history"]),
            "messages": messages,
        }
    
    def end_conversation(self, conversation_id: str) -> bool:
        """
        End a conversation and clean up resources.
        
        Args:
            conversation_id: The ID of the conversation to end
            
        Returns:
            bool: True if the conversation was ended, False if not found
        """
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False
