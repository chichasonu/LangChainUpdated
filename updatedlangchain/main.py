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

# --- STEP 1: Define your core Agent with Google ADK ---
adk_agent = AdkAgent(
    name="my_adk_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful A2A compliant agent.",
    tools=[]
)

# --- STEP 2: Create ADK App and Runner ---
app = App(
    name="weather_app",
    root_agent=adk_agent
)

session_service = InMemorySessionService()
runner = Runner(app=app, session_service=session_service)

# --- STEP 3: Use Google ADK's built-in A2A executor ---
agent_executor = A2aAgentExecutor(runner=runner)

# --- STEP 4: Configure A2A Framework Components ---
public_agent_card = AgentCard(
    name="ADK Managed Agent",
    description="An AI agent powered by google-adk and a2a-sdk v1.x+",
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
        push_notifications=False
    ),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"]
)

request_handler = DefaultRequestHandler(
    agent_executor=agent_executor,
    task_store=InMemoryTaskStore(),
    agent_card=public_agent_card,
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