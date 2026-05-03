from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from crucible_launcher.installer import PORTS_ROOT, is_installed
from crucible_launcher.registry import Tool


def run(tool: Tool, extra: list[str] | None = None) -> int:
    if not is_installed(tool):
        print(f"[crucible] {tool.name} is not installed. Try: crux install {tool.name}")
        return 127
    cmd = _resolve(tool) + list(tool.args) + list(extra or [])
    if tool.requires_sudo and hasattr(os, "geteuid") and os.geteuid() != 0:
        cmd = ["sudo", *cmd]
    print(f"[crucible] $ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.call(cmd)


def _resolve(tool: Tool) -> list[str]:
    base = PORTS_ROOT / tool.command / "bin"
    for suffix in ("", ".ps1", ".cmd", ".exe"):
        bundled = base / f"{tool.command}{suffix}"
        if bundled.exists():
            if suffix == ".ps1":
                return ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(bundled)]
            return [str(bundled)]
    return [tool.command]
