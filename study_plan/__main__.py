"""Project entry: local web interface, legacy CLI, or legacy HTML demo."""

import argparse
from datetime import date, timedelta

from .calendar_view import save_calendar
from .input_ui import collect_input
from .scheduler import schedule
from .web_app import run_web


def demo_input():
    start_date = date(2026, 11, 9)
    tasks = [
        {"subject": "CS1302A Python", "exam_date": date(2026, 11, 11), "minutes": 180},
        {"subject": "Mathematics", "exam_date": date(2026, 11, 14), "minutes": 180},
    ]
    slots = []
    for offset in range(7):
        slots.append({"date": start_date + timedelta(days=offset), "start": 19 * 60,
                      "end": 20 * 60})
    return start_date, tasks, slots


def main():
    parser = argparse.ArgumentParser(description="Smart Study Planner local calendar")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cli", action="store_true", help="Use legacy terminal input mode")
    group.add_argument("--demo", action="store_true", help="Generate a legacy HTML example")
    parser.add_argument("--port", type=int, default=8765, help="Web server port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically")
    args = parser.parse_args()

    if not args.cli and not args.demo:
        if not 0 <= args.port <= 65535:
            parser.error("Port must be between 0 and 65535.")
        run_web(args.port, not args.no_browser)
        return
    try:
        start_date, tasks, slots = demo_input() if args.demo else collect_input()
        sessions, unscheduled = schedule(tasks, slots)
        path = save_calendar(start_date, slots, sessions, unscheduled)
    except (EOFError, KeyboardInterrupt):
        print("\nInput cancelled.")
        return
    print(f"Calendar generated:{path}")
    print(f"Browser URL:{path.as_uri()}")
    for task in unscheduled:
        print(f'{task["subject"]} has {task["remaining_minutes"]} minutes remaining')


if __name__ == "__main__":
    main()
