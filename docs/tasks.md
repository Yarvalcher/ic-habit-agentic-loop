# Habit-OS Implementation Tasks

Based on the roadmap outlined in `ideas.md`, here is the tracked status of all implementation tasks:

## Phase 1: Semantic & Dynamic Intelligence

- [ ] **Task 1: OSI Metadata Integration**
  - Create a metadata collection in MongoDB.
  - Store the OSI schema to provide context to the agent.
- [ ] **Task 2: The "Prime Directive" Tool**
  - Write a tool `get_semantic_mapping(domain: str)` that fetches synonyms and field definitions to help the agent understand raw JSON.
- [x] **Task 3: Dynamic Windowing**
  - Update `get_performance_correlation` to accept a `days` argument. *(Already implemented in `agent.py`)*

## Phase 2: Collaboration & Memory

- [ ] **Task 4: Cross-Agent Context**
  - Update sub-agent tool wrappers (`tool_analyze_sleep`, `tool_analyze_exercise_and_metrics`, etc.) to pass relevant conversation history or insights discovered by other agents into the `ToolContext`.
- [ ] **Task 5: The "Decision Log" (MCP Write)**
  - Update the root agent's logic/prompt to explicitly use the `insert-one` MCP tool to save a recommendations document ("Plan of Action") into MongoDB.

## Phase 3: Autonomous Monitoring

- [ ] **Task 6: Scheduled Sensing**
  - Implement a cron job or background scheduler that triggers the Brain agent every morning to scan for "Metabolic Drift" and generate notifications proactively.
