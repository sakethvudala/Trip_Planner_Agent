"""Base agent implementation for the Trip Planner system."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
from pydantic import BaseModel, Field

from app.llm.gemini_client import GeminiClient
from app.framework.adk_runtime import ADKRuntime, ToolResult
from app.agents.base import AgentCard, AgentMessage, AgentContext, AgentStep
from app.logging_config import get_logger
import langwatch


T = TypeVar('T', bound=BaseModel)

class BaseAgent(ABC):
    """Base class for all agents in the Trip Planner system."""
    
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
        
        # Register the agent's tools with the runtime
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register the agent's tools with the ADK runtime."""
        from app.framework.adk_runtime import ToolDefinition
        
        for tool in self.get_tools():
            try:
                # Convert dict to ToolDefinition if needed
                if isinstance(tool, dict):
                    tool_name = tool['name']
                    self.logger.debug(f"Registering tool: {tool_name}")
                    
                    handler_method = self._get_tool_handler(tool_name)
                    self.logger.debug(f"Handler for {tool_name}: {handler_method}")
                    
                    # Create a wrapper that matches the expected signature
                    def make_handler(method):
                        async def handler_wrapper(payload: dict, context: dict):
                            # Call the handler method with the payload
                            if asyncio.iscoroutinefunction(method):
                                return await method(**payload)
                            else:
                                return method(**payload)
                        return handler_wrapper
                    
                    handler = make_handler(handler_method) if handler_method else None
                    if not handler:
                        self.logger.warning(f"No handler found for tool: {tool_name}")
                        continue
                    
                    tool = ToolDefinition(
                        name=tool_name,
                        description=tool['description'],
                        input_schema=tool.get('parameters', {}),
                        output_schema=tool.get('returns', {}),
                        handler=handler
                    )
                
                self.adk_runtime.register_tool(tool)
                self.logger.info(f"Registered tool: {tool.name}")
            except Exception as e:
                tool_name = tool.name if hasattr(tool, 'name') else tool.get('name', 'unknown')
                self.logger.error(f"Failed to register tool {tool_name}: {str(e)}")
                raise
    
    def _get_tool_handler(self, tool_name: str):
        """Get the handler method for a tool by name."""
        handler_name = f"handle_{tool_name.replace('.', '_')}"
        self.logger.debug(f"Looking for handler: {handler_name} for tool: {tool_name}")
        return getattr(self, handler_name, None)
    
    @abstractmethod
    def get_tools(self) -> list:
        """Get the list of tools available to this agent.
        
        Returns:
            List of ToolDefinition objects
        """
        pass
    
    async def process_message(
        self, 
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Process an incoming message and return a response.
        
        Args:
            message: The incoming message
            context: The current conversation context
            
        Returns:
            An optional response message
        """
        try:
            # Log the incoming message
            self.logger.info(
                f"Processing message from {message.sender}",
                correlation_id=context.correlation_id,
                message_content=message.content[:100] + "..." if message.content else "",
                message_metadata=message.metadata,
            )
            
            # Start a new step in the context
            context.start_new_step(f"Processing message from {message.sender}")
            
            # Process the message using the agent's implementation
            with langwatch.span(name=f"{self.card.name}.process_message") as span:
                span.add_input(input={"message": message.content, "sender": message.sender})
                
                response = await self._process_message(message, context)
                
                span.add_output(output=response.content if response else None)
            
            # Finalize the current step
            context.finalize_current_step()
            
            return response
            
        except Exception as e:
            # Log the error
            self.logger.error(
                f"Error processing message: {str(e)}",
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            
            # Add the error to the context
            context.add_error(e, {"message": "Error processing message"})
            
            # Create an error response
            return AgentMessage(
                sender=self.card.name,
                receiver=message.sender,
                content=f"I encountered an error while processing your request: {str(e)}",
                metadata={
                    "error": True,
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                }
            )
    
    @abstractmethod
    async def _process_message(
        self, 
        message: AgentMessage,
        context: AgentContext,
    ) -> AgentMessage:
        """Process an incoming message (implemented by subclasses).
        
        Args:
            message: The incoming message
            context: The current conversation context
            
        Returns:
            An optional response message
        """
        pass
    
    async def execute_tool(
        self, 
        tool_name: str, 
        tool_args: Dict[str, Any], 
        context: AgentContext,
    ) -> ToolResult:
        """Execute a tool and return the result.
        
        Args:
            tool_name: The name of the tool to execute
            tool_args: The arguments to pass to the tool
            context: The current conversation context
            
        Returns:
            The result of the tool execution
        """
        try:
            # Log the tool execution
            self.logger.info(
                f"Executing tool: {tool_name}",
                correlation_id=context.correlation_id,
                tool_name=tool_name,
                tool_args=tool_args,
            )
            
            # Add the tool call to the current step
            tool_call = context.current_step.add_tool_call(tool_name, tool_args)
            
            # Execute the tool
            with langwatch.span(name=f"tool:{tool_name}") as span:
                span.add_input(input=tool_args)
                
                result = await self.adk_runtime.call_tool(
                    name=tool_name,
                    payload=tool_args,
                    context={
                        "correlation_id": context.correlation_id,
                        "caller_agent": self.card.name,
                    },
                )
                
                # Update the tool call with the result
                tool_call.result = result.data if hasattr(result, 'data') else {}
                tool_call.error = result.error if hasattr(result, 'error') else None
                
                span.add_output(output=tool_call.result)
            
            # Log the result
            if result.success:
                self.logger.info(
                    f"Tool {tool_name} executed successfully",
                    correlation_id=context.correlation_id,
                    tool_name=tool_name,
                )
            else:
                self.logger.error(
                    f"Tool {tool_name} failed: {result.error}",
                    correlation_id=context.correlation_id,
                    tool_name=tool_name,
                    error=result.error,
                )
            
            return result
            
        except Exception as e:
            # Log the error
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            self.logger.error(
                error_msg,
                correlation_id=context.correlation_id,
                tool_name=tool_name,
                error=str(e),
                exc_info=True,
            )
            
            # Add the error to the context
            context.add_error(e, {"tool_name": tool_name, "tool_args": tool_args})
            
            # Return an error result
            return ToolResult(
                success=False,
                error=error_msg,
                data={"error": str(e)},
            )
    
    async def generate_response(
        self,
        context: AgentContext,
        system_prompt: str,
        user_prompt: str,
        tools: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Generate a response using the LLM.
        
        Args:
            context: The current conversation context
            system_prompt: The system prompt to use
            user_prompt: The user prompt to use
            tools: Optional list of tools to make available to the LLM
            
        Returns:
            The generated response from the LLM
        """
        try:
            # Log the request
            self.logger.info(
                "Generating response with LLM",
                correlation_id=context.correlation_id,
                system_prompt_length=len(system_prompt),
                user_prompt_length=len(user_prompt),
                tool_count=len(tools) if tools else 0,
            )
            
            # Call the LLM
            response = await self.llm.generate(
                model=self.card.llm_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=tools,
            )
            
            # Log the response
            self.logger.info(
                "Received response from LLM",
                correlation_id=context.correlation_id,
                response_length=len(str(response)),
            )
            
            return response
            
        except Exception as e:
            # Log the error
            error_msg = f"Error generating response: {str(e)}"
            self.logger.error(
                error_msg,
                correlation_id=context.correlation_id,
                error=str(e),
                exc_info=True,
            )
            
            # Add the error to the context
            context.add_error(e, {"message": "Error generating response"})
            
            # Re-raise the exception
            raise
    
    def create_response(
        self,
        content: str,
        recipient: str,
        metadata: Optional[Dict] = None,
    ) -> AgentMessage:
        """Create a response message.
        
        Args:
            content: The content of the message
            recipient: The recipient of the message
            metadata: Optional metadata to include with the message
            
        Returns:
            A new AgentMessage
        """
        return AgentMessage(
            sender=self.card.name,
            receiver=recipient,
            content=content,
            metadata=metadata or {},
        )
    
    def create_error_response(
        self,
        error: Exception,
        recipient: str,
        context: Optional[Dict] = None,
    ) -> AgentMessage:
        """Create an error response message.
        
        Args:
            error: The exception that occurred
            recipient: The recipient of the message
            context: Additional context about the error
            
        Returns:
            A new AgentMessage with error details
        """
        return self.create_response(
            content=f"I encountered an error: {str(error)}",
            recipient=recipient,
            metadata={
                "error": True,
                "error_type": type(error).__name__,
                "error_details": str(error),
                "context": context or {},
            },
        )
