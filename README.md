# ic-habit-agentic-loop

A Gemini-powered agentic orchestrator that bridges MongoDB Atlas telemetry with science-backed reasoning. Using a custom MCP (Model Context Protocol) implementation on Google Cloud, the system detects recovery deficits and executes programmatic updates to training plans to prevent overtraining.

## Project Structure

```
ic-habit-agentic-loop/
├── README.md                          (This file: Project overview and setup instructions)
├── agent_brain           /            (Core: MongoDB Atlas & MCP Integration)
│   └── agent.py                       (The "agent_brain" - habit_os_brain)
├── test_agent_mongodb_mcp/            (Core: MongoDB Atlas & MCP Integration)
│   └── agent.py                       (The "agent_brain" - habit_os_brain)
└── test_agent_example/                (Example: Weather and Time utility agent)
    └── agent.py                       (Demonstrates Tool-use and ThinkingConfig)
```

### Detailed Description

The `ic-habit-agentic-loop` project implements a Gemini-powered agentic orchestrator designed to integrate MongoDB Atlas telemetry with science-backed reasoning. It leverages a custom MCP implementation on Google Cloud to intelligently detect recovery deficits in user data (such as sleep, exercise, and weight). The system then programmatically updates training plans to prevent overtraining, making it a smart assistant for habit and health management.

The `test_agent_mongodb_mcp/agent.py` file is central, configuring an `LlmAgent` named `habit_os_brain`. This agent is set up with specific instructions to analyze user data from MongoDB using a `McpToolset`. This toolset enables the agent to perform `find` operations to retrieve recent logs and `insert-one` operations to create new user profiles directly within MongoDB, facilitating dynamic interaction with the user's habit data. It also uses GCP Secret Manager for secure retrieval of API keys and connection strings.
