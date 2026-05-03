from __future__ import annotations

import argparse
import sys
from pathlib import Path

from firejail_win.runner import run
from firejail_win.translate import PROFILES_DIR, parse


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="firejail-win")
    p.add_argument("--profile", default="default")
    p.add_argument("--net", choices=["none", "allow"])
    p.add_argument("--read-only", action="append", default=[])
    p.add_argument("--blacklist", action="append", default=[])
    p.add_argument("--tmpfs", action="append", default=[])
    p.add_argument("--sandbox", action="store_true",
                   help="run inside Windows Sandbox (heavy, requires Pro/Enterprise)")
    p.add_argument("--print", action="store_true")
    p.add_argument("argv", nargs=argparse.REMAINDER)
    args = p.parse_args(argv)

    profile_path = Path(args.profile)
    if not profile_path.exists():
        profile_path = PROFILES_DIR / f"{args.profile}.profile"
    if not profile_path.exists():
        print(f"profile not found: {args.profile}", file=sys.stderr)
        return 2

    plan = parse(profile_path.read_text())
    if args.net == "none":
        plan.net_deny = True
    plan.file_readonly.extend(args.read_only)
    plan.file_deny.extend(args.blacklist)
    if args.tmpfs:
        plan.private_temp = True
        plan.file_deny.extend(args.tmpfs)
    if args.sandbox:
        plan.sandbox = True

    for w in plan.warnings:
        print(f"[firejail-win] {w}", file=sys.stderr)

    if args.print:
        print(plan)
        return 0

    if not args.argv:
        print("no command given", file=sys.stderr)
        return 2

    target = args.argv[1:] if args.argv[0] == "--" else args.argv
    return run(plan, target)
