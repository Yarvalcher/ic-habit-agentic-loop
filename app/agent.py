import json
import os
from datetime import datetime

from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.cloud import secretmanager
from google.genai import types
from mcp import StdioServerParameters
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from app.app_utils.burnout_model import calculate_burnout_risk_score


def get_secret(secret_id):
    """Retrieves secrets from GCP Secret Manager using ADC."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/12654003615/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


os.environ["GOOGLE_API_KEY"] = get_secret("GEMINI_API")
uri = get_secret("mongodb_url_read")
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

    id: str | None = Field(None, alias="_id")

    user_id: str
    age: int
    gender: str
    base_location: str

    data_processed: str
    optimization_status: str
    last_updated: datetime

    goals: list[str]
    supplements: list[str]
    recommendations: list[str]

    dietary_strategy: DietaryStrategy
    performance_metrics: PerformanceMetrics


async def get_active_user_profile(user_id: str = "athlete_001") -> str:
    """
    CONTEXT TOOL: Retrieves the persistent global state of the user.
    """
    raw_profile = await db.user_profile.find_one({"user_id": user_id})
    if not raw_profile:
        return f"No persistent profile found for user_id: {user_id}."

    raw_profile["_id"] = str(raw_profile["_id"])

    try:
        validated_profile = UserProfile(**raw_profile)
        clean_json = validated_profile.model_dump_json(indent=2)
        return (
            f"--- ACTIVE USER PROFILE ({user_id}) ---\n"
            f"Data:\n{clean_json}\n\n"
            f"INSTRUCTION: Use these baseline metrics to contextualize your analysis."
        )
    except Exception as e:
        return f"Error validating user profile schema: {e!s}"


# --- Static Schema Mapping ---
SCHEMA_MAPPING = {
    "collections": "user_profile - main information about the user. sleep_logs - total sleep duration in hours. body_stats - weight, body fat percentage, and body measurements. daily_metrics - daily step count synced from Huawei Health. sessions - detailed training sessions with nested exercise sets.",
    "user_profile": "Keeps your static profile, goals, and current Big Picture status (e.g., Deload Phase)",
    "body_stats": "Your ongoing weight, body fat, and measurements.",
    "biomarkers": "For blood work, hormone levels, and clinical data",
    "lifestyle_logs": "For daily stress ratings, alcohol/caffeine intake, and subjective recovery scores.",
    "decision_log": "Stores the autonomous decisions and recommendations for you, providing a paper trail of why we changed your training or nutrition.",
    "sessions_schema": (
        "Each document in 'sessions' has the following structure: "
        "{ date: str, timestamp: datetime, total_volume: int, "
        "exercises: [ { exercise: str (name of the exercise, e.g. 'Deadlifts'), "
        "sets: [ { reps: int, weight: float (kg), rpe: float (Rate of Perceived Exertion 1-10) } ] } ] }. "
        "IMPORTANT: total_volume > 0 means the session contains weight-training exercises. "
        "Always unpack exercises[].sets[] to calculate per-exercise volume (reps * weight), "
        "average RPE, and set counts when analysing strength sessions."
    ),
    "total_volume": "Calculated as sum of (reps * weight) across all sets of all exercises in a session. Represents overall muscular workload for that day.",
    "duration_h": "Sleep duration in hours.",
    "daily_metrics_schema": (
        "Each document in 'daily_metrics' has the following structure: "
        "{ date: str (YYYY-MM-DD), source: str (e.g. 'huawei_health_sync'), "
        "steps: int, timestamp: datetime }. "
        "NOTE: this collection contains ONLY step count data. "
        "There is no active_calories, distance, or strain field here."
    ),
    "steps": "Daily step count from Huawei Health. Proxy for general physical activity outside structured training.",
    "strain": "A holistic physiological strain score, higher means more fatigue.",
    "REM_cycles": "Number of Rapid Eye Movement phases during sleep, crucial for mental recovery.",
}


async def get_performance_correlation(days: int = 30) -> str:
    """
    ANALYSIS TOOL: Analyzes the relationship between training volume and sleep quality.
    This allows the agent to 'sense' the user's current physiological state
    based on historical data migrated during the seeding process.
    """
    # Query the 'sessions' and 'sleep_logs' collections using the 2026 Unified Schema
    sessions = (
        await db.sessions.find().sort("date", -1).limit(days).to_list(length=days)
    )
    sleep = await db.sleep_logs.find().sort("date", -1).limit(days).to_list(length=days)

    if not sessions or not sleep:
        return "Insufficient data found in MongoDB to perform correlation analysis."

    # Calculate aggregate metrics for reasoning
    total_vol = sum(s.get("total_volume", 0) for s in sessions)
    avg_sleep = sum(sl.get("duration_h", 0) for sl in sleep) / len(sleep)

    # Return a structured string for the LLM to process
    return (
        f"Analysis for the last {days} days:\n"
        f"- Aggregate Training Volume: {total_vol}\n"
        f"- Average Sleep Duration: {avg_sleep:.2f} hours.\n"
        f"- Data Integrity Check: {len(sessions)} sessions and {len(sleep)} sleep logs analyzed."
    )


# --- Sub-Agent Definitions ---

sleep_agent = Agent(
    model="gemini-3.1-flash-lite",
    name="sleep_analyst",
    instruction="Analyze sleep logs for REM cycles and recovery quality. Focus on sleep hygiene improvements. Data contains total sleep in duration in hours per night. there's no details split by different phases",
)

exercise_metrics_agent = Agent(
    model="gemini-3.1-flash-lite",
    name="exercise_metrics_analyst",
    instruction=(
        "You are a strength and conditioning analyst. You have access to two data sources:\n"
        "1. 'sessions' collection — each document represents a training day. "
        "When total_volume > 0 the session is a WEIGHT-TRAINING session. "
        "The nested structure is: exercises (array) -> each item has 'exercise' (name) and 'sets' (array). "
        "Each set has: 'reps' (int), 'weight' (float, kg), 'rpe' (float, Rate of Perceived Exertion 1-10). "
        "ALWAYS unpack exercises[].sets[] to compute per-exercise volume (reps * weight * sets), "
        "average RPE, and total set counts. Never rely on total_volume alone for detailed analysis.\n"
        "Sessions with total_volume == 0 are cardio sessions (cycling, running) — analyse them by any available duration or distance fields in the session document.\n"
        "2. 'daily_metrics' collection — contains ONLY steps (int) per day, synced from Huawei Health. There is no distance or active_calories field in this collection.\n"
        "Focus on: physiological strain trends, per-exercise volume progression, RPE patterns, "
        "and whether daily movement targets are being met."
    ),
)

weight_agent = Agent(
    model="gemini-3.1-flash-lite",
    name="weight_analyst",
    instruction="Analyze body composition trends and caloric maintenance levels based on weight logs. Additionally it could be information about measures of the athletes as biceps, back and weist in cm. You could find a body fat percentage as well",
)

biomarkers_agent = Agent(
    model="gemini-3.1-flash-lite",
    name="biomarkers_analyst",
    instruction=(
        "You are a clinical data specialist. Analyze blood work, hormone levels, and other "
        "biomarker readings from the 'biomarkers' collection. Identify trends, flag values "
        "outside reference ranges, and correlate findings with the athlete's performance goals. "
        "Always contextualise results against the user profile (age, gender, training phase)."
    ),
)

lifestyle_agent = Agent(
    model="gemini-3.1-flash-lite",
    name="lifestyle_analyst",
    instruction=(
        "You are a recovery and lifestyle specialist. Analyze daily stress ratings, "
        "alcohol/caffeine intake, and subjective recovery scores from the 'lifestyle_logs' "
        "collection. Identify patterns that negatively or positively impact athletic performance "
        "and sleep quality. Provide actionable behavioural recommendations."
    ),
)

decision_log_agent = Agent(
    model="gemini-3.1-flash-lite",
    name="decision_log_reviewer",
    instruction=(
        "You are an autonomous decision auditor. Review past recommendations and action plans "
        "stored in the 'decision_log' collection. Summarise the history of interventions, assess "
        "whether previous recommendations were followed, and identify recurring patterns or "
        "unresolved issues that require a new recommendation from the root agent."
    ),
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
    raw_sleep_data = (
        await db.sleep_logs.find().sort("date", -1).limit(30).to_list(length=30)
    )
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
    raw_exercise_data = (
        await db.sessions.find().sort("date", -1).limit(30).to_list(length=30)
    )
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
    raw_weight_data = (
        await db.body_stats.find().sort("date", -1).limit(30).to_list(length=30)
    )
    user_profile = await get_active_user_profile()

    payload = (
        f"User Profile Context:\n{user_profile}\n\n"
        f"User Question & Context: {query}\n"
        f"Schema Mapping: {json.dumps(SCHEMA_MAPPING)}\n"
        f"Data: {json.dumps(raw_weight_data, default=str)}"
    )
    return await _run_sub_agent(weight_agent, payload)


async def tool_analyze_biomarkers(query: str) -> str:
    """Specialized tool: delegates blood work and hormone analysis to the biomarkers_analyst sub-agent.
    IMPORTANT FOR ROOT AGENT: Include any findings from other sub-agents in your 'query' string to provide cross-agent context.
    """
    raw_data = await db.biomarkers.find().sort("date", -1).limit(30).to_list(length=30)
    user_profile = await get_active_user_profile()

    payload = (
        f"User Profile Context:\n{user_profile}\n\n"
        f"User Question & Context: {query}\n"
        f"Schema Mapping: {json.dumps(SCHEMA_MAPPING)}\n"
        f"Raw Biomarker Data: {json.dumps(raw_data, default=str)}"
    )
    return await _run_sub_agent(biomarkers_agent, payload)


async def tool_analyze_lifestyle(query: str) -> str:
    """Specialized tool: delegates stress, caffeine, alcohol, and subjective recovery analysis to the lifestyle_analyst sub-agent.
    IMPORTANT FOR ROOT AGENT: Include any findings from other sub-agents in your 'query' string to provide cross-agent context.
    """
    raw_data = (
        await db.lifestyle_logs.find().sort("date", -1).limit(30).to_list(length=30)
    )
    user_profile = await get_active_user_profile()

    payload = (
        f"User Profile Context:\n{user_profile}\n\n"
        f"User Question & Context: {query}\n"
        f"Schema Mapping: {json.dumps(SCHEMA_MAPPING)}\n"
        f"Raw Lifestyle Logs: {json.dumps(raw_data, default=str)}"
    )
    return await _run_sub_agent(lifestyle_agent, payload)


async def tool_review_decision_log(query: str) -> str:
    """Specialized tool: retrieves and audits past autonomous decisions stored in the decision_log collection.
    Use this to avoid repeating recommendations and to identify unresolved interventions.
    """
    raw_data = (
        await db.decision_log.find().sort("timestamp", -1).limit(20).to_list(length=20)
    )

    payload = (
        f"User Question & Context: {query}\n"
        f"Schema Mapping: {json.dumps(SCHEMA_MAPPING)}\n"
        f"Past Decision Log Entries: {json.dumps(raw_data, default=str)}"
    )
    return await _run_sub_agent(decision_log_agent, payload)


async def predict_burnout_risk(user_id: str = "athlete_001") -> str:
    """Specialized tool: Predicts Burnout Risk Score (0-100) based on recent volume, sleep, and lifestyle logs."""
    # 1. Volume (last 7 days)
    recent_sessions = await db.sessions.find().sort("date", -1).limit(7).to_list(length=7)
    recent_volume = sum(s.get("total_volume", 0) for s in recent_sessions)
    baseline_volume = 10000 # hardcoded baseline to prevent complex lookbacks for now
    
    # 2. Sleep
    recent_sleep = await db.sleep_logs.find().sort("date", -1).limit(7).to_list(length=7)
    avg_sleep = sum(sl.get("duration_h", 0) for sl in recent_sleep) / len(recent_sleep) if recent_sleep else 7.5

    # 3. Mood
    recent_lifestyle = await db.lifestyle_logs.find().sort("date", -1).limit(7).to_list(length=7)
    negative_mood_days = sum(1 for log in recent_lifestyle if "Anxious" in log.get("mood", "") or "Low" in log.get("energy_level", ""))

    score = calculate_burnout_risk_score(recent_volume, baseline_volume, avg_sleep, negative_mood_days)
    
    return f"BURNOUT RISK PREDICTION: The current Burnout Risk Score is {score}/100. (Based on recent volume: {recent_volume}, avg sleep: {avg_sleep:.1f}h, and {negative_mood_days} negative mood days)."


# --- MCP Tool Integration ---

# --- Main Root Agent ---

root_agent = Agent(
    model="gemini-3.1-flash-lite",
    name="habit_os_control_agent",
    description="Autonomous Physiological Optimization Engine",
    instruction=(
        "You are the Lead Autonomous Controller for Habit-OS. Your goal is to minimize 'metabolic drift' "
        "and maximize athlete performance by coordinating specialized sub-agents. "
        "0. Always use 'get_active_user_profile' first to understand the athlete's goals, age, and dietary strategy before making recommendations. "
        "1. Use 'tool_analyze_sleep', 'tool_analyze_exercise_and_metrics', and 'tool_analyze_weight' for detailed domain analysis. "
        "   IMPORTANT: Always pass relevant findings from previous tools into the 'query' argument of the next tool to build cross-agent context. "
        "2. Use 'get_performance_correlation' for high-level physiological sensing. "
        "3. Use 'predict_burnout_risk' to calculate the Burnout Risk Score based on quantitative and qualitative data. If the Risk Score > 80, strongly advise against heavy training and proactively recommend a deload or mobility session. "
        "4. Use 'tool_analyze_biomarkers' to interpret blood work and hormone panels when the user asks about health markers or clinical data. "
        "5. Use 'tool_analyze_lifestyle' to evaluate stress, caffeine/alcohol intake, and subjective recovery scores. "
        "6. Use 'tool_review_decision_log' BEFORE making new recommendations to check what interventions have already been suggested, avoiding repetition. "
        "7. Use the 'insert-one' tool from the MongoDB MCP server to onboard new users or save processed profiles into MongoDB. "
        "8. If metrics indicate high strain (volume > 8000, sleep < 7h), trigger a 'Deload Phase' recommendation. "
        "9. DECISION LOGGING: Whenever you recommend a specific action plan, Deload Phase, or make a significant conclusion, "
        "   use the MongoDB 'insert-one' tool to save a JSON document detailing your recommendation and reasoning into the 'decision_log' collection."
    ),
    tools=[
        get_active_user_profile,
        get_performance_correlation,
        tool_analyze_sleep,
        tool_analyze_exercise_and_metrics,
        tool_analyze_weight,
        tool_analyze_biomarkers,
        tool_analyze_lifestyle,
        tool_review_decision_log,
        predict_burnout_risk,
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
        ),
    ],
)
