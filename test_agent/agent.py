import os
import json
import asyncio
from google.cloud import secretmanager
from google.adk.agents.llm_agent import Agent
from google.adk.agents.base_agent import AgentInput

# --- 1. SECRETS MANAGEMENT ---
def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    project_id = "12654003615"
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

os.environ["GOOGLE_API_KEY"] = get_secret("GEMINI_API")

# --- 2. SUB-AGENT DEFINITION ---
specialist_agent = Agent(
    model='gemini-3.1-flash-lite', 
    name="specialist_analyst",
    instruction="Summarize the input provided to you concisely."
)

# --- 3. TOOL DEFINITION (The Orchestration Logic) ---
async def call_specialist_tool(user_query: str) -> str:
    """
    Invokes the specialist sub-agent.
    Uses AgentInput to satisfy the '1 positional argument' requirement.
    """
    # Create the explicit Input Object
    # This ensures ADK sees exactly ONE argument (the object)
    agent_input = AgentInput(input=user_query)
    
    final_text = ""
    
    # Iterate through the stream using the explicit input object
    async for event in specialist_agent.run(agent_input):
        if hasattr(event, 'output') and event.output:
            if hasattr(event.output, 'text'):
                final_text = event.output.text
            else:
                final_text = str(event.output)
                
    return final_text if final_text else "Error: No response."

# --- 4. ROOT AGENT ---
root_agent = Agent(
    model='gemini-3.1-flash-lite',
    name="orchestration_tester",
    instruction="Delegate analysis to 'call_specialist_tool' and present findings.",
    tools=[call_specialist_tool]
)