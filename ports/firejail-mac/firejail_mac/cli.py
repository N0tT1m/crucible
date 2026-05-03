from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from firejail_mac.translate import PROFILES_DIR, parse, to_sbpl


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="firejail-mac")
    p.add_argument("--profile", default="default", help="profile name in profiles/ or absolute path")
    p.add_argument("--net", choices=["none", "allow"], help="override network access")
    p.add_argument("--read-only", action="append", default=[])
    p.add_argument("--blacklist", action="append", default=[])
    p.add_argument("--tmpfs", action="append", default=[],
                   help="path to make non-persistent (mapped to private-tmp+blacklist)")
    p.add_argument("--lima", action="store_true",
                   help="run inside a hardened Lima VM instead of sandbox-exec")
    p.add_argument("--print", action="store_true", help="print the generated .sb and exit")
    p.add_argument("argv", nargs=argparse.REMAINDER)
    args = p.parse_args(argv)

    if args.lima:
        return _run_lima(args.argv)

    profile_path = Path(args.profile)
    if not profile_path.exists():
        profile_path = PROFILES_DIR / f"{args.profile}.profile"
    if not profile_path.exists():
        print(f"profile not found: {args.profile}", file=sys.stderr)
        return 2

    sb = parse(profile_path.read_text())
    if args.net == "none":
        sb.network = "deny"
    sb.read_only.extend(args.read_only)
    sb.blacklist.extend(args.blacklist)
    if args.tmpfs:
        sb.private_tmp = True
        sb.blacklist.extend(args.tmpfs)

    profile_text = to_sbpl(sb)
    for w in sb.warnings:
        print(f"[firejail-mac] {w}", file=sys.stderr)

    if args.print:
        sys.stdout.write(profile_text)
        return 0

    if not args.argv:
        print("no command given", file=sys.stderr)
        return 2

    target = args.argv[0:1] if args.argv[0] != "--" else args.argv[1:2]
    rest = args.argv[1:] if args.argv[0] != "--" else args.argv[2:]

    with tempfile.NamedTemporaryFile("w", suffix=".sb", delete=False) as f:
        f.write(profile_text)
        sb_path = f.name
    try:
        cmd = ["sandbox-exec", "-f", sb_path, *target, *rest]
        return subprocess.call(cmd)
    finally:
        os.unlink(sb_path)


def _run_lima(argv: list[str]) -> int:
    vm = os.environ.get("FIREJAIL_LIMA_VM", "firejail")
    if not argv:
        print("no command given", file=sys.stderr)
        return 2
    return subprocess.call(["limactl", "shell", vm, "--", *argv])
