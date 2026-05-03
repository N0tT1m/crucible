from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from crucible_launcher.registry import Install, Tool

# Install backends added for Windows: winget, scoop, choco.
# These are added below alongside the Unix backends in _plan().

PORTS_ROOT = Path(__file__).resolve().parents[2] / "ports"


def is_installed(tool: Tool) -> bool:
    return shutil.which(tool.command) is not None or _ports_path(tool) is not None


def _ports_path(tool: Tool) -> Path | None:
    base = PORTS_ROOT / tool.command / "bin"
    for suffix in ("", ".ps1", ".cmd", ".exe"):
        candidate = base / f"{tool.command}{suffix}"
        if candidate.exists():
            return candidate
    return None


def install(tool: Tool, *, dry_run: bool = False) -> int:
    """Run the first applicable install backend declared in the manifest."""
    inst: Install = tool.install
    plan = _plan(inst)
    if not plan:
        print(f"[crucible] {tool.name}: no install method declared")
        return 1
    cmd, label = plan
    print(f"[crucible] {tool.name}: {label}")
    if dry_run:
        print("  $ " + " ".join(cmd))
        return 0
    return subprocess.call(cmd)


def _plan(inst: Install) -> tuple[list[str], str] | None:
    if inst.brew:
        return (["brew", "install", inst.brew], f"brew install {inst.brew}")
    if inst.cask:
        return (["brew", "install", "--cask", inst.cask], f"brew install --cask {inst.cask}")
    if inst.pipx:
        return (["pipx", "install", inst.pipx], f"pipx install {inst.pipx}")
    if inst.pip:
        return ([sys.executable, "-m", "pip", "install", inst.pip], f"pip install {inst.pip}")
    if inst.cargo:
        return (["cargo", "install", inst.cargo], f"cargo install {inst.cargo}")
    if inst.go:
        return (["go", "install", inst.go], f"go install {inst.go}")
    if inst.docker:
        return (["docker", "pull", inst.docker], f"docker pull {inst.docker}")
    if inst.lima:
        return (["limactl", "start", "--name", inst.lima, "template://default"], f"lima start {inst.lima}")
    if inst.winget:
        return (["winget", "install", "-e", "--id", inst.winget], f"winget install {inst.winget}")
    if inst.scoop:
        return (["scoop", "install", inst.scoop], f"scoop install {inst.scoop}")
    if inst.choco:
        return (["choco", "install", "-y", inst.choco], f"choco install {inst.choco}")
    if inst.powershell:
        return (["powershell", "-ExecutionPolicy", "Bypass", "-File", inst.powershell], f"pwsh {inst.powershell}")
    if inst.script:
        return (["bash", inst.script], f"bash {inst.script}")
    return None
