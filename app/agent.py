import os
import asyncio
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from motor.motor_asyncio import AsyncIOMotorClient
from google.cloud import secretmanager
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
import json
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from google.genai import types

def get_secret(secret_id):
    """Retrieves secrets from GCP Secret Manager using ADC."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/12654003615/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

os.environ["GOOGLE_API_KEY"] = get_secret("GEMINI_API")
uri = get_secret("mongodb_url")
db_client = AsyncIOMotorClient(uri)
db = db_client["habit_os_agent"]

# --- DOMAIN MODELS (Schema Mapping) ---

class DietaryStrategy(BaseModel):
    calories_kcal: int
    protein_g: int

class PerformanceMetrics(BaseModel):
    max_rpe: int
    avg_volume: float
    avg_sleep: float

class UserProfile(BaseModel):
    """
    Pydantic representation of the MongoDB user_profile collection.
    Enforces type safety and validates data before the LLM processes it.
    """
    id: Optional[str] = Field(None, alias="_id")
    
    user_id: str
    age: int
    gender: str
    base_location: str
    
    data_processed: str
    optimization_status: str
    last_updated: datetime
    
    goals: List[str]
    supplements: List[str]
    recommendations: List[str]
    
    dietary_strategy: DietaryStrategy
    performance_metrics: PerformanceMetrics

async def get_active_user_profile(user_id: str = "athlete_001") -> str:
    """
    CONTEXT TOOL: Retrieves the persistent global state of the user.
    """
    raw_profile = await db.user_profile.find_one({"user_id": user_id})
    if not raw_profile:
        return f"No persistent profile found for user_id: {user_id}."

    raw_profile['_id'] = str(raw_profile['_id'])
    
    try:
        validated_profile = UserProfile(**raw_profile)
        clean_json = validated_profile.model_dump_json(indent=2)
        return (
            f"--- ACTIVE USER PROFILE ({user_id}) ---\n"
            f"Data:\n{clean_json}\n\n"
            f"INSTRUCTION: Use these baseline metrics to contextualize your analysis."
        )
    except Exception as e:
        return f"Error validating user profile schema: {str(e)}"

# --- Static Schema Mapping ---
SCHEMA_MAPPING = {
    "collections": "user_profile - show a main information about an user. sleep_logs - show total duration of sleep in hours. body_stats - show weight, body fat percentage, and body measurements. daily_metrics - show total steps and calories burned. sessions - show information about executed exercises in a particular day. exercise_metrics - show number of steps in duration in meters and spend calories in a particular day.",
    "total_volume": "Calculated as: sets * reps * weight. Represents overall muscular workload.",
    "duration_h": "Sleep duration in hours.",
    "active_calories": "Calories burned through deliberate exercise and movement.",
    "steps": "Daily step count. Proxy for general physical activity outside structured training.",
    "strain": "A holistic physiological strain score, higher means more fatigue.",
    "REM_cycles": "Number of Rapid Eye Movement phases during sleep, crucial for mental recovery."
}


async def get_performance_correlation(days: int = 30) -> str:
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




# --- Sub-Agent Definitions ---

sleep_agent = Agent(
    model='gemini-3.1-flash-lite',
    name='sleep_analyst',
    instruction="Analyze sleep logs for REM cycles and recovery quality. Focus on sleep hygiene improvements. Data contains total sleep in duration in hours per night. there's no details split by different phases"
)

exercise_metrics_agent = Agent(
    model='gemini-3.1-flash-lite',
    name='exercise_metrics_analyst',
    instruction="Analyze training volume, intensity, and daily activity metrics (steps, active calories). Focus on physiological strain and daily movement targets. daily_metric collection contains information about number of steps in the distance in meter. and sessions collection contain infromation about cycling, running exercise and weight exercise contains information with total_volume and details for each exercise with weight, reps, rpe, and sets"
)

weight_agent = Agent(
    model='gemini-3.1-flash-lite',
    name='weight_analyst',
    instruction="Analyze body composition trends and caloric maintenance levels based on weight logs. Additionally it could be information about measures of the athletes as biceps, back and weist in cm. You could find a body fat precentage as well"
)

# --- Tool Wrappers for Sub-Agents ---


async def _run_sub_agent(sub_agent: Agent, payload: str) -> str:
    """
    Invokes a sub-agent using the stable public Runner + InMemorySessionService API.

    This is the correct, future-proof ADK pattern:
    - Never touches private _invocation_context internals
    - Runner handles all InvocationContext construction internally
    - Immune to new mandatory fields added in future ADK versions
    """
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="sub_agent_runner",
        user_id="internal",
    )
    runner = Runner(
        app_name="sub_agent_runner",
        agent=sub_agent,
        session_service=session_service,
    )
    new_message = types.Content(
        role="user",
        parts=[types.Part(text=payload)],
    )
    collected: list[str] = []
    async for event in runner.run_async(
        user_id="internal",
        session_id=session.id,
        new_message=new_message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    collected.append(part.text)

    return "\n".join(collected) if collected else "(no response from sub-agent)"


async def tool_analyze_sleep(query: str) -> str:
    """Specialized tool: delegates sleep log analysis to the sleep_analyst sub-agent.
    IMPORTANT FOR ROOT AGENT: Include any findings from other sub-agents in your 'query' string to provide cross-agent context.
    """
    raw_sleep_data = await db.sleep_logs.find().sort("date", -1).limit(30).to_list(length=30)
    user_profile = await get_active_user_profile()

    payload = (
        f"User Profile Context:\n{user_profile}\n\n"
        f"User Question & Context: {query}\n"
        f"Schema Mapping: {json.dumps(SCHEMA_MAPPING)}\n"
        f"Raw Data: {json.dumps(raw_sleep_data, default=str)}"
    )
    return await _run_sub_agent(sleep_agent, payload)


async def tool_analyze_exercise_and_metrics(query: str) -> str:
    """Specialized tool for training volume, physical performance, and daily activity metrics.
    IMPORTANT FOR ROOT AGENT: Include any findings from other sub-agents in your 'query' string to provide cross-agent context.
    """
    raw_exercise_data = await db.sessions.find().sort("date", -1).limit(30).to_list(length=30)
    user_profile = await get_active_user_profile()

    payload = (
        f"User Profile Context:\n{user_profile}\n\n"
        f"User Question & Context: {query}\n"
        f"Schema Mapping: {json.dumps(SCHEMA_MAPPING)}\n"
        f"Data: {json.dumps(raw_exercise_data, default=str)}"
    )
    return await _run_sub_agent(exercise_metrics_agent, payload)


async def tool_analyze_weight(query: str) -> str:
    """Specialized tool for weight trends and body composition analysis.
    IMPORTANT FOR ROOT AGENT: Include any findings from other sub-agents in your 'query' string to provide cross-agent context.
    """
    raw_weight_data = await db.weight_logs.find().sort("date", -1).limit(30).to_list(length=30)
    user_profile = await get_active_user_profile()

    payload = (
        f"User Profile Context:\n{user_profile}\n\n"
        f"User Question & Context: {query}\n"
        f"Schema Mapping: {json.dumps(SCHEMA_MAPPING)}\n"
        f"Data: {json.dumps(raw_weight_data, default=str)}"
    )
    return await _run_sub_agent(weight_agent, payload)

# --- MCP Tool Integration ---

# --- Main Root Agent ---

root_agent = Agent(
    model='gemini-3.1-flash-lite',
    name='habit_os_control_agent',
    description="Autonomous Physiological Optimization Engine",
    instruction=(
        "You are the Lead Autonomous Controller for Habit-OS. Your goal is to minimize 'metabolic drift' "
        "and maximize athlete performance by coordinating specialized sub-agents. "
        "0. Always use 'get_active_user_profile' first to understand the athlete's goals, age, and dietary strategy before making recommendations. "
        "1. Use 'tool_analyze_sleep', 'tool_analyze_exercise_and_metrics', and 'tool_analyze_weight' for detailed domain analysis. "
        "   IMPORTANT: Always pass relevant findings from previous tools into the 'query' argument of the next tool to build cross-agent context. "
        "2. Use 'get_performance_correlation' for high-level physiological sensing. "
        "3. Use the 'insert-one' tool from the MongoDB MCP server to onboard new users or save processed profiles into MongoDB. "
        "4. If metrics indicate high strain (volume > 8000, sleep < 7h), trigger a 'Deload Phase' recommendation. "
        "5. DECISION LOGGING: Whenever you recommend a specific action plan, Deload Phase, or make a significant conclusion, "
        "   use the MongoDB 'insert-one' tool to save a JSON document detailing your recommendation and reasoning into the 'decision_log' collection."
    ),
    tools=[
        get_active_user_profile,
        get_performance_correlation,
        tool_analyze_sleep,
        tool_analyze_exercise_and_metrics,
        tool_analyze_weight,
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",
                        "mongodb-mcp-server",
                        # We do NOT add --readOnly so that you can write data
                    ],
                    env={
                        **os.environ,
                        "MDB_MCP_CONNECTION_STRING": uri,
                        "MONGODB_URI": uri,
                    },
                ),
                timeout=30,
            ),
        )
    ],
)