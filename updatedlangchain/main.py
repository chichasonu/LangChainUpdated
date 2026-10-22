import uvicorn
from starlette.applications import Starlette

# 1. Import from Google ADK
from google.adk import Agent as AdkAgent
from google.adk.runners import Runner
from google.adk.apps import App
from google.adk.sessions import InMemorySessionService
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor

# 2. Import from a2a-sdk v1.x+
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.types import AgentCard, AgentInterface, AgentCapabilities
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
HOST = "localhost"
PORT = 8000
from custom_request_handler import CustomRequestHandler

from custom_inmemory_task_store import CustomInMemoryTaskStore
from custom_redis_task_store import CustomRedisTaskStore
from custom_redis_session_service import CustomRedisSessionService

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # This enables INFO level logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Output to console
        logging.FileHandler('app.log')      # Also save to file
    ]
)

# Set specific logger level for the custom task store
logging.getLogger('updatedlangchain.custom_inmemory_task_store').setLevel(logging.DEBUG)
# logging.getLogger('updatedlangchain.custom_request_handler').setLevel(logging.DEBUG)


# Example weather tool
def get_weather(location: str) -> str:
    """Get the current weather for a given location"""
    # You can integrate with a real weather API here
    # For now, returning a mock response
    return f"The weather in {location} is sunny and 75°F"

# --- STEP 1: Define your core Agent with Google ADK ---
adk_agent = AdkAgent(
    name="my_adk_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful A2A compliant agent.",
    tools=[get_weather] 
)

# --- STEP 2: Create ADK App and Runner ---
app = App(
    name="weather_app",
    root_agent=adk_agent
)

# session_service = InMemorySessionService()

# session_service = RedisMemorySessionService(redis_client=redis_client)


# Remove or comment out:
# session_service = InMemorySessionService()

# Replace with:
session_service = CustomRedisSessionService(host="localhost", port=6379, db=0)

# WITH THIS - Redis Session Service:
import redis
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
 

runner = Runner(app=app, session_service=session_service)

# --- STEP 3: Use Google ADK's built-in A2A executor ---
agent_executor = A2aAgentExecutor(runner=runner)

# --- STEP 4: Configure A2A Framework Components ---
public_agent_card = AgentCard(
    name="ADK Managed Agent",
    description="An AI weather assistant that provides current weather information for any location worldwide.",  # Updated description
    version="1.0.0",
    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",
            protocol_version="1.0",
            url=f"http://{HOST}:{PORT}/api/v1/jsonrpc"
        )
    ],
    capabilities=AgentCapabilities(
        streaming=True,
        push_notifications=True
    ),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"]
)


# from a2a_redis import RedisTaskStore
# from a2a_redis.utils import create_redis_client
 

# redis_a2a_client = create_redis_client(url="redis://localhost:6379/0", max_connections=50)
# task_store = RedisTaskStore(redis_a2a_client, prefix="weather_agent:tasks:")

# Use your CustomRedisTaskStore instead:
task_store = CustomRedisTaskStore(host="localhost", port=6379, db=0)

request_handler = CustomRequestHandler(
    agent_executor=agent_executor,
    # task_store=CustomInMemoryTaskStore(max_tasks=1000, task_ttl_seconds=3600),
    task_store=task_store,
    agent_card=public_agent_card
)

# --- STEP 5: Compose Router and Boot Server ---
app = Starlette(
    routes=[
        *create_agent_card_routes(public_agent_card),
        *create_jsonrpc_routes(request_handler, rpc_url="/api/v1/jsonrpc"),
    ]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)