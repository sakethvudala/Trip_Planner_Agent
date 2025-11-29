"""
ADK (Agent Development Kit) Style Tool Runtime.

This module provides a runtime for managing and executing tools that agents can use.
It handles tool registration, schema generation, and execution with proper context.
"""
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypedDict, Union

from loguru import logger
from pydantic import BaseModel, Field

from app.logging_config import get_logger

# Get logger with module name
logger = get_logger(__name__)


class ToolContext(TypedDict):
    """Context passed to tool handlers."""
    correlation_id: str
    caller_agent: str
    tool_name: str
    tool_args: Dict[str, Any]


class ToolResult(BaseModel):
    """Standardized result from tool execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Definition of a tool that can be used by agents."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any], ToolContext], Any]
    
    class Config:
        arbitrary_types_allowed = True  # To allow Callable in Pydantic model


class ADKRuntime:
    """Runtime for managing and executing tools."""
    
    def __init__(self):
        """Initialize the ADK runtime with an empty tool registry."""
        self._tools: Dict[str, ToolDefinition] = {}
        logger.info("Initialized ADK Runtime")
    
    def register_tool(self, tool: ToolDefinition) -> None:
        """
        Register a tool with the runtime.
        
        Args:
            tool: The tool definition to register
            
        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool_schemas(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get the schemas for the specified tools.
        
        Args:
            tool_names: List of tool names to get schemas for. If None, returns all.
            
        Returns:
            List of tool schemas in the format expected by the LLM
        """
        tools = []
        names = tool_names if tool_names is not None else self._tools.keys()
        
        for name in names:
            if name not in self._tools:
                logger.warning(f"Tool not found: {name}")
                continue
                
            tool = self._tools[name]
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": tool.input_schema.get("properties", {}),
                    "required": tool.input_schema.get("required", []),
                },
            })
        
        return tools
    
    async def call_tool(
        self, 
        name: str, 
        payload: Dict[str, Any], 
        correlation_id: str,
        caller_agent: str,
    ) -> Dict[str, Any]:
        """
        Call a tool by name with the given payload.
        
        Args:
            name: Name of the tool to call
            payload: Arguments to pass to the tool
            correlation_id: Correlation ID for the current operation
            caller_agent: Name of the agent calling the tool
            
        Returns:
            The result of the tool execution
            
        Raises:
            ValueError: If the tool is not found
            Exception: If the tool execution fails
        """
        if name not in self._tools:
            error_msg = f"Tool not found: {name}"
            logger.error(
                error_msg,
                correlation_id=correlation_id,
                caller_agent=caller_agent,
                tool_name=name,
            )
            raise ValueError(error_msg)
        
        tool = self._tools[name]
        tool_context = ToolContext(
            correlation_id=correlation_id,
            caller_agent=caller_agent,
            tool_name=name,
            tool_args=payload,
        )
        
        # Log tool call start
        logger.info(
            f"Calling tool: {name}",
            correlation_id=correlation_id,
            caller_agent=caller_agent,
            tool_name=name,
            payload=payload,
        )
        
        try:
            # Execute the tool handler
            result = await tool.handler(payload, tool_context)
            
            # If the result is already a ToolResult, use it directly
            if isinstance(result, ToolResult):
                tool_result = result
            # If it's a dict, convert to ToolResult
            elif isinstance(result, dict):
                tool_result = ToolResult(success=True, data=result)
            # Otherwise, wrap in ToolResult
            else:
                tool_result = ToolResult(success=True, data={"result": result})
            
            # Log successful tool execution
            logger.info(
                f"Tool {name} executed successfully",
                correlation_id=correlation_id,
                caller_agent=caller_agent,
                tool_name=name,
                result_length=len(str(tool_result.dict())) if hasattr(tool_result, 'dict') else None,
            )
            
            # Return the result as a dict
            return tool_result.dict()
            
        except Exception as e:
            # Log the error
            error_msg = f"Error executing tool {name}: {str(e)}"
            logger.error(
                error_msg,
                correlation_id=correlation_id,
                caller_agent=caller_agent,
                tool_name=name,
                error=str(e),
                exc_info=True,
            )
            
            # Return an error result
            return ToolResult(
                success=False,
                error=error_msg,
                metadata={"exception": str(e)},
            ).dict()
    
    def list_tools(self) -> List[str]:
        """
        Get a list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """
        Get a tool definition by name.
        
        Args:
            name: Name of the tool to get
            
        Returns:
            The tool definition, or None if not found
        """
        return self._tools.get(name)


def tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    output_schema: Dict[str, Any],
) -> Callable:
    """
    Decorator to register a function as a tool.
    
    Args:
        name: Name of the tool
        description: Description of what the tool does
        input_schema: JSON Schema for the tool's input parameters
        output_schema: JSON Schema for the tool's output
        
    Returns:
        A decorator that registers the function as a tool
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # This wrapper is used when the tool is called directly
            # For the ADKRuntime, we'll use the original function
            return await func(*args, **kwargs)
        
        # Store the tool metadata as attributes of the wrapper
        wrapper.__tool_metadata__ = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "output_schema": output_schema,
        }
        
        return wrapper
    
    return decorator
