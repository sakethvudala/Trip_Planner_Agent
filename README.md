# Trip Planner Super Agent System

A sophisticated multi-agent trip planning system powered by Google Gemini and LangWatch, featuring intelligent orchestration and agent-to-agent communication.

## Features

### Super Agent Architecture
- **TripSuperAgent**: Orchestrates all specialized agents with intelligent routing
- **PlannerAgent**: State-based router that determines next planning steps
- **LocationAgent**: Finds and recommends points of interest using Google Maps
- **StayAgent**: Handles hotel and accommodation search and booking
- **RouteAgent**: Optimizes travel routes and transportation
- **BudgetAgent**: Manages trip budget and expense tracking

### Key Capabilities
- **Agent-to-Agent Communication**: Seamless coordination between specialized agents
- **LangWatch Integration**: Full observability with traces, spans, and events
- **AtoA Standard Compliance**: Agent Card at `/.well-known/agent_card.json`
- **RESTful API**: FastAPI-powered endpoints with OpenAPI documentation
- **Tool Management**: Dynamic tool registration and execution via ADK Runtime

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    TripSuperAgent                        │
│              (Orchestration Loop)                        │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │   PlannerAgent        │
        │  (State-based Router) │
        └───────────┬───────────┘
                    │
    ┌───────────────┼───────────────┬───────────────┐
    │               │               │               │
┌───▼────┐    ┌────▼─────┐   ┌────▼────┐    ┌────▼──────┐
│Location│    │  Stay    │   │  Route  │    │  Budget   │
│ Agent  │    │  Agent   │   │  Agent  │    │  Agent    │
└────────┘    └──────────┘   └─────────┘    └───────────┘
```

### Orchestration Flow

1. User sends trip request to TripSuperAgent
2. TripSuperAgent enters orchestration loop:
   - Consults PlannerAgent for next step
   - PlannerAgent analyzes current state and returns target agent + action
   - TripSuperAgent executes action via target agent
   - Results are passed back to PlannerAgent
   - Loop continues until PlannerAgent signals completion
3. Final trip plan is returned to user

## Prerequisites

- Python 3.9+
- Google API Key (for Gemini LLM)
- LangWatch API Key (optional, for observability)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd agent
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file:**
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   LANGWATCH_API_KEY=your_langwatch_api_key_here  # Optional
   ENVIRONMENT=development
   DEBUG=True
   HOST=0.0.0.0
   PORT=8000
   LOG_LEVEL=INFO
   ```

## Running the Application

**Start the server:**
```bash
python server.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### Core Endpoints
- `POST /api/chat` - Send a trip planning request
- `GET /api/conversations/{conversation_id}` - Get conversation history
- `DELETE /api/conversations/{conversation_id}` - End a conversation
- `GET /health` - Health check endpoint

### Discovery & Documentation
- `GET /.well-known/agent_card.json` - Agent Card (AtoA standard)
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /api/openapi.json` - OpenAPI schema

## Example Usage

### Send a Trip Planning Request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Plan a 3-day trip to Paris",
    "user_id": "user123"
  }'
```

### Response
```json
{
  "response": "I'll help you plan a 3-day trip to Paris...",
  "session_id": "conv-123",
  "status": "success"
}
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GOOGLE_API_KEY` | Google API key for Gemini LLM | - | Yes |
| `LANGWATCH_API_KEY` | LangWatch API key for observability | - | No |
| `ENVIRONMENT` | Application environment | development | No |
| `DEBUG` | Enable debug mode | False | No |
| `HOST` | Host to bind the server to | 0.0.0.0 | No |
| `PORT` | Port to run the server on | 8000 | No |
| `LOG_LEVEL` | Logging level | INFO | No |

## Development

### Project Structure
```
agent/
├── app/
│   ├── agents/           # Agent implementations
│   │   ├── base.py       # Core data classes
│   │   ├── base_agent.py # Base agent class
│   │   ├── trip_super_agent.py
│   │   ├── planner_agent.py
│   │   ├── location_agent.py
│   │   ├── stay_agent.py
│   │   ├── route_agent.py
│   │   └── budget_agent.py
│   ├── framework/        # Core framework
│   │   └── adk_runtime.py
│   ├── llm/             # LLM clients
│   │   └── gemini_client.py
│   ├── tools/           # Tool implementations
│   ├── config.py        # Configuration
│   ├── schemas.py       # Pydantic models
│   └── logging_config.py
├── server.py            # FastAPI application
├── requirements.txt     # Dependencies
└── README.md
```

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8

# Type checking
mypy app/
```

## LangWatch Integration

The system includes full LangWatch observability:

- **Root Traces**: Created at TripSuperAgent level for each request
- **Agent Spans**: Each agent's message processing creates a nested span
- **Tool Spans**: Each tool execution creates a nested span
- **Events**: Orchestration steps logged as trace events

View traces in your LangWatch dashboard after setting `LANGWATCH_API_KEY`.

## Agent-to-Agent (AtoA) Standard

This agent follows the AtoA standard for agent discovery and communication:

**Agent Card Endpoint:** `GET /.well-known/agent_card.json`

The agent card includes:
- Agent identity and metadata
- Capabilities and skills
- Service discovery information
- API endpoints and schemas
- Compliance and security information

## Tools & Integrations

### Implemented Tools
- `maps.search_places` - Search for locations
- `maps.distance_matrix` - Calculate distances
- `reviews.get` - Get place reviews

### Planned Tools
- Hotel search and booking
- Route optimization
- Currency conversion
- Expense tracking

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.

---

**Built with:**
- [Google Gemini](https://ai.google.dev/) - LLM
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [LangWatch](https://langwatch.ai/) - Observability
- [Pydantic](https://pydantic.dev/) - Data validation
