import os
import asyncio
from google.adk.agents.llm_agent import Agent
from motor.motor_asyncio import AsyncIOMotorClient
from google.cloud import secretmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json

def get_mongodb_uri():
    """
    Retrieves the MongoDB connection string securely from GCP Secret Manager.
    This ensures no sensitive credentials are hardcoded in the public repository.
    """
    client = secretmanager.SecretManagerServiceClient()

    name = "projects/12654003615/secrets/mongodb_url/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

uri = get_mongodb_uri()
db_client = AsyncIOMotorClient(uri)
db = db_client["habit_os_agent"]



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




# --- Sub-Agent Definitions ---

sleep_agent = Agent(
    model='gemini-3.1-flash-lite',
    name='sleep_analyst',
    instruction="Analyze sleep logs for REM cycles and recovery quality. Focus on sleep hygiene improvements."
)

exercise_metrics_agent = Agent(
    model='gemini-3.1-flash-lite',
    name='exercise_metrics_analyst',
    instruction="Analyze training volume, intensity, and daily activity metrics (steps, active calories). Focus on physiological strain and daily movement targets."
)

weight_agent = Agent(
    model='gemini-3.1-flash-lite',
    name='weight_analyst',
    instruction="Analyze body composition trends and caloric maintenance levels based on weight logs."
)

# --- Tool Wrappers for Sub-Agents ---

# --- Specialized Tool with Context Injection ---

async def tool_analyze_sleep(query: str) -> str:
    """Specialized tool for deep sleep analysis with real data injection."""
    # Fetch latest raw data to give context to the sub-agent
    raw_sleep_data = await db.sleep_logs.find().sort("date", -1).limit(5).to_list(length=5)
    
    contextual_query = f"User Question: {query}\nRaw Data: {json.dumps(raw_sleep_data, default=str)}"
    
    response = await sleep_agent.run(contextual_query)
    return response.text

async def tool_analyze_exercise_and_metrics(query: str) -> str:
    """Specialized tool for training volume, physical performance, and daily activity metrics."""
    # Inject recent exercise sessions and activity data
    raw_exercise_data = await db.sessions.find().sort("date", -1).limit(10).to_list(length=10)
    
    contextual_query = f"User Question: {query}\nData: {json.dumps(raw_exercise_data, default=str)}"
    
    response = await exercise_metrics_agent.run(contextual_query)
    return response.text

async def tool_analyze_weight(query: str) -> str:
    """Specialized tool for weight trends and body composition analysis."""
    # Inject weight logs (assuming weight_logs collection exists per schema)
    raw_weight_data = await db.weight_logs.find().sort("date", -1).limit(30).to_list(length=30)
    
    contextual_query = f"User Question: {query}\nData: {json.dumps(raw_weight_data, default=str)}"
    
    response = await weight_agent.run(contextual_query)
    return response.text

# --- MCP Tool Integration ---

async def create_profile_via_mcp(user_data_json: str) -> str:
    """
    Creates a user profile in MongoDB using the MCP server.
    Input should be a JSON string containing name, goals, and baseline metrics.
    """
    # Connect to the official MongoDB MCP server via npx
    # Ensure MONGODB_URI is passed in environment variables
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "mongodb-mcp-server"],
        env={**os.environ, "MONGODB_URI": uri}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Using the official 'insert_one' tool from mongodb-mcp-server
            arguments = {
                "database": "habit_os_agent",
                "collection": "user_profiles",
                "document": json.loads(user_data_json)
            }
            return await session.call_tool("insert_one", arguments=arguments)

# --- Main Root Agent ---

root_agent = Agent(
    model='gemini-3.1-flash-lite',
    name='habit_os_control_agent',
    description="Autonomous Physiological Optimization Engine",
    instruction=(
        "You are the Lead Autonomous Controller for Habit-OS. Your goal is to minimize 'metabolic drift' "
        "and maximize athlete performance by coordinating specialized sub-agents. "
        "1. Use 'tool_analyze_sleep', 'tool_analyze_exercise_and_metrics', and 'tool_analyze_weight' for detailed domain analysis. "
        "2. Use 'get_performance_correlation' for high-level physiological sensing. "
        "3. Use 'create_profile_via_mcp' to onboard new users or save processed profiles into MongoDB. "
        "4. If metrics indicate high strain (volume > 8000, sleep < 7h), trigger a 'Deload Phase' recommendation."
    ),
    tools=[
        get_performance_correlation,
        tool_analyze_sleep,
        tool_analyze_exercise_and_metrics,
        tool_analyze_weight,
        create_profile_via_mcp
    ],
)