# SentinelOracle Architecture & Consensus Flow

This document details the underlying state machine, threat modeling, and execution stages of SentinelOracle.

## Lifecycle Flow

```text
[ Initiator ] 
      │ 
      ▼ establish_mission()
 [ PENDING ] 
      │
      ├──> [ Agents ] ──> join_mission()
      │
      ├──> (Optional) initiator ──> evict_unresponsive_agent()
      │
      ▼ provide_evidence(URL, content_hash)
 [ READY FOR SYNC ]
      │
      ▼ execute_consensus()
┌────────────────────────────────────────┐
│ GenLayer Non-Deterministic Environment │
│ 1. Leader fetches URL & prompts LLM    │
│ 2. Validators verify & re-execute      │
│ 3. Unanimous agreement checked         │
└────────────────────────────────────────┘
      │
      ├── (All Match)    ──> [ CONVERGED ] (Outcome stored)
      └── (Disagreement) ──> [ DIVERGED ]  (Logged as UNRESOLVED)
