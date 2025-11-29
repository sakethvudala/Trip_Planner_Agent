""
Tests for the Trip Planner API.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.agents.trip_super_agent import TripSuperAgent

# Create test client
client = TestClient(app)

def test_health_check():
    ""Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_chat_endpoint():
    ""Test the chat endpoint with a simple message."""
    test_message = {"message": "Plan a trip to Paris for 3 days"}
    response = client.post("/api/chat", json=test_message)
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "metadata" in data

def test_conversation_history():
    ""Test retrieving conversation history."""
    # First, create a conversation
    test_message = {"message": "What can you do?"}
    response = client.post("/api/chat", json=test_message)
    conversation_id = response.json()["conversation_id"]
    
    # Now get the conversation history
    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conversation_id
    assert len(data["messages"]) > 0

@pytest.mark.asyncio
async def test_super_agent_initialization():
    ""Test that the super agent initializes all sub-agents correctly."""
    agent = TripSuperAgent()
    assert hasattr(agent, "agents")
    assert "planner" in agent.agents
    assert "location" in agent.agents
    assert "stay" in agent.agents
    assert "route" in agent.agents
    assert "budget" in agent.agents

@pytest.mark.asyncio
async def test_super_agent_message_processing():
    ""Test that the super agent can process a message."""
    agent = TripSuperAgent()
    response = await agent.process_message("Plan a trip to Tokyo")
    assert "response" in response
    assert "metadata" in response
    assert "conversation_id" in response["metadata"]

def test_invalid_conversation_id():
    ""Test handling of invalid conversation ID."""
    response = client.get("/api/conversations/invalid-id")
    assert response.status_code == 404

def test_end_conversation():
    ""Test ending a conversation."""
    # First, create a conversation
    test_message = {"message": "Test conversation"}
    response = client.post("/api/chat", json=test_message)
    conversation_id = response.json()["conversation_id"]
    
    # Now end the conversation
    response = client.delete(f"/api/conversations/{conversation_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify the conversation is gone
    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 404
