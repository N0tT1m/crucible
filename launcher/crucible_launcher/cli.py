from __future__ import annotations

import argparse
import sys

from crucible_launcher import doctor, installer, registry, runner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crux", description="Crucible launcher")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("tui", help="Launch categorized TUI menu (default)")
    sub.add_parser("list", help="List all manifested tools by category")
    sub.add_parser("doctor", help="Show install status of every tool")

    p_install = sub.add_parser("install", help="Install a tool via its manifest")
    p_install.add_argument("name")
    p_install.add_argument("--dry-run", action="store_true")

    p_run = sub.add_parser("run", help="Run a tool by name (extra args passed through)")
    p_run.add_argument("name")
    p_run.add_argument("extra", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)

    if args.cmd in (None, "tui"):
        from crucible_launcher.tui import launch
        return launch()

    tools = {t.name: t for t in registry.load_tools()}

    if args.cmd == "list":
        for cat, items in registry.by_category(list(tools.values())).items():
            print(f"\n[{cat}]")
            for t in items:
                print(f"  {t.name:24s} {t.help}")
        return 0

    if args.cmd == "doctor":
        return doctor.report()

    if args.cmd == "install":
        t = tools.get(args.name)
        if not t:
            print(f"unknown tool: {args.name}", file=sys.stderr)
            return 2
        return installer.install(t, dry_run=args.dry_run)

    if args.cmd == "run":
        t = tools.get(args.name)
        if not t:
            print(f"unknown tool: {args.name}", file=sys.stderr)
            return 2
        extra = list(args.extra)
        if extra and extra[0] == "--":
            extra = extra[1:]
        return runner.run(t, extra)

    parser.print_help()
    return 1
