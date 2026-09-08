# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass
import hashlib
import json

LIMIT_AGENTS = 8
LIMIT_OUTCOMES = 12
MAX_PAYLOAD = 20000
ORACLE_POLICY = "sentinel-strict-consensus-final"

@allow_storage
@dataclass
class Mission:
    initiator: Address
    description: str
    outcomes_json: str
    invited_json: str
    roster_json: str
    current_cycle: u64
    latest_resolution_id: str
    latest_status: str

@allow_storage
@dataclass
class Evidence:
    mission_id: str
    cycle: u64
    provider: Address
    source_link: str
    content_hash: str

@allow_storage
@dataclass
class Resolution:
    mission_id: str
    cycle: u64
    status: str
    agreed_outcome: str
    details_json: str
    checksum: str

class SentinelOracle(gl.Contract):
    missions: TreeMap[str, Mission]
    has_mission: TreeMap[str, bool]

    evidences: TreeMap[str, Evidence]
    has_evidence: TreeMap[str, bool]

    resolutions: TreeMap[str, Resolution]
    has_resolution: TreeMap[str, bool]

    def __init__(self) -> None:
        pass

    # ---------------------------------------------------------
    # MISSION MANAGEMENT
    # ---------------------------------------------------------

    @gl.public.write
    def establish_mission(
        self,
        mission_id: str,
        description: str,
        outcomes_json: str,
        agents_json: str
    ) -> None:
        m_id = self._validate_slug(mission_id)
        outcomes = self._parse_strings(outcomes_json, 2, LIMIT_OUTCOMES, "outcomes")
        invited = self._parse_addresses(agents_json)

        if self.has_mission.get(m_id, False):
            raise gl.vm.UserError("REJECTED: Mission ID already in use")
        if "UNDETERMINED" in outcomes:
            raise gl.vm.UserError("REJECTED: 'UNDETERMINED' is a reserved keyword")

        sender = str(gl.message.sender_address).lower()
        roster = {
            str(address).lower(): (str(address).lower() == sender)
            for address in invited
        }

        self.missions[m_id] = Mission(
            initiator=gl.message.sender_address,
            description=self._clean_text(description),
            outcomes_json=json.dumps(outcomes, separators=(",", ":")),
            invited_json=json.dumps([str(a).lower() for a in invited], separators=(",", ":")),
            roster_json=json.dumps(roster, sort_keys=True, separators=(",", ":")),
            current_cycle=u64(1),
            latest_resolution_id="",
            latest_status="PENDING"
        )
        self.has_mission[m_id] = True

    @gl.public.write
    def join_mission(self, mission_id: str) -> None:
        m_id = self._validate_slug(mission_id)
        mission = self._get_mission(m_id)
        sender = str(gl.message.sender_address).lower()
        invited_list = json.loads(mission.invited_json)

        if sender not in invited_list:
            raise gl.vm.UserError("REJECTED: Not on the invitation list")

        roster = json.loads(mission.roster_json)
        if sender not in roster:
            raise gl.vm.UserError("REJECTED: Agent roster state is inconsistent")

        roster[sender] = True
        mission.roster_json = json.dumps(roster, sort_keys=True, separators=(",", ":"))
        self.missions[m_id] = mission

    @gl.public.write
    def evict_unresponsive_agent(self, mission_id: str, target_agent: str) -> None:
        m_id = self._validate_slug(mission_id)
        mission = self._get_mission(m_id)
        sender = str(gl.message.sender_address).lower()

        if sender != str(mission.initiator).lower():
            raise gl.vm.UserError("REJECTED: Only the initiator can evict agents")

        target = str(target_agent).strip().lower()
        roster = json.loads(mission.roster_json)

        if target not in roster:
            raise gl.vm.UserError("REJECTED: Target agent not in roster")
        if len(roster) <= 2:
            raise gl.vm.UserError("REJECTED: A mission requires at least 2 active agents")

        del roster[target]
        mission.roster_json = json.dumps(roster, sort_keys=True, separators=(",", ":"))
        self.missions[m_id] = mission

    # ---------------------------------------------------------
    # EVIDENCE
    # ---------------------------------------------------------

    @gl.public.write
    def provide_evidence(self, mission_id: str, source_link: str, content_hash: str) -> None:
        m_id = self._validate_slug(mission_id)
        mission = self._get_mission(m_id)
        sender = str(gl.message.sender_address).lower()
        roster = json.loads(mission.roster_json)

        if not roster.get(sender, False):
            raise gl.vm.UserError("REJECTED: You must join the mission first")

        key = self._build_evidence_key(m_id, mission.current_cycle, sender)
        if self.has_evidence.get(key, False):
            raise gl.vm.UserError("REJECTED: Evidence already provided for this cycle")

        self.evidences[key] = Evidence(
            mission_id=m_id,
            cycle=mission.current_cycle,
            provider=gl.message.sender_address,
            source_link=self._validate_url(source_link),
            content_hash=self._validate_hash(content_hash)
        )
        self.has_evidence[key] = True

    # ---------------------------------------------------------
    # CONSENSUS ENGINE & LLM
    # ---------------------------------------------------------

    @gl.public.write
    def execute_consensus(self, mission_id: str) -> None:
        m_id = self._validate_slug(mission_id)
        mission = self._get_mission(m_id)
        roster = json.loads(mission.roster_json)

        if len(roster) < 2:
            raise gl.vm.UserError("REJECTED: A mission requires at least 2 active agents")
        if not all(roster.values()):
            raise gl.vm.UserError("REJECTED: Awaiting pending invitations to be accepted or evicted")

        for agent in roster.keys():
            evidence_key = self._build_evidence_key(m_id, mission.current_cycle, agent)
            if not self.has_evidence.get(evidence_key, False):
                raise gl.vm.UserError("REJECTED: Not all active agents have submitted evidence")

        resolution_data = self._process_llm_consensus(m_id, mission)

        if not self._verify_schema(resolution_data, m_id, mission):
            raise gl.vm.UserError("CRITICAL: Consensus schema validation failed")

        payload_string = json.dumps(resolution_data, sort_keys=True, separators=(",", ":"))
        res_id = f"{m_id}:{int(mission.current_cycle)}"

        record = Resolution(
            mission_id=m_id,
            cycle=mission.current_cycle,
            status=resolution_data["resolution_status"],
            agreed_outcome=resolution_data["agreed_outcome"],
            details_json=payload_string,
            checksum=hashlib.sha256(payload_string.encode()).hexdigest()
        )

        self.resolutions[res_id] = record
        self.has_resolution[res_id] = True
        mission.latest_resolution_id = res_id
        mission.latest_status = record.status
        mission.current_cycle += u64(1)
        self.missions[m_id] = mission

    def _process_llm_consensus(self, m_id, mission):
        def _run_leader():
            roster = json.loads(mission.roster_json)
            outcomes = json.loads(mission.outcomes_json)
            logs = []

            for agent in sorted(roster.keys()):
                evidence_key = self._build_evidence_key(m_id, mission.current_cycle, agent)
                evidence = self.evidences[evidence_key]
                web_data = self._grab_web_content(evidence.source_link)
                
                hash_match = (web_data["fingerprint"] == evidence.content_hash)
                evaluated_belief = "UNDETERMINED"

                # LLM is executed if the network request is successful, 
                # tolerating dynamic page changes while logging the hash match status.
                if web_data["network_status"] == "SUCCESS":
                    prompt = (
                        f"Mission: {mission.description}\n"
                        f"Allowed Outcomes: {json.dumps(outcomes)}\n"
                        f"Source Data: {web_data['content']}\n\n"
                        "Act as a strict deterministic classifier. "
                        "Analyze the Source Data and map it to exactly ONE of the Allowed Outcomes.\n"
                        "Ignore minor variations, ads, or updated timestamps in the text.\n"
                        "Do not invent facts. Do not return explanations.\n"
                        "Return ONLY JSON in this exact form: {\"outcome\":\"...\"}"
                    )
                    llm_reply = gl.nondet.exec_prompt(prompt, response_format="json")

                    if isinstance(llm_reply, dict):
                        raw_outcome = str(llm_reply.get("outcome", "UNDETERMINED")).strip().upper()
                        if raw_outcome in outcomes:
                            evaluated_belief = raw_outcome

                logs.append({
                    "agent": agent,
                    "fetch_status": web_data["network_status"],
                    "http_code": web_data["http_code"],
                    "hash_verified": hash_match,
                    "agent_belief": evaluated_belief
                })

            beliefs = [log["agent_belief"] for log in logs]
            is_unanimous = (len(beliefs) > 0 and "UNDETERMINED" not in beliefs and all(belief == beliefs[0] for belief in beliefs))

            payload = {
                "engine_policy": ORACLE_POLICY,
                "mission_id": m_id,
                "cycle_number": int(mission.current_cycle),
                "outcomes": outcomes,
                "total_participants": len(roster),
                "agent_logs": logs,
                "agreed_outcome": beliefs[0] if is_unanimous else "UNDETERMINED",
                "resolution_status": "CONVERGED" if is_unanimous else "DIVERGED"
            }
            payload["security_hash"] = self._calculate_security_hash(payload)
            return payload

        def _run_validator(leader_output):
            if not isinstance(leader_output, gl.vm.Return): return False
            leader_data = leader_output.calldata
            
            # The validator MUST run its own execution to prevent malicious leaders from forging the JSON.
            validator_data = _run_leader()
            
            return (self._verify_schema(leader_data, m_id, mission) and 
                    self._verify_schema(validator_data, m_id, mission) and 
                    leader_data == validator_data)

        consensus_result = gl.vm.run_nondet_unsafe(_run_leader, _run_validator)

        if not self._verify_schema(consensus_result, m_id, mission):
            raise gl.vm.UserError("CRITICAL: LLM non-deterministic failure or schema mismatch")
        return consensus_result

    # ---------------------------------------------------------
    # STRICT SCHEMA / INTEGRITY VALIDATION
    # ---------------------------------------------------------

    def _verify_schema(self, data, m_id, mission):
        if not isinstance(data, dict): return False
        try:
            roster = json.loads(mission.roster_json)
            outcomes = json.loads(mission.outcomes_json)
            roster_agents = sorted(str(agent).lower() for agent in roster.keys())

            if data.get("engine_policy") != ORACLE_POLICY: return False
            if data.get("mission_id") != m_id: return False
            if int(data.get("cycle_number", -1)) != int(mission.current_cycle): return False
            if int(data.get("total_participants", -1)) != len(roster): return False
            if data.get("resolution_status") not in ("CONVERGED", "DIVERGED"): return False
            if not isinstance(data.get("outcomes"), list): return False
            if data["outcomes"] != outcomes: return False

            logs = data.get("agent_logs")
            if not isinstance(logs, list) or len(logs) != len(roster): return False

            logged_agents = []
            for log in logs:
                if not isinstance(log, dict): return False
                for field in ("agent", "fetch_status", "http_code", "hash_verified", "agent_belief"):
                    if field not in log: return False

                agent = str(log["agent"]).lower()
                if agent not in roster: return False
                logged_agents.append(agent)

                if log["fetch_status"] not in ("SUCCESS", "FAILED"): return False
                if not isinstance(log["hash_verified"], bool): return False
                if not isinstance(log["http_code"], int): return False

                belief = str(log["agent_belief"]).upper()
                if belief != "UNDETERMINED" and belief not in outcomes: return False

            if sorted(logged_agents) != roster_agents: return False

            beliefs = [str(log["agent_belief"]).upper() for log in logs]
            expected_unanimous = (len(beliefs) > 0 and "UNDETERMINED" not in beliefs and all(b == beliefs[0] for b in beliefs))
            expected_status = "CONVERGED" if expected_unanimous else "DIVERGED"
            expected_outcome = beliefs[0] if expected_unanimous else "UNDETERMINED"

            if data.get("resolution_status") != expected_status: return False
            if data.get("agreed_outcome") != expected_outcome: return False

            supplied_hash = str(data.get("security_hash", "")).lower()
            if len(supplied_hash) != 64 or any(c not in "0123456789abcdef" for c in supplied_hash): return False

            payload_without_hash = dict(data)
            del payload_without_hash["security_hash"]
            expected_hash = self._calculate_security_hash(payload_without_hash)

            if supplied_hash != expected_hash: return False
            return True

        except Exception:
            return False

    # ---------------------------------------------------------
    # VIEWS
    # ---------------------------------------------------------

    @gl.public.view
    def fetch_mission(self, mission_id: str) -> Mission:
        return self._get_mission(self._validate_slug(mission_id))

    @gl.public.view
    def fetch_resolution(self, mission_id: str, cycle: u64) -> Resolution:
        key = f"{self._validate_slug(mission_id)}:{int(cycle)}"
        if not self.has_resolution.get(key, False):
            raise gl.vm.UserError("REJECTED: Resolution not found")
        return self.resolutions[key]

    # ---------------------------------------------------------
    # UTILITIES
    # ---------------------------------------------------------

    def _calculate_security_hash(self, payload: dict) -> str:
        payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload_str.encode()).hexdigest()

    def _grab_web_content(self, url: str) -> dict:
        try:
            res = gl.nondet.web.get(url)
            code = int(getattr(res, "status_code", getattr(res, "status", 0)))
            text = res.body.decode("utf-8", errors="ignore")[:MAX_PAYLOAD]
            is_valid = 200 <= code < 300 and len(text) > 0
            return {
                "network_status": "SUCCESS" if is_valid else "FAILED",
                "http_code": code,
                "fingerprint": hashlib.sha256(text.encode()).hexdigest(),
                "content": text if is_valid else ""
            }
        except Exception:
            return {"network_status": "FAILED", "http_code": 0, "fingerprint": hashlib.sha256(b"").hexdigest(), "content": ""}

    def _parse_addresses(self, text: str):
        try: raw = json.loads(text)
        except Exception: raise gl.vm.UserError("REJECTED: Invalid agent format")
        if not isinstance(raw, list) or not (2 <= len(raw) <= LIMIT_AGENTS): raise gl.vm.UserError(f"REJECTED: Must be 2 to {LIMIT_AGENTS} agents")
        validated = []
        for val in raw:
            addr = Address(str(val))
            if str(addr).lower() in [str(x).lower() for x in validated]: raise gl.vm.UserError("REJECTED: Duplicate agents found")
            validated.append(addr)
        if str(gl.message.sender_address).lower() not in [str(x).lower() for x in validated]:
            raise gl.vm.UserError("REJECTED: Initiator must be included in the roster")
        return validated

    def _parse_strings(self, text: str, min_len: int, max_len: int, label: str):
        try: raw = json.loads(text)
        except Exception: raise gl.vm.UserError(f"REJECTED: Invalid {label} JSON")
        if not isinstance(raw, list) or not (min_len <= len(raw) <= max_len): raise gl.vm.UserError(f"REJECTED: {label} length out of bounds")
        validated = sorted(set(self._clean_text(str(x)).upper() for x in raw))
        if len(validated) != len(raw): raise gl.vm.UserError(f"REJECTED: Duplicate items in {label}")
        return validated

    def _get_mission(self, m_id: str) -> Mission:
        if not self.has_mission.get(m_id, False): raise gl.vm.UserError("REJECTED: Mission does not exist")
        return self.missions[m_id]

    def _build_evidence_key(self, m_id: str, cycle: u64, agent: str) -> str:
        return f"{m_id}:{int(cycle)}:{str(agent).lower()}"

    def _validate_slug(self, val: str) -> str:
        cleaned = val.strip()
        if not (1 <= len(cleaned) <= 80): raise gl.vm.UserError("REJECTED: Slug must be 1-80 chars")
        return cleaned

    def _clean_text(self, val: str) -> str:
        cleaned = val.strip()
        if not (1 <= len(cleaned) <= 1000): raise gl.vm.UserError("REJECTED: Text length out of bounds")
        return cleaned

    def _validate_hash(self, val: str) -> str:
        cleaned = val.strip().lower()
        if len(cleaned) != 64 or any(c not in "0123456789abcdef" for c in cleaned): raise gl.vm.UserError("REJECTED: Invalid SHA-256 hash")
        return cleaned

    def _validate_url(self, val: str) -> str:
        cleaned = val.strip()
        if len(cleaned) > 512 or not cleaned.startswith("https://") or "localhost" in cleaned.lower() or "127.0.0.1" in cleaned:
            raise gl.vm.UserError("REJECTED: Invalid or unsafe URL")
        return cleaned