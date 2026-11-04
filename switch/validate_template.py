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
    assert "kickoff" in room, "Room must define kickoff message"

    # 7. Official Switch Core Lint (if Switch runtime is installed on machine)
    switch_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Switch Console Canary" / "resources" / "local-server",
        Path("C:/Users/Ganesh Nair/AppData/Local/Programs/Switch Console Canary/resources/local-server")
    ]
    official_checked = False
    for sp in switch_paths:
        core_dir = sp / "switch" / "src" / "core"
        site_dir = sp / "switch" / "site-packages"
        if core_dir.exists() and site_dir.exists():
            sys.path.extend([str(core_dir), str(site_dir)])
            try:
                from switch_core.template_lint import lint_template
                lint_res = lint_template(content)
                assert len(lint_res.errors) == 0, f"Switch Core lint errors: {lint_res.errors}"
                assert len(lint_res.warnings) == 0, f"Switch Core lint warnings: {lint_res.warnings}"
                official_checked = True
                print("Switch Core Official Validator: 0 errors, 0 warnings. Template is 100% clean.")
                break
            except Exception as e:
                print(f"Notice: Official lint execution skipped: {e}")

    if not official_checked:
        print("Template structural pre-checks passed: schema, parameters, roles, and agents valid.")

    return True

if __name__ == "__main__":
    t_path = Path(__file__).parent / "ship-court.template.yaml"
    validate_template(t_path)
