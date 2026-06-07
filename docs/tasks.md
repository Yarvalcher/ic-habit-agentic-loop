# Habit-OS Implementation Tasks

Based on the roadmap outlined in `ideas.md`, here is the tracked status of all implementation tasks:

## Phase 1: Semantic & Dynamic Intelligence

- [x] **Task 1 & 2: Schema Mapping & Pydantic Validation**
  - Added a static `SCHEMA_MAPPING` to provide semantics.
  - Implemented strict Pydantic models (`UserProfile`, etc.) to validate and clean the MongoDB output, protecting the LLM from bad data.
- [x] **Task 3: Dynamic Windowing**
  - Update `get_performance_correlation` to accept a `days` argument. *(Implemented in `agent.py`)*

## Phase 2: Collaboration & Memory

- [x] **Task 4: Cross-Agent Context**
  - Updated sub-agent tool wrappers to inject the `UserProfile` directly into the payload.
  - Instructed the Root Agent to extract and pass relevant findings across sub-agents in the query string.
- [x] **Task 5: The "Decision Log" (MCP Write)**
  - Updated the root agent's logic to explicitly use the `insert-one` MCP tool to save recommendations ("Plan of Action") into MongoDB.

## Phase 3: Autonomous Monitoring

- [ ] **Task 6: Scheduled Sensing**
  - Implement a cron job or background scheduler that triggers the Brain agent every morning to scan for "Metabolic Drift" and generate notifications proactively.

## Phase 4: Predictive Burnout & Injury Modeling

- [x] **Task 7: The Burnout Risk Model**
  - Created a pure Python mathematical model to calculate strain risk based on quantitative and qualitative data.
  - Implemented full TDD test coverage for edge cases and mathematical bounds.
- [x] **Task 8: Agent Integration**
  - Added `predict_burnout_risk` tool to the Root Agent.
  - Updated Root Agent instructions to proactively recommend a deload session when the Risk Score exceeds 80.
