"""Google Gemini client wrapper for the Trip Planner application."""
import json
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

import google.generativeai as genai
from loguru import logger

from app.config import get_settings
from app.logging_config import get_logger

# Get logger with module name
logger = get_logger(__name__)

# Define types for better type hints
class ToolCall(TypedDict):
    """Structure for a tool call from the LLM."""
    name: str
    args: dict

class LLMResponse(TypedDict):
    """Standardized response from the LLM."""
    content: str
    tool_calls: Optional[List[ToolCall]]

class GeminiClient:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self):
        """Initialize the Gemini client with settings."""
        settings = get_settings()
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model_name = settings.GEMINI_MODEL_NAME
        self.timeout = settings.LLM_TIMEOUT
        
        # Initialize the model
        self.model = genai.GenerativeModel(self.model_name)
        logger.info(f"Initialized Gemini client with model: {self.model_name}")
    
    async def chat(
        self,
        model: str,
        system_prompt: str,
        messages: List[Dict[str, str]],
        correlation_id: str,
        agent_name: str,
    ) -> Dict[str, Any]:
        """
        Send a chat message to the Gemini model.
        
        Args:
            model: The model to use (overrides the default if provided)
            system_prompt: The system prompt to guide the model's behavior
            messages: List of message dicts with 'role' and 'content' keys
            correlation_id: Unique identifier for the conversation
            agent_name: Name of the agent making the request
            
        Returns:
            Dict containing the model's response
        """
        # Use the specified model or fall back to default
        model_to_use = model or self.model_name
        
        # Prepare the messages for the API
        chat_messages = [{"role": "user" if msg["role"] == "user" else "model", 
                         "parts": [msg["content"]]} 
                        for msg in messages]
        
        # Add system prompt as the first message
        if system_prompt:
            chat_messages.insert(0, {"role": "user", "parts": [system_prompt]})
        
        # Log the request
        logger.info(
            f"Sending chat request to {model_to_use}",
            correlation_id=correlation_id,
            agent_name=agent_name,
            message_count=len(chat_messages),
            system_prompt=system_prompt[:100] + "..." if system_prompt else ""
        )
        
        try:
            # Call the Gemini API
            response = await self.model.generate_content_async(
                contents=chat_messages,
                generation_config={
                    "max_output_tokens": 2048,
                    "temperature": 0.2,
                },
                request_options={
                    "timeout": self.timeout,
                },
            )
            
            # Extract the response text
            response_text = ""
            if response and hasattr(response, 'text'):
                response_text = response.text
            
            # Log the response
            logger.info(
                f"Received response from {model_to_use}",
                correlation_id=correlation_id,
                agent_name=agent_name,
                response_length=len(response_text),
            )
            
            return {"content": response_text}
            
        except Exception as e:
            logger.error(
                f"Error calling Gemini API: {str(e)}",
                correlation_id=correlation_id,
                agent_name=agent_name,
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def chat_with_tools(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        available_tools: List[Dict[str, Any]],
        correlation_id: str,
        agent_name: str,
    ) -> Dict[str, Any]:
        """
        Send a chat message to the Gemini model with tool calling support.
        
        Args:
            model: The model to use (overrides the default if provided)
            system_prompt: The system prompt to guide the model's behavior
            user_prompt: The user's message
            available_tools: List of available tools with their schemas
            correlation_id: Unique identifier for the conversation
            agent_name: Name of the agent making the request
            
        Returns:
            Dict with either a final answer or a tool call
        """
        # Use the specified model or fall back to default
        model_to_use = model or self.model_name
        
        # Prepare the tool schema for Gemini
        tools = []
        if available_tools:
            tools = [{
                "function_declarations": [
                    {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {}),
                    }
                    for tool in available_tools
                ]
            }]
        
        # Log the request
        logger.info(
            f"Sending tool-augmented chat request to {model_to_use}",
            correlation_id=correlation_id,
            agent_name=agent_name,
            tool_count=len(available_tools),
        )
        
        try:
            # Call the Gemini API with tools
            response = await self.model.generate_content_async(
                contents=[
                    {"role": "user", "parts": [{"text": system_prompt}]},
                    {"role": "model", "parts": [{"text": "Understood, I'm ready to help."}]},
                    {"role": "user", "parts": [{"text": user_prompt}]},
                ],
                tools=tools,
                tool_config={"function_calling_config": {"mode": "AUTO"}},
                generation_config={
                    "max_output_tokens": 2048,
                    "temperature": 0.2,
                },
                request_options={
                    "timeout": self.timeout,
                },
            )
            
            # Process the response
            if not response.candidates:
                raise ValueError("No response candidates returned from Gemini")
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise ValueError("No content in the response")
            
            part = candidate.content.parts[0]
            
            # Check for tool calls
            if hasattr(part, 'function_call') and part.function_call:
                # Handle function call
                function_call = part.function_call
                logger.info(
                    f"Tool call detected: {function_call.name}",
                    correlation_id=correlation_id,
                    agent_name=agent_name,
                    tool_name=function_call.name,
                )
                
                return {
                    "type": "tool_call",
                    "tool_name": function_call.name,
                    "tool_args": json.loads(function_call.args) if hasattr(function_call, 'args') else {},
                    "assistant_thoughts": f"Calling tool: {function_call.name}",
                }
            
            # If no tool call, return as a final answer
            response_text = part.text if hasattr(part, 'text') else ""
            
            # Log the response
            logger.info(
                f"Received final response from {model_to_use}",
                correlation_id=correlation_id,
                agent_name=agent_name,
                response_length=len(response_text),
            )
            
            return {
                "type": "final_answer",
                "content": response_text,
            }
            
        except Exception as e:
            logger.error(
                f"Error in chat_with_tools: {str(e)}",
                correlation_id=correlation_id,
                agent_name=agent_name,
                error=str(e),
                exc_info=True,
            )
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The number of tokens
        """
        # This is a simplified implementation
        # In production, you might want to use a more accurate tokenizer
        return len(text.split())  # Rough approximation
