"""Switch Template Schema Validator.
Validates switch/ship-court.template.yaml against structural assertions and, when available,
the official SandboxAQ switch_core.template_lint engine.
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import yaml

def validate_template(template_path: Path) -> bool:
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    # 1. Version check
    assert data.get("version") == 1, "Template version must be 1"

    # 2. Params check
    params = data.get("params", {})
    for req in ("team", "repository", "provider", "bridge", "directory"):
        assert req in params, f"Missing required parameter '{req}'"

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
    assert "kickoff" in data, "Room must define kickoff message"

    # Prefer installed official tooling; missing runtime is explicitly reported.
    import importlib.util
    official_available = importlib.util.find_spec('switch_core') is not None
    if official_available:
        from switch_core.template_lint import lint_template
        result = lint_template(content)
        if result.errors or result.warnings:
            raise ValueError(f"Official template lint failed: {result}")
        print('Official Switch lint passed: 0 errors, 0 warnings.')
    else:
        print('Structural checks passed. Official Switch lint NOT RUN: switch_core is not installed.')

    return True

if __name__ == "__main__":
    t_path = Path(__file__).parent / "ship-court.template.yaml"
    validate_template(t_path)
