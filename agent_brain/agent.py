import os
import asyncio
from google.adk.agents.llm_agent import Agent
from motor.motor_asyncio import AsyncIOMotorClient
from google.cloud import secretmanager

# --- INFRASTRUCTURE CONFIGURATION ---

def get_mongodb_uri():
    """
    Retrieves the MongoDB connection string securely from GCP Secret Manager.
    This ensures no sensitive credentials are hardcoded in the public repository.
    """
    client = secretmanager.SecretManagerServiceClient()
    # Using your project number identified during ADC setup
    name = "projects/12654003615/secrets/mongodb_url/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Initialize the asynchronous MongoDB client
# Python 3.14 performance optimization: Motor allows non-blocking DB calls
uri = get_mongodb_uri()
db_client = AsyncIOMotorClient(uri)
db = db_client["habit_os_agent"]

# --- AGENT TOOL DEFINITIONS ---

async def get_performance_correlation(days: int = 14) -> str:
    """
    ANALYSIS TOOL: Analyzes the relationship between training volume and sleep quality.
    This allows the agent to 'sense' the user's current physiological state
    based on historical data migrated during the seeding process.
    """
    # Query the 'sessions' and 'sleep_logs' collections using the 2026 Unified Schema
    sessions = await db.sessions.find().sort("date", -1).limit(days).to_list(length=days)
    sleep = await db.sleep_logs.find().sort("date", -1).limit(days).to_list(length=days)
    
    if not sessions or not sleep:
        return "Insufficient data found in MongoDB to perform correlation analysis."

    # Calculate aggregate metrics for reasoning
    total_vol = sum(s.get('total_volume', 0) for s in sessions)
    avg_sleep = sum(sl.get('duration_h', 0) for sl in sleep) / len(sleep)
    
    # Return a structured string for the LLM to process
    return (
        f"Analysis for the last {days} days:\n"
        f"- Aggregate Training Volume: {total_vol}\n"
        f"- Average Sleep Duration: {avg_sleep:.2f} hours.\n"
        f"- Data Integrity Check: {len(sessions)} sessions and {len(sleep)} sleep logs analyzed."
    )

# --- AGENT ORCHESTRATION ---

# Fetch the Gemini key similarly to the Mongo URI
def get_gemini_key():
    client = secretmanager.SecretManagerServiceClient()
    name = "projects/12654003615/secrets/GEMINI_API/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

root_agent = Agent(
    model='gemini-2.5-flash', # Chosen for low latency and high cost-efficiency (fits $100 budget)
    name='habit_os_control_agent',
    description="Autonomous Physiological Optimization Engine",
    instruction=(
        "You are the Lead Autonomous Controller for Habit-OS. Your goal is to minimize 'metabolic drift' "
        "and maximize athlete performance by acting on empirical data. "
        "1. Always use 'get_performance_correlation' to ground your advice in actual user history. "
        "2. If you detect high training volume (>8000) coupled with low sleep (<7h), recommend a 'Deload Phase'. "
        "3. Provide rational, science-based responses. Do not hallucinate metrics not present in the data."
    ),
    tools=[get_performance_correlation],
)