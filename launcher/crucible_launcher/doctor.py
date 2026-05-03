from __future__ import annotations

import platform
import shutil

from crucible_launcher.installer import is_installed
from crucible_launcher.registry import Tool, load_tools


def report() -> int:
    tools = load_tools()
    osname = platform.system()
    print(f"crucible doctor — host: {osname} {platform.release()}")
    print(f"  brew:    {'ok' if shutil.which('brew') else 'missing'}")
    print(f"  docker:  {'ok' if shutil.which('docker') else 'missing'}")
    print(f"  limactl: {'ok' if shutil.which('limactl') else 'missing'}")
    print(f"  pipx:    {'ok' if shutil.which('pipx') else 'missing'}")
    print()
    missing: list[Tool] = []
    for t in tools:
        if t.macos_only and osname != "Darwin":
            continue
        if t.windows_only and osname != "Windows":
            continue
        if t.linux_only and osname != "Linux":
            continue
        ok = is_installed(t)
        marker = "✓" if ok else "·"
        print(f"  {marker} [{t.category}] {t.name}")
        if not ok:
            missing.append(t)
    print()
    if missing:
        print(f"{len(missing)} tool(s) not on PATH. Install with: crux install <name>")
    else:
        print("all manifested tools available.")
    return 0 if not missing else 1
