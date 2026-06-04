# ic-habit-agentic-loop

A Gemini-powered agentic orchestrator that bridges MongoDB Atlas telemetry with science-backed reasoning. The system detects recovery deficits, coordinates specialized sub-agents, and executes programmatic updates to training plans to prevent overtraining.

## Project Structure

```
ic-habit-agentic-loop/
├── README.md                          (Project overview and setup instructions)
├── docs/                              (Documentation, ideas, and tasks)
├── agent_brain/                       (Core: ADK Agents & MongoDB Integration)
│   └── agent.py                       (The main agent architecture)
├── test_agent_mongodb_mcp/            (Core: MongoDB Atlas & MCP Integration)
│   └── agent.py                       (The "agent_brain" - habit_os_brain)
└── test_agent_example/                (Example: Weather and Time utility agent)
    └── agent.py                       (Demonstrates Tool-use and ThinkingConfig)
```

## Architecture Overview

The core logic resides in `agent_brain/agent.py` and is built using the Google ADK (Agent Development Kit). The architecture is designed around a Root Agent that coordinates multiple Specialized Sub-Agents.

### 🧠 The Lead Controller (`habit_os_control_agent`)
An autonomous physiological optimization engine that monitors "metabolic drift" and maximizes athlete performance.
- Evaluates high-level correlations between training volume and sleep (`get_performance_correlation`).
- Uses the `mongodb-mcp-server` (via Model Context Protocol) to seamlessly save recommendations and processed profiles into MongoDB.
- Triggers Deload Phases if metrics indicate high strain.

### 🕵️ Specialized Sub-Agents
The controller delegates domain-specific analysis to these agents using custom tools (`tool_context.run_node`):
- **Sleep Analyst (`sleep_agent`)**: Analyzes sleep hygiene, REM cycles, and recovery quality.
- **Exercise Metrics Analyst (`exercise_metrics_agent`)**: Analyzes training volume, physiological strain, and daily movement.
- **Weight Analyst (`weight_agent`)**: Tracks body composition trends and caloric maintenance levels.

### 🔒 Security and Database Integration
- **GCP Secret Manager**: Securely fetches the `GEMINI_API` key and `mongodb_url` using Google Application Default Credentials (ADC).
- **Direct MongoDB Integration**: Uses `motor` (async MongoDB driver) to fetch recent telemetry logs and feed them directly into the sub-agent context payloads.

## Getting Started

### Prerequisites

1.  **Google Cloud Platform**: You must be authenticated with GCP to access Secret Manager.
    ```bash
    gcloud auth application-default login
    ```
2.  **Node.js**: Required to run the `mongodb-mcp-server` (triggered via `npx`).
3.  **Python 3.10+** and the ADK dependencies.

### Running the Project

You can run the agent locally using the ADK development server.

1.  **Start the ADK Web UI**:
    Navigate to the root directory and start the server:
    ```bash
    adk web --port 8000
    ```
2.  **Interact with the Agent**:
    Open the provided URL (e.g., `http://localhost:8000`) in your browser to interact with the `habit_os_control_agent` and observe the sub-agent coordination in action.
