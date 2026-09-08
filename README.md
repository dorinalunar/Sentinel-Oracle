# SentinelOracle 🛡️
![GenLayer](https://img.shields.io/badge/Network-GenLayer-blue)
![Language](https://img.shields.io/badge/Language-Python-green)
![License](https://img.shields.io/badge/License-MIT-purple)
## Overview
**SentinelOracle** is a decentralized AI consensus oracle on GenLayer. It enables multi-agent missions to verify off-chain web data using LLM classification, cryptographic hash commitments, and strict deterministic validation without relying on trusted intermediaries.
By leveraging GenLayer's non-deterministic execution environment, SentinelOracle seamlessly bridges the gap between dynamic web data and immutable blockchain state.
---
## Key Features
*   **Strict AI Consensus:** Employs a robust LLM validation schema requiring unanimous agreement among participating agents to prevent hallucinations or malicious outputs.
*   **Cryptographic Integrity:** Secures all submitted evidence and resolution states using SHA-256 fingerprinting, ensuring complete data immutability.
*   **Anti-Stalling Mechanism:** Features dynamic roster management allowing the mission initiator to evict unresponsive agents, completely eliminating liveness failures.
*   **Web Volatility Tolerance:** Intelligently separates network availability from byte-perfect hash matching, allowing the AI to successfully process slightly altered dynamic web pages (e.g., updated timestamps).
---
## Mission Workflow
1.  **Establish Mission:** The initiator creates a mission via `establish_mission`, defining the prompt, a strict list of allowed outcomes, and inviting 2 to 8 agents.
2.  **Agent Onboarding:** Invited agents call `join_mission` to confirm their active participation and lock in the roster.
3.  **Evidence Submission:** Each agent executes `provide_evidence`, committing a source URL and the SHA-256 hash of the content they are referencing.
4.  **Consensus Execution:** Anyone can trigger `execute_consensus`. The GenLayer engine autonomously fetches the URLs, processes the text through a strict LLM classifier, and validates the schema across nodes to reach a final `CONVERGED` or `DIVERGED` state.
---
## Technical Architecture

| Component | Implementation Details |
| :--- | :--- |
| **State Storage** | Utilizes GenLayer's `@allow_storage` and `TreeMap` for highly optimized, gas-efficient state tracking. |
| **AI Integration** | Executes `gl.nondet.exec_prompt` with forced JSON formatting to guarantee strict data typing and predictability. |
| **Network Engine** | Uses `gl.nondet.web.get` wrapped in extensive error handling to gracefully manage HTTP failures or timeouts. |
| **Consensus Security** | Implements a robust Leader-Validator verification model via `gl.vm.run_nondet_unsafe`. |
