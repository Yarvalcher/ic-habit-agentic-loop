# ic-habit-agentic-loop

A Gemini-powered agentic orchestrator that bridges MongoDB Atlas telemetry with science-backed reasoning. The system detects recovery deficits, coordinates specialized sub-agents, and executes programmatic updates to training plans to prevent overtraining.

Agent generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) version `0.41.3`

## Project Structure

```
ic-habit-agentic-loop/
├── app/                               (Core agent code)
│   ├── agent.py                       (The main agent architecture)
│   ├── fast_api_app.py                (FastAPI Backend server)
│   └── app_utils/                     (App utilities and helpers)
├── docs/                              (Documentation, ideas, and tasks)
├── tests/                             (Unit, integration, and load tests)
├── GEMINI.md                          (AI-assisted development guide)
├── Makefile                           (Development commands)
└── pyproject.toml                     (Project dependencies)
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Architecture Overview

The core logic resides in `app/agent.py` and is built using the Google ADK (Agent Development Kit). The architecture is designed around a Root Agent that coordinates multiple Specialized Sub-Agents.

### 🧠 The Lead Controller (`habit_os_control_agent`)
An autonomous physiological optimization engine that monitors "metabolic drift" and maximizes athlete performance.
- Retrieves global user profiles via `get_active_user_profile` to ground its recommendations in the athlete's goals, age, and dietary strategy.
- Evaluates high-level correlations between training volume and sleep (`get_performance_correlation`).
- Uses the `mongodb-mcp-server` (via Model Context Protocol) to seamlessly save recommendations and processed profiles into MongoDB (The "Decision Log").
- Triggers Deload Phases if metrics indicate high strain.

### 🕵️ Specialized Sub-Agents
The controller delegates domain-specific analysis to these agents using custom tools (`tool_context.run_node`). Sub-agents now receive a strict Pydantic-validated `UserProfile` context and cross-agent findings in their payload:
- **Sleep Analyst (`sleep_agent`)**: Analyzes sleep hygiene, REM cycles, and recovery quality.
- **Exercise Metrics Analyst (`exercise_metrics_agent`)**: Analyzes training volume, physiological strain, and daily movement.
- **Weight Analyst (`weight_agent`)**: Tracks body composition trends and caloric maintenance levels.

### 🔒 Security, Validation, and Database Integration
- **GCP Secret Manager**: Securely fetches the `GEMINI_API` key and `mongodb_url` using Google Application Default Credentials (ADC).
- **Direct MongoDB Integration & Pydantic**: Uses `motor` (async MongoDB driver) to fetch recent telemetry logs. Data is strictly validated and cleaned using `pydantic` models before being fed into sub-agent contexts, protecting the LLM from bad data.

## Getting Started

### Prerequisites

Before you begin, ensure you have:
1.  **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/)
2.  **Google Cloud Platform**: You must be authenticated with GCP to access Secret Manager.
    ```bash
    gcloud auth application-default login
    ```
    or [Install Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3.  **Node.js**: Required to run the `mongodb-mcp-server` (triggered via `npx`).
4.  **make**: Build automation tool - [Install](https://www.gnu.org/software/make/) (pre-installed on most Unix-based systems)
5.  **Python 3.10+**

### Quick Start

Install required packages and launch the local development environment:

```bash
make install && make playground
```

### Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `make install`       | Install dependencies using uv                                                               |
| `make playground`    | Launch local development environment                                                        |
| `make lint`          | Run code quality checks                                                                     |
| `make test`          | Run unit and integration tests                                                              |
| `make deploy`        | Deploy agent to Cloud Run                                                                   |
| `make local-backend` | Launch local development server with hot-reload                                             |

For full command options and usage, refer to the [Makefile](Makefile).

### ADK Web UI
You can also run the agent locally using the ADK development server:
1.  **Start the ADK Web UI**:
    Navigate to the root directory and start the server:
    ```bash
    adk web --port 8000
    ```
2.  **Interact with the Agent**:
    Open the provided URL (e.g., `http://localhost:8000`) in your browser to interact with the `habit_os_control_agent` and observe the sub-agent coordination in action.

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `uvx agent-starter-pack enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `uvx agent-starter-pack setup-cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `uvx agent-starter-pack upgrade` | Auto-upgrade to latest version while preserving customizations |
| `uvx agent-starter-pack extract` | Extract minimal, shareable version of your agent |

---

## Development

Edit your agent logic in `app/agent.py` and test with `make playground` - it auto-reloads on save.
See the [development guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/development-guide) for the full workflow.

## Deployment

```bash
gcloud config set project <your-project-id>
make deploy
```

To add CI/CD and Terraform, run `uvx agent-starter-pack enhance`.
To set up your production infrastructure, run `uvx agent-starter-pack setup-cicd`.
See the [deployment guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/deployment) for details.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.
See the [observability guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/observability) for queries and dashboards.
# Updated Trigger
