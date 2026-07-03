"""shl -- inspect and manage a self-healing locator store from the command line."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .store import LocatorStore


def _cmd_init(args: argparse.Namespace) -> None:
    store = LocatorStore(args.path)
    store.save()
    print(f"Created {store.path}")


def _cmd_list(args: argparse.Namespace) -> None:
    store = LocatorStore(args.path)
    specs = store.all()
    if not specs:
        print(f"No locators registered in {store.path}")
        return
    for name, spec in sorted(specs.items()):
        heals = f" (healed {spec.heal_count}x)" if spec.heal_count else ""
        print(f"{name:30s} {spec.selector}{heals}")


def _cmd_report(args: argparse.Namespace) -> None:
    store = LocatorStore(args.path)
    events = store.heal_events()
    if not events:
        print("No healing events recorded yet.")
        return
    for event in events[-args.limit :]:
        ts = datetime.fromtimestamp(event["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{ts}] {event['name']}: {event['old_selector']} -> "
            f"{event['new_selector']} (confidence={event['score']:.2f})"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shl", description="Self-healing locator toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create an empty locator store file")
    p_init.add_argument("path", nargs="?", default="locators.yaml")
    p_init.set_defaults(func=_cmd_init)

    p_list = sub.add_parser("list", help="List registered locators")
    p_list.add_argument("path", nargs="?", default="locators.yaml")
    p_list.set_defaults(func=_cmd_list)

    p_report = sub.add_parser("report", help="Show recent healing events")
    p_report.add_argument("path", nargs="?", default="locators.yaml")
    p_report.add_argument("-n", "--limit", type=int, default=20)
    p_report.set_defaults(func=_cmd_report)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
