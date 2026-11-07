from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional
from .bridge_connector import ChatBridgeConnector
from .switch_room import SwitchRoom


class FloorState(str, Enum):
    LISTENING = "listening"
    EVALUATING = "evaluating"
    HAND_RAISED = "hand_raised"
    WAITING = "waiting"
    GRANTED = "granted"
    SPEAKING = "speaking"
    YIELDING = "yielding"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class FloorRequest:
    request_id: str
    meeting_id: str
    agent_id: str
    intent: str
    emoji: str
    reason: str
    spoken_script: str
    priority: int
    evidence_refs: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 90.0)
    state: FloorState = FloorState.WAITING


class FloorRequestController:
    def __init__(self, room: SwitchRoom, bridge: Optional[ChatBridgeConnector] = None, default_ttl_seconds: float = 90.0):
        self.room = room
        self.bridge = bridge
        self.default_ttl_seconds = default_ttl_seconds
        self.requests: Dict[str, FloorRequest] = {}
        self.active_speaker_request_id: Optional[str] = None
        self.room.register_session("shipcourt-third-voice", "third-voice", "boardroom-voice-gateway", "openai-gpt4o")

    def raise_hand(
        self,
        meeting_id: str,
        agent_id: str,
        emoji: str,
        reason: str,
        spoken_script: str,
        priority: int = 80,
        evidence_refs: Optional[List[str]] = None,
        now: Optional[float] = None,
    ) -> FloorRequest:
        ts = now if now is not None else time.time()
        for existing in self.requests.values():
            if existing.meeting_id == meeting_id and existing.agent_id == agent_id and existing.state == FloorState.WAITING and existing.reason == reason:
                return existing
        req_id = f"floor-{len(self.requests) + 1:03d}"
        f_req = FloorRequest(
            request_id=req_id,
            meeting_id=meeting_id,
            agent_id=agent_id,
            intent="challenge",
            emoji=emoji,
            reason=reason,
            spoken_script=spoken_script,
            priority=priority,
            evidence_refs=list(evidence_refs or []),
            created_at=ts,
            expires_at=ts + self.default_ttl_seconds,
            state=FloorState.WAITING,
        )
        self.requests[req_id] = f_req
        card_msg = f'{emoji} **[{agent_id.upper()} RAISED A HAND]** (`{req_id}`, Priority {priority}): "{reason}"'
        self.room.post_message("third-voice", card_msg, sender_role="third-voice")
        if self.bridge:
            self.bridge.forward_to_chat(card_msg)
        return f_req

    def grant_floor(self, request_id: str, human_actor: str, now: Optional[float] = None) -> Dict[str, Any]:
        ts = now if now is not None else time.time()
        if not self.room.enforce_human_verdict_gate(human_actor):
            raise PermissionError(f"Only a human approver can grant the floor (got `{human_actor}`).")
        f_req = self.requests[request_id]
        if f_req.state in (FloorState.GRANTED, FloorState.SPEAKING, FloorState.YIELDING):
            return {"granted": False, "reason": "already_processed_idempotent", "state": f_req.state.value}
        if ts > f_req.expires_at:
            f_req.state = FloorState.EXPIRED
            return {"granted": False, "reason": "request_expired", "state": f_req.state.value}
        f_req.state = FloorState.YIELDING
        speech_msg = f"🎙️ **[{f_req.agent_id.upper()} SPEAKING — Granted by {human_actor}]**: {f_req.spoken_script}"
        self.room.post_message("third-voice", speech_msg, sender_role="third-voice")
        if self.bridge:
            self.bridge.forward_to_chat(speech_msg)
        return {"granted": True, "request_id": request_id, "spoken_script": f_req.spoken_script, "state": f_req.state.value}
