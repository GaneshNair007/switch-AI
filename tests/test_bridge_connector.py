"""Tests for ChatBridgeConnector parsing and event forwarding."""
from server.switch_room import SwitchRoom
from server.bridge_connector import ChatBridgeConnector

def test_parse_mattermost_webhook():
    room = SwitchRoom("test-bridge-room")
    connector = ChatBridgeConnector(room)

    payload = {
        "user_name": "priya",
        "text": "@court-clerk open case https://github.com/acme/shop/pull/482",
        "channel_name": "ship-court"
    }

    parsed = connector.parse_incoming_webhook(payload)
    assert parsed["sender"] == "priya"
    assert "open case" in parsed["text"]
    assert parsed["channel"] == "ship-court"

    msg_id = connector.handle_webhook_event(payload)
    assert msg_id is not None
    assert len(room.messages) == 1
    assert room.messages[0].sender == "priya"
