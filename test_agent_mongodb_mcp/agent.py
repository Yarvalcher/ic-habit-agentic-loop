import os
from google.cloud import secretmanager
from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# --- 1. SECRET RETRIEVAL FUNCTION ---
def get_secret(secret_id):
    """Retrieves secrets from GCP Secret Manager using ADC."""
    client = secretmanager.SecretManagerServiceClient()
    project_id = "12654003615"
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# --- 2. ENVIRONMENT SETUP ---
# Retrieve the Gemini API key and MongoDB URL
os.environ["GOOGLE_API_KEY"] = get_secret("GEMINI_API")
CONNECTION_STRING = get_secret("mongodb_url")

# --- 3. ROOT AGENT WITH MCP TOOLSET ---
root_agent = Agent(
    model="gemini-3.1-flash-lite",
    name="habit_os_brain",
    instruction=(
        "You are the main intellectual center for Habit-OS. Your duty is to analyze "
        "user data regarding sleep, exercise, and weight directly from MongoDB. "
        "Use the 'find' tool to search for recent logs and 'insert-one' "
        "to create new user profiles."
    ),
    tools=[
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
                        "MDB_MCP_CONNECTION_STRING": CONNECTION_STRING,
                    },
                ),
                timeout=30,
            ),
        )
    ],
)