"""Base classes and types for the agent system."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from pydantic import BaseModel, Field

from app.llm.gemini_client import GeminiClient
from app.framework.adk_runtime import ADKRuntime, ToolContext


class AgentCard(BaseModel):
    """Metadata and capabilities of an agent."""
    name: str
    description: str
    tools: List[str] = Field(default_factory=list)
    llm_model: str = "gemini-1.5-flash"
    system_prompt: str = ""
    
    def __str__(self) -> str:
        return f"Agent(name='{self.name}', tools={self.tools})"


class AgentMessage(BaseModel):
    """A message between agents or from user to agent."""
    sender: str
    receiver: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"{self.sender} -> {self.receiver}: {self.content[:50]}..."


class ToolCall(BaseModel):
    """A tool call made by an agent."""
    name: str
    args: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentStep(BaseModel):
    """A single step in the agent's reasoning process."""
    thought: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    next_agent: Optional[str] = None
    
    def add_tool_call(self, name: str, args: Dict[str, Any]) -> ToolCall:
        """Add a tool call to this step."""
        tool_call = ToolCall(name=name, args=args)
        self.tool_calls.append(tool_call)
        return tool_call
    
    def set_tool_result(self, tool_call_index: int, result: Dict[str, Any], error: str = None) -> None:
        """Set the result of a tool call."""
        if 0 <= tool_call_index < len(self.tool_calls):
            self.tool_calls[tool_call_index].result = result
            self.tool_calls[tool_call_index].error = error
        else:
            raise IndexError(f"Tool call index {tool_call_index} out of range")


class AgentContext(BaseModel):
    """The context for an agent's execution."""
    # Input from the user
    user_input: Dict[str, Any]
    
    # Agent's working memory
    memory: Dict[str, Any] = Field(default_factory=dict)
    
    # Current step in the agent's reasoning
    current_step: Optional[AgentStep] = None
    
    # History of steps taken so far
    history: List[AgentStep] = Field(default_factory=list)
    
    # Any errors that occurred during execution
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    def add_error(self, error: Exception, context: Dict[str, Any] = None) -> None:
        """Add an error to the context."""
        error_info = {
            "error": str(error),
            "type": type(error).__name__,
            "context": context or {},
        }
        self.errors.append(error_info)
    
    def start_new_step(self, thought: str) -> None:
        """Start a new reasoning step."""
        if self.current_step is not None:
            self.history.append(self.current_step)
        self.current_step = AgentStep(thought=thought)
    
    def finalize_current_step(self) -> None:
        """Finalize the current step and add it to history."""
        if self.current_step is not None:
            self.history.append(self.current_step)
            self.current_step = None


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(
        self,
        card: AgentCard,
        llm_client: GeminiClient,
        adk_runtime: ADKRuntime,
        logger=None,
    ):
        """Initialize the agent with its dependencies."""
        self.card = card
        self.llm = llm_client
        self.adk_runtime = adk_runtime
        self.logger = logger or get_logger(f"agent.{card.name.lower()}")
        
        # Set the model from the card if provided
        if not hasattr(self.llm, 'model_name'):
            self.llm.model_name = card.llm_model
    
    @abstractmethod
    async def handle(
        self,
        message: AgentMessage,
        context: AgentContext,
        correlation_id: str,
    ) -> AgentMessage:
        """
        Handle an incoming message and return a response.
        
        Args:
            message: The incoming message
            context: The current execution context
            correlation_id: A unique ID for this interaction
            
        Returns:
            An optional response message to another agent
        """
        pass
    
    async def process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext,
        correlation_id: str,
    ) -> Dict[str, Any]:
        """
        Process a list of tool calls and return the results.
        
        Args:
            tool_calls: List of tool calls to process
            context: The current execution context
            correlation_id: A unique ID for this interaction
            
        Returns:
            A dictionary of tool call results
        """
        results = {}
        
        for i, tool_call in enumerate(tool_calls):
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            
            if not tool_name:
                self.logger.warning(
                    f"Tool call missing name: {tool_call}",
                    correlation_id=correlation_id,
                    agent_name=self.card.name,
                )
                continue
            
            # Add the tool call to the current step
            tool_call_obj = context.current_step.add_tool_call(tool_name, tool_args)
            
            try:
                # Call the tool
                result = await self.adk_runtime.call_tool(
                    name=tool_name,
                    payload=tool_args,
                    correlation_id=correlation_id,
                    caller_agent=self.card.name,
                )
                
                # Store the result
                tool_call_obj.result = result
                results[tool_name] = result
                
                self.logger.info(
                    f"Tool call {i+1}/{len(tool_calls)} completed: {tool_name}",
                    correlation_id=correlation_id,
                    agent_name=self.card.name,
                    tool_name=tool_name,
                    success=True,
                )
                
            except Exception as e:
                error_msg = f"Error calling tool {tool_name}: {str(e)}"
                tool_call_obj.error = error_msg
                results[tool_name] = {"error": error_msg}
                
                self.logger.error(
                    error_msg,
                    correlation_id=correlation_id,
                    agent_name=self.card.name,
                    tool_name=tool_name,
                    error=str(e),
                    exc_info=True,
                )
        
        return results
    
    async def generate_response(
        self,
        context: AgentContext,
        correlation_id: str,
        user_prompt: str,
        system_prompt_override: str = None,
    ) -> Dict[str, Any]:
        """
        Generate a response using the LLM.
        
        Args:
            context: The current execution context
            correlation_id: A unique ID for this interaction
            user_prompt: The user's prompt
            system_prompt_override: Optional override for the system prompt
            
        Returns:
            The LLM's response
        """
        system_prompt = system_prompt_override or self.card.system_prompt
        
        # Get available tools for this agent
        available_tools = self.adk_runtime.get_tool_schemas(self.card.tools)
        
        self.logger.info(
            "Generating response with LLM",
            correlation_id=correlation_id,
            agent_name=self.card.name,
            has_system_prompt=bool(system_prompt),
            tool_count=len(available_tools),
        )
        
        # Call the LLM
        response = await self.llm.chat_with_tools(
            model=self.card.llm_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            available_tools=available_tools,
            correlation_id=correlation_id,
            agent_name=self.card.name,
        )
        
        return response


def get_logger(name: str):
    """Get a logger instance for an agent."""
    import logging
    from app.logging_config import get_logger as get_app_logger
    
    # Create a logger with the agent's name
    logger = get_app_logger(name)
    
    # Configure the logger with agent-specific context
    class AgentLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            # Add agent name to log records
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            
            # Ensure we have the required fields
            extra = kwargs['extra']
            extra.setdefault('agent_name', self.extra.get('agent_name', 'unknown'))
            
            return msg, kwargs
    
    return AgentLoggerAdapter(logger, {'agent_name': name})
