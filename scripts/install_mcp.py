#!/usr/bin/env python3
"""Register the stats-mcp server into WorkBuddy's mcp.json (safe merge).

Run once after installing dependencies. Makes the 9 statistical tools
available as MCP tools in WorkBuddy (then trust the connector in the UI).
"""
import json
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SERVER_PY = SKILL_DIR / "server.py"
MCP_JSON = Path.home() / ".workbuddy" / "mcp.json"


def main():
    if not SERVER_PY.exists():
        print(f"ERROR: server.py not found at {SERVER_PY}")
        return 1

    python = shutil.which("python") or shutil.which("python3")
    if not python:
        print("ERROR: no 'python' interpreter found on PATH.")
        return 1

    entry = {
        "command": python,
        "args": [str(SERVER_PY)],
    }

    cfg = {}
    if MCP_JSON.exists():
        try:
            cfg = json.loads(MCP_JSON.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR: could not parse {MCP_JSON}: {e}")
            return 1
    cfg.setdefault("mcpServers", {})

    if "stats-mcp" in cfg["mcpServers"]:
        print("stats-mcp already present in mcp.json; nothing to do.")
        return 0

    # backup before editing
    shutil.copy(MCP_JSON, MCP_JSON.with_suffix(".json.bak"))
    cfg["mcpServers"]["stats-mcp"] = entry
    MCP_JSON.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Added 'stats-mcp' to {MCP_JSON}.")
    print("Restart WorkBuddy (or re-read config) and click 'Trust' on the "
          "stats-mcp connector in the connector management page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
