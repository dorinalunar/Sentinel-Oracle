# Sentinel Oracle 🛡️
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

## Deployment & Testing Guide

You can easily deploy and test this contract using the GenLayer Studio simulator. Since this is a multi-agent oracle, you will need **two wallet addresses** to complete a full consensus cycle.

### 1. Deploy the Contract
* Open [GenLayer Studio](https://studio.genlayer.com/) (or your local GenLayer environment).
* Upload `SentinelOracle.py`.
* Click **Deploy new instance** and wait for the transaction to be accepted.

### 2. Establish a Mission (Wallet 1)
From the **Write Methods** section, call `establish_mission` to initialize a task:
* `mission_id`: `test-mission-01`
* `description`: `What is the main topic of the example.com domain?`
* `outcomes_json`: `["DOMAINS", "WEATHER", "CRYPTO"]`
* `agents_json`: `["0xYourWalletAddress1...", "0xYourWalletAddress2..."]`

### 3. Join the Mission (Wallet 2)
* Switch your active account in the simulator to the **second wallet address**.
* Call `join_mission` with the `mission_id`: `test-mission-01`.

### 4. Provide Evidence (Both Wallets)
Both agents must submit their web evidence before the AI can run. **Execute this step once from Wallet 1, and once from Wallet 2:**
* Call `provide_evidence`.
* `mission_id`: `test-mission-01`
* `source_link`: `https://example.com`
* `content_hash`: `ea8fac7c65fb589b0d53560f5251f74f9e9b243478dcb6b3ea79b5e36449c8d9` *(Valid SHA-256 for example.com)*

### 5. Execute AI Consensus
From any of the participating wallets, call `execute_consensus`:
* `mission_id`: `test-mission-01`
* *Note: During this transaction, the GenLayer nodes will perform HTTP requests, execute the LLM prompt, and cryptographically verify the consensus.*

### 6. Verify the Outcome
Navigate to the **Read State** section to see the AI's decision:
* Call `fetch_resolution` with `mission_id`: `test-mission-01` and `cycle`: `1`.
* The returned JSON will display the `resolution_status` (e.g., `CONVERGED`) and the `agreed_outcome` (e.g., `DOMAINS`).
