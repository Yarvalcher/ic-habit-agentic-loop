import os
import asyncio
from google.adk.agents.llm_agent import Agent
from motor.motor_asyncio import AsyncIOMotorClient
from google.cloud import secretmanager
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
import json

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

from google.adk.tools.tool_context import ToolContext

def _extract_text(result) -> str:
    if hasattr(result, "text"):
        return result.text
    if isinstance(result, str):
        return result
    return str(result)

async def tool_analyze_sleep(query: str, tool_context: ToolContext) -> str:
    """Specialized tool using the ADK-native run pattern."""
    # Fetch latest raw data to give context to the sub-agent
    raw_sleep_data = await db.sleep_logs.find().sort("date", -1).limit(5).to_list(length=5)
    
    payload = f"User Question: {query}\nRaw Data: {json.dumps(raw_sleep_data, default=str)}"
    
    # Use ADK's run_node to make the sub-agent a First Class Citizen in Traces
    result = await tool_context.run_node(sleep_agent, node_input=payload)
    return _extract_text(result)

async def tool_analyze_exercise_and_metrics(query: str, tool_context: ToolContext) -> str:
    """Specialized tool for training volume, physical performance, and daily activity metrics."""
    # Inject recent exercise sessions and activity data
    raw_exercise_data = await db.sessions.find().sort("date", -1).limit(10).to_list(length=10)
    
    payload = f"User Question: {query}\nData: {json.dumps(raw_exercise_data, default=str)}"
    result = await tool_context.run_node(exercise_metrics_agent, node_input=payload)
    return _extract_text(result)

async def tool_analyze_weight(query: str, tool_context: ToolContext) -> str:
    """Specialized tool for weight trends and body composition analysis."""
    # Inject weight logs (assuming weight_logs collection exists per schema)
    raw_weight_data = await db.weight_logs.find().sort("date", -1).limit(30).to_list(length=30)
    
    payload = f"User Question: {query}\nData: {json.dumps(raw_weight_data, default=str)}"
    result = await tool_context.run_node(weight_agent, node_input=payload)
    return _extract_text(result)

# --- MCP Tool Integration ---

# We now use McpToolset directly in the agent's tools array
# instead of manually writing a Python wrapper for insert_one!

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
        "3. Use the 'insert-one' tool from the MongoDB MCP server to onboard new users or save processed profiles into MongoDB. "
        "4. If metrics indicate high strain (volume > 8000, sleep < 7h), trigger a 'Deload Phase' recommendation."
    ),
    tools=[
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