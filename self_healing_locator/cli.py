"""shl -- inspect and manage a self-healing locator store from the command line."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from . import copilot_assist
from .store import HealEvent, LocatorSpec, LocatorStore


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
        frame = f" [in frame: {spec.frame_selector}]" if spec.frame_selector else ""
        failed = f" [{len(spec.failed_selectors)} failed attempt(s)]" if spec.failed_selectors else ""
        print(f"{name:30s} {spec.selector}{frame}{heals}{failed}")


def _cmd_report(args: argparse.Namespace) -> None:
    store = LocatorStore(args.path)
    events = store.heal_events()
    if not events:
        print("No healing events recorded yet.")
        return
    for event in events[-args.limit :]:
        ts = datetime.fromtimestamp(event["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        source = event.get("source", "heuristic")
        print(
            f"[{ts}] {event['name']}: {event['old_selector']} -> "
            f"{event['new_selector']} (confidence={event['score']:.2f}, source={source})"
        )


def _cmd_review(args: argparse.Namespace) -> None:
    store = LocatorStore(args.path)
    pending = store.list_pending()
    if not pending:
        print("Nothing pending review.")
        return
    for p in pending:
        ts = datetime.fromtimestamp(p.created_at).strftime("%Y-%m-%d %H:%M:%S")
        frame = f" [in frame: {p.frame_selector}]" if p.frame_selector else ""
        print(f"[{ts}] {p.name}: {p.old_selector} -> {p.new_selector}{frame}")
        print(f"    confidence={p.score:.2f}  reason={p.reason}")
        print(f"    matched text: {p.fingerprint.get('text', '')!r}")


def _cmd_approve(args: argparse.Namespace) -> None:
    store = LocatorStore(args.path)
    pending = store.pop_pending(args.name)
    if pending is None:
        print(f"No pending heal named '{args.name}'")
        return 1
    store.update_selector(pending.name, pending.new_selector, pending.fingerprint, frame_selector=pending.frame_selector)
    store.log_heal_event(
        HealEvent(
            name=pending.name,
            old_selector=pending.old_selector,
            new_selector=pending.new_selector,
            score=pending.score,
            source=pending.source,
        )
    )
    print(f"Approved: {pending.name} -> {pending.new_selector}")


def _cmd_reject(args: argparse.Namespace) -> None:
    store = LocatorStore(args.path)
    pending = store.pop_pending(args.name)
    if pending is None:
        print(f"No pending heal named '{args.name}'")
        return 1
    print(f"Rejected: {pending.name} (was proposing {pending.new_selector})")


def _cmd_assist(args: argparse.Namespace) -> None:
    store = LocatorStore(args.path)
    names = copilot_assist.pending_assist_names(store.path)
    if not names:
        print(f"No locators waiting on Copilot Chat assist for {store.path}")
        return
    _, md_path = copilot_assist.assist_paths(store.path)
    print(f"Prompts ready for Copilot Chat: {md_path}")
    for name in names:
        print(f"  - {name}")


def _cmd_assist_apply(args: argparse.Namespace) -> None:
    store = LocatorStore(args.path)
    spec = store.get(args.name)
    if spec is None:
        print(f"No locator named '{args.name}' in {store.path}")
        return 1
    old_selector = spec.selector
    store.update_selector(args.name, args.selector, spec.fingerprint, frame_selector=args.frame_selector)
    store.clear_failed_attempts(args.name)
    store.log_heal_event(
        HealEvent(
            name=args.name,
            old_selector=old_selector,
            new_selector=args.selector,
            score=1.0,
            source="copilot_chat",
        )
    )
    copilot_assist.clear_assist(store.path, args.name)
    print(f"Applied: {args.name} -> {args.selector} (source=copilot_chat)")


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

    p_review = sub.add_parser("review", help="Show heals withheld for looking destructive")
    p_review.add_argument("path", nargs="?", default="locators.yaml")
    p_review.set_defaults(func=_cmd_review)

    p_approve = sub.add_parser("approve", help="Apply a pending heal")
    p_approve.add_argument("name")
    p_approve.add_argument("path", nargs="?", default="locators.yaml")
    p_approve.set_defaults(func=_cmd_approve)

    p_reject = sub.add_parser("reject", help="Discard a pending heal")
    p_reject.add_argument("name")
    p_reject.add_argument("path", nargs="?", default="locators.yaml")
    p_reject.set_defaults(func=_cmd_reject)

    p_assist = sub.add_parser("assist", help="List locators with a Copilot Chat prompt waiting")
    p_assist.add_argument("path", nargs="?", default="locators.yaml")
    p_assist.set_defaults(func=_cmd_assist)

    p_assist_apply = sub.add_parser(
        "assist-apply", help="Apply a selector obtained by hand (e.g. via Copilot Chat)"
    )
    p_assist_apply.add_argument("name")
    p_assist_apply.add_argument("selector")
    p_assist_apply.add_argument("path", nargs="?", default="locators.yaml")
    p_assist_apply.add_argument("--frame", dest="frame_selector", default=None, help="iframe selector, if applicable")
    p_assist_apply.set_defaults(func=_cmd_assist_apply)

    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
