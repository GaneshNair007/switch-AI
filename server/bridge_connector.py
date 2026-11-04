"""Chat Bridge Connector: Bridges Mattermost and Slack webhook payloads to Switch room events."""
from __future__ import annotations
import json, urllib.request
from typing import Dict, Any, Optional
from .switch_room import SwitchRoom

class ChatBridgeConnector:
    def __init__(self, room: SwitchRoom, webhook_url: Optional[str] = None):
        self.room = room
        self.webhook_url = webhook_url

    def parse_incoming_webhook(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Normalize payload from Mattermost or Slack outgoing webhooks."""
        # Mattermost format: user_name, text, channel_name
        # Slack format: user_name, text, channel_id
        sender = payload.get("user_name", payload.get("user", "developer"))
        text = payload.get("text", payload.get("content", "")).strip()
        channel = payload.get("channel_name", payload.get("channel_id", "ship-court"))
        return {"sender": sender, "text": text, "channel": channel}

    def handle_webhook_event(self, payload: Dict[str, Any]) -> Optional[str]:
        """Dispatch incoming webhook message into the Switch room."""
        parsed = self.parse_incoming_webhook(payload)
        sender = parsed["sender"]
        text = parsed["text"]
        
        # Post into Switch room
        msg = self.room.post_message(sender, text)
        return msg.id

    def forward_to_chat(self, text: str) -> bool:
        """Send outgoing notification back to external chat channel webhook."""
        if not self.webhook_url:
            return False
        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps({"text": text, "username": "ShipCourt-Clerk"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

