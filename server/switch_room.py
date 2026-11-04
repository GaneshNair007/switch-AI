"""Switch Room Core Engine & Chat Bridge Server.
Implements the Switch room state machine, session registration, exclusive role enforcement,
task/decision records, and chat commands (!agents-status, !list-agents, !list-aliases, !roles).
"""
from __future__ import annotations
import json, time, uuid
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from .models import Task, Verdict, VerdictType, CaseState

@dataclass
class AgentSession:
    agent_id: str
    name: str
    alias: str
    location: str
    provider: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "ONLINE"
    last_heartbeat: float = field(default_factory=time.time)

@dataclass
class RoomMessage:
    id: str
    sender: str
    content: str
    timestamp: float = field(default_factory=time.time)
    role: Optional[str] = None

class SwitchRoom:
    def __init__(self, room_name: str = "ship-court", bridge: str = "mattermost"):
        self.room_name = room_name
        self.bridge = bridge
        self.sessions: Dict[str, AgentSession] = {}
        self.aliases: Dict[str, str] = {
            "clerk": "court-clerk",
            "historian": "incident-historian",
            "prosecutor": "prosecutor",
            "defender": "defender",
            "rollback": "rollback-engineer"
        }
        self.messages: List[RoomMessage] = []
        self.exclusive_roles: Dict[str, str] = {"approver": "Priya"} # Human judge holds exclusive approver
        self.tasks: List[Task] = []
        self.decisions: List[Dict[str, Any]] = []
        self.message_listeners: List[Callable[[RoomMessage], None]] = []

    def register_session(self, agent_name: str, alias: str, location: str, provider: str = "claude") -> AgentSession:
        """Register an active agent session into the room."""
        session = AgentSession(
            agent_id=agent_name,
            name=agent_name,
            alias=alias,
            location=location,
            provider=provider
        )
        self.sessions[agent_name] = session
        return session

    def subscribe(self, listener: Callable[[RoomMessage], None]):
        """Subscribe an agent or webhook to room broadcast events."""
        self.message_listeners.append(listener)

    def post_message(self, sender: str, content: str, sender_role: Optional[str] = None) -> RoomMessage:
        """Broadcast a message into the Switch room."""
        msg = RoomMessage(
            id=str(uuid.uuid4())[:8],
            sender=sender,
            content=content,
            role=sender_role
        )
        self.messages.append(msg)
        for listener in list(self.message_listeners):
            try:
                listener(msg)
            except Exception as e:
                print(f"[Switch Room Error] Listener dispatch error: {e}")
        return msg

    def handle_command(self, cmd: str, sender: str) -> Optional[str]:
        """Execute Switch administrative and inspection commands."""
        clean_cmd = cmd.strip()
        if clean_cmd == "!agents-status":
            lines = [f"[ONLINE] Switch Room #{self.room_name} Agent Sessions Status:"]
            for s in self.sessions.values():
                lines.append(f"  * @{s.alias} ({s.name}) | Session: {s.session_id} | Location: {s.location} | Provider: {s.provider} | Status: [{s.status}]")
            return "\n".join(lines)

        elif clean_cmd == "!list-agents":
            lines = [f"[ROSTER] Registered Courtroom Agents in #{self.room_name}:"]
            for s in self.sessions.values():
                lines.append(f"  - {s.name} (Alias: @{s.alias}, Host: {s.location}, Provider: {s.provider})")
            return "\n".join(lines)

        elif clean_cmd == "!list-aliases":
            lines = [f"[ALIASES] Switch Room Aliases:"]
            for alias, target in self.aliases.items():
                lines.append(f"  - @{alias} -> {target}")
            return "\n".join(lines)

        elif clean_cmd == "!roles":
            lines = [f"[ROLES] Switch Room Roles:"]
            for role, assignee in self.exclusive_roles.items():
                lines.append(f"  - {role}: {assignee} (EXCLUSIVE: true -- non-transferable to agents)")
            return "\n".join(lines)

        elif clean_cmd == "!tasks":
            if not self.tasks:
                return "[INFO] No open tasks in this room."
            lines = [f"[TASKS] Switch Assigned Tasks:"]
            for t in self.tasks:
                lines.append(f"  - [{t.status}] {t.description} (Owner: {t.owner})")
            return "\n".join(lines)

        elif clean_cmd == "!decisions":
            if not self.decisions:
                return "[INFO] No recorded decisions in this case."
            lines = [f"[DECISIONS] Switch Auditable Decisions:"]
            for d in self.decisions:
                lines.append(f"  - Case {d.get('case_id')}: {d.get('verdict')} by Judge {d.get('judge')} | Reason: {d.get('reason')}")
            return "\n".join(lines)

        return None

    def enforce_human_verdict_gate(self, sender: str) -> bool:
        """Verify that the sender holds the exclusive approver role."""
        approver = self.exclusive_roles.get("approver")
        # Check if sender matches human approver name
        if sender.lower() == approver.lower():
            return True
        # Explicitly reject agents
        if sender in self.sessions or sender in self.aliases or sender.startswith("court-"):
            return False
        return False

    def record_decision(self, case_id: str, verdict: Verdict):
        """Persist structured decision into Switch storage."""
        record = {
            "case_id": case_id,
            "judge": verdict.judge,
            "verdict": verdict.type.value,
            "reason": verdict.reason or "Release conditions established",
            "timestamp": time.time()
        }
        self.decisions.append(record)
