🔍 Code Review Observations
Semantic Gap: The agent currently receives raw JSON. While Gemini is smart, it may struggle with non-standard field names across long contexts.

Stateless Sub-Agents: When the Brain calls tool_analyze_sleep, the sub-agent gets a "snapshot." If the user asks a follow-up, the sub-agent doesn't inherently see the conversation history unless you pass the history object from the ToolContext.

Hardcoded Logic: Your get_performance_correlation uses a fixed 14-day window. As we discussed, making this dynamic allows the agent to "zoom out" when it detects a trend.

🗺️ Habit-OS Implementation Roadmap
I suggest a three-phase approach to turn this from a functional prototype into a sophisticated physiological sensing system.

Phase 1: Semantic & Dynamic Intelligence (The "Next 48 Hours")
Goal: Bridge the gap between raw data and agentic reasoning.

Task 1: OSI Metadata Integration. Create a metadata collection in MongoDB. Store the OSI schema you shared.

Task 2: The "Prime Directive" Tool. Write a tool get_semantic_mapping(domain: str) that fetches synonyms and field definitions.

Task 3: Dynamic Windowing. Update get_performance_correlation to accept a days argument, allowing the agent to request 7, 30, or 90 days based on the user's question.

Task 4: Cross-Agent Context. Update sub-agent tool wrappers to pass relevant history. If the Sleep Agent knows the Exercise Agent found a "High Volume" week, its recovery analysis will be much more accurate.

Task 5: The "Decision Log" (MCP Write). Instead of just telling the user to "Deload," have the agent use the MCP insert-one to save a recommendations document. This creates a "Plan of Action" the user can actually see in the database.

Task 6: 📝 Project Proposal: Automated Morning Check-In & Context Engine
🎯 Objective
To transition Habit-OS from a reactive system into a proactive context engine by using automated morning scheduling to prompt the user for qualitative insights (mood, plans, subjective energy) and record structured data natively into a MongoDB lifestyle_log.

1. 🔄 The Architectural Loop
Because serverless systems (Google Cloud Run) are stateless and cannot sleep in memory to self-trigger, the interaction is driven via a secure cloud alarm system:

[ Google Cloud Scheduler ]  --- (Daily 8:00 AM Cron / OIDC Authenticated Request) --->
           |
           v
[ Google Cloud Run Service ] ---> (Triggers Outreach Hook: Telegram Bot API / Slack Webhook) --->
           |
           v
   [ User's Phone ] <--- ("Good morning! How are you feeling, and what's your plan today?")
           |
           +--- (User replies with unstructured text: e.g., "Anxious about my 2 PM sync, going running later.")
           |
           v
[ FastAPI Endpoint: /agent/user-response ] ---> (Passes text to Gemini parsing agent) --->
           |
           v
[ MongoDB Atlas (lifestyle_log Collection) ] <--- (Saves structured JSON metadata)

2. 🗄️ Structured Data Mapping (lifestyle_log)
Unstructured user replies are read by Gemini using a strict Pydantic parsing layer to isolate qualitative and quantitative data frames seamlessly.

Python
# Target Schema Representation
{
    "timestamp": "ISODate('2026-06-06T08:05:00Z')",
    "energy_level": "Moderate-Low",
    "mood": "Anxious but Determined",
    "daily_plan": [
        "2:00 PM Team Sync / Presentation",
        "Evening Running / Cardio Session"
    ],
    "raw_reflection": "Anxious about my 2 PM sync, going running later to clear my head.",
    "tags": ["#presentation", "#anxiety", "#cardio_plan"]
}
3. 🔒 Core Infrastructure & Security Components
Cloud Scheduler: Set to trigger a specific private endpoint (e.g., POST /cron/morning-check-in) using a standard cron expression (e.g., 0 8 * * * for 8:00 AM daily).

OIDC Authentication Security: Cloud Scheduler attaches a secure, cryptographic OpenID Connect (OIDC) token to the request header. This ensures your private endpoint blocks the general public with a 403 Forbidden error, responding only to authorized Google Cloud systems.

Continuous Delivery Integration: This new workflow will compile cleanly through your newly fixed GitHub-connected Cloud Build pipeline. Secrets (Gemini API keys, MongoDB write URIs) remain securely decoupled inside Google Secret Manager and will automatically inject at container runtime.

🚀 Why this Elevates Phase 3
By compiling qualitative data (lifestyle_log) directly alongside your physiological metrics (sleep_log, steps_log), your sub-agents can begin correlating biometric patterns to subjective human states. For example, the agent can cross-reference whether an Anxious morning mood log statistically aligns with a drop in deep sleep metrics from the night before!

## Phase 4: Predictive Burnout & Injury Modeling (Executed)
**Objective**: Introduce a proactive "Burnout Risk Score" based on an athlete's physiological (training volume, sleep) and qualitative (mood, stress) data.

**Task 7**: Create a pure, atomic Python function `calculate_burnout_risk_score` using TDD to generate a 0-100 score based on volume spikes, sleep deficits, and consecutive negative mood days.
**Task 8**: Introduce a `predict_burnout_risk` tool in `agent.py` so the Root Agent can preemptively intercept and adjust training plans before overtraining occurs.