import os
import datetime
from zoneinfo import ZoneInfo
from google.genai import types
from google.genai.types import ThinkingConfig
from google.adk.agents.llm_agent import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.cloud import secretmanager

# --- 1. SECRETS & AUTH ---
def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    project_id = "12654003615"
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# ADK automatically uses this for authentication
os.environ["GOOGLE_API_KEY"] = get_secret("GEMINI_API")
MODEL_NAME = "gemini-3.1-flash-lite"

# --- 2. TOOLS ---
def get_weather(city: str) -> dict:
    """Retrieves the current weather report."""
    if city.lower() == "new york":
        return {"status": "success", "report": "Sunny, 25°C."}
    return {"status": "error", "message": "City not found."}

def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    try:
        tz = ZoneInfo("America/New_York") if city.lower() == "new york" else ZoneInfo("UTC")
        now = datetime.datetime.now(tz)
        return {"status": "success", "report": now.strftime("%Y-%m-%d %H:%M:%S")}
    except Exception:
        return {"status": "error", "message": "Timezone error."}

# --- 3. PLANNER CONFIGURATION ---
# This matches the industrial example you provided
thinking_config = ThinkingConfig(
    include_thoughts=True,
    thinking_budget=256
)

planner = BuiltInPlanner(
    thinking_config=thinking_config
)

# --- 4. THE ROOT AGENT ---
# This is the entry point the ADK Web UI is looking for
root_agent = LlmAgent(
    model=MODEL_NAME,
    name="wethear_and_time_checker",
    description="Agent check weather and time in New York",
    instruction=(
        "You are the agent that check weather and time in New York"
        "ignore other cities you does not have access to it"
    ),
    planner=planner,
    tools=[get_weather, get_current_time]
)