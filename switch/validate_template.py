"""Switch Template Schema Validator.
Validates that switch/ship-court.template.yaml conforms to the Switch Console schema.
"""
from __future__ import annotations
import re, sys
from pathlib import Path
import yaml

def validate_template(template_path: Path) -> bool:
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 1. Version check
    assert data.get("version") == 1, "Template version must be 1"

    # 2. Params check
    params = data.get("params", {})
    assert "team" in params, "Missing 'team' parameter"
    assert "repository" in params, "Missing 'repository' parameter"
    assert "provider" in params, "Missing 'provider' parameter"
    assert "bridge" in params, "Missing 'bridge' parameter"

    # 3. Agents check
    agents = data.get("agents", [])
    assert len(agents) >= 5, f"Expected at least 5 courtroom agents, found {len(agents)}"
    agent_names = set()
    for agent in agents:
        name = agent.get("name")
        assert name, "Agent must have a name"
        agent_names.add(name)
        assert "addressing" in agent, f"Agent {name} missing addressing scope"
        assert "instructions" in agent, f"Agent {name} missing instructions"

    # 4. Room check
    room = data.get("room", {})
    assert room.get("name"), "Room must have a name"
    assert room.get("bridge"), "Room must specify a bridge"
    assert set(room.get("agents", [])) == agent_names, "Room agents must match defined agents"
    assert "users" in room, "Room must specify users (e.g. {$creator})"
    assert "aliases" in room, "Room must define aliases"

    # 5. Exclusive role check
    roles = room.get("roles", [])
    approver_role = next((r for r in roles if r.get("name") == "approver"), None)
    assert approver_role is not None, "Missing 'approver' role in room"
    assert approver_role.get("exclusive") is True, "The approver role must be exclusive"

    # 6. Kickoff check
    assert "kickoff" in room, "Room must define kickoff message"

    print("Template validation successful: switch/ship-court.template.yaml conforms 100% to Switch Console schema.")
    return True

if __name__ == "__main__":
    t_path = Path(__file__).parent / "ship-court.template.yaml"
    validate_template(t_path)
