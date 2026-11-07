from __future__ import annotations
import json
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple
from .switch_room import SwitchRoom


class ChatBridgeConnector:
    """Multi-Persona Chat Bridge supporting Discord native webhooks, Mattermost, and Slack."""

    PERSONA_PROFILES: Dict[str, Dict[str, Any]] = {
        "clerk": {"username": "ShipCourt Clerk ⚖️", "color": 0x4F46E5},
        "prosecutor": {"username": "ShipCourt Prosecutor 🚨", "color": 0xDC2626},
        "defender": {"username": "ShipCourt Defender 🛡️", "color": 0x2563EB},
        "judge": {"username": "Hon. Chief Justice 👩‍⚖️", "color": 0x7C3AED},
        "rollback": {"username": "Rollback Engineer ⏪", "color": 0xD97706},
        "antigravity-guard": {"username": "Antigravity Scope Guard 🛰️", "color": 0x0D9488},
        "third-voice": {"username": "Boardroom Third Voice ✋", "color": 0xEC4899},
        "parallel-earth": {"username": "Parallel Earth Simulator 🌍", "color": 0x059669},
        "github-ops": {"username": "GitHub Operations Agent 🐙", "color": 0x1E293B},
    }

    def __init__(
        self,
        room: SwitchRoom,
        webhook_url: Optional[str] = None,
        platform: str = "auto",
        transport: Optional[Callable[[urllib.request.Request], Tuple[int, bytes]]] = None,
    ):
        self.room = room
        self.webhook_url = webhook_url
        self.platform = platform
        self.transport = transport
        self.sent_payloads: List[Dict[str, Any]] = []

    def _is_discord_webhook(self) -> bool:
        if self.platform.lower() == "discord":
            return True
        if self.platform.lower() in ("mattermost", "slack"):
            return False
        if not self.webhook_url:
            return False
        url_lower = self.webhook_url.lower()
        return "discord.com/api/webhooks" in url_lower or "discordapp.com/api/webhooks" in url_lower

    def parse_incoming_webhook(self, payload: Dict[str, Any]) -> Dict[str, str]:
        sender = (
            payload.get("user_name")
            or payload.get("user")
            or (payload.get("author", {}) if isinstance(payload.get("author"), dict) else {}).get("username")
            or "developer"
        )
        text = payload.get("text") or payload.get("content") or ""
        channel = (
            payload.get("channel_name")
            or payload.get("channel_id")
            or self.room.room_name
            or "ship-court"
        )
        return {"sender": str(sender), "text": str(text), "channel": str(channel)}

    def handle_webhook_event(self, payload: Dict[str, Any]) -> Optional[str]:
        parsed = self.parse_incoming_webhook(payload)
        text = parsed["text"].strip()
        sender = parsed["sender"]
        if not text:
            return None
        self.room.post_message(sender=sender, content=text)
        if text.startswith("!"):
            return self.room.handle_command(text, sender)
        return f"ACK:{sender}:{parsed['channel']}"

    def build_outgoing_payload(
        self,
        text: str,
        agent_role: str = "clerk",
        embed_title: Optional[str] = None,
        embed_fields: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        profile = self.PERSONA_PROFILES.get(agent_role, self.PERSONA_PROFILES["clerk"])
        if self._is_discord_webhook():
            payload: Dict[str, Any] = {
                "content": text,
                "username": profile["username"],
                "text": text,
            }
            if embed_title or embed_fields:
                embed: Dict[str, Any] = {
                    "title": embed_title or profile["username"],
                    "description": text,
                    "color": profile["color"],
                }
                if embed_fields:
                    embed["fields"] = embed_fields
                payload["embeds"] = [embed]
            return payload
        return {
            "text": text,
            "username": profile["username"] if agent_role != "clerk" else "ShipCourt-Clerk",
        }

    def forward_to_chat(
        self,
        text: str,
        agent_role: str = "clerk",
        embed_title: Optional[str] = None,
        embed_fields: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        payload = self.build_outgoing_payload(
            text=text,
            agent_role=agent_role,
            embed_title=embed_title,
            embed_fields=embed_fields,
        )
        self.sent_payloads.append(payload)
        if not self.webhook_url:
            return False
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Switch-ShipCourt/2.0"},
            method="POST",
        )
        try:
            if self.transport is not None:
                status, _ = self.transport(req)
                return 200 <= status < 300
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False
