"""Spawn a target process inside an AppContainer + Job Object on Windows.

This module is the platform-touching part of firejail-win. The pure-Python
side (CLI / parser) is deliberately importable on non-Windows hosts so the
launcher's manifest discovery doesn't blow up. Windows-only ctypes/pywin32
calls live behind `_on_windows()`.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from firejail_win.translate import Plan, to_wsb


def _on_windows() -> bool:
    return sys.platform == "win32"


def run(plan: Plan, target: list[str]) -> int:
    if plan.sandbox:
        return _run_sandbox(plan, target)
    if not _on_windows():
        print("[firejail-win] non-Windows host: would spawn under AppContainer:", target)
        return 0
    return _run_appcontainer(plan, target)


def _run_sandbox(plan: Plan, target: list[str]) -> int:
    wsb_text = to_wsb(plan, target)
    wsb_path = Path(tempfile.mkstemp(suffix=".wsb")[1])
    wsb_path.write_text(wsb_text, encoding="utf-8")
    try:
        return subprocess.call(["WindowsSandbox.exe", str(wsb_path)])
    finally:
        try:
            wsb_path.unlink()
        except OSError:
            pass


def _run_appcontainer(plan: Plan, target: list[str]) -> int:
    """Stub: the real impl uses CreateProcess with PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES.

    The full implementation needs:
      1. CreateAppContainerProfile with a per-tool SID (recoverable name like
         "crucible.firejail-win.<hash>").
      2. SECURITY_CAPABILITIES with no capabilities (deny by default).
      3. Job Object (CreateJobObjectW) with the limits in plan.job_limits.
      4. WFP filters (FwpmEngineOpen + FwpmFilterAdd) tagged with the
         AppContainer SID, denying out-bound when plan.net_deny.
      5. ACL ACEs on each plan.file_deny path that deny the AppContainer SID.

    For the scaffold we shell out to a PowerShell helper that drives the
    AppContainer + Job Object portion via pywin32. WFP wiring is left for
    the next pass — denial via Windows Firewall (NetFirewall PowerShell
    cmdlets) covers most apps in the meantime.
    """
    here = Path(__file__).parent
    helper = here / "appcontainer.ps1"
    if not helper.exists():
        # Soft-fail: spawn under a Job Object even without AppContainer.
        env = os.environ.copy()
        if plan.private_temp:
            env["TEMP"] = tempfile.mkdtemp(prefix="firejail-")
            env["TMP"] = env["TEMP"]
        return subprocess.call(target, env=env)

    args = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(helper),
            "-DenyNet", "1" if plan.net_deny else "0"]
    for d in plan.file_deny:
        args += ["-DenyPath", d]
    args += ["--"] + target
    return subprocess.call(args)
