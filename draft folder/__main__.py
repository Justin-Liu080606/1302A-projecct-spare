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
        {"subject": "数学", "exam_date": date(2026, 11, 14), "minutes": 180},
    ]
    slots = []
    for offset in range(7):
        slots.append({"date": start_date + timedelta(days=offset), "start": 19 * 60,
                      "end": 20 * 60})
    return start_date, tasks, slots


def main():
    parser = argparse.ArgumentParser(description="Smart Study Planner 本地复习日历")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cli", action="store_true", help="使用旧版终端输入模式")
    group.add_argument("--demo", action="store_true", help="生成旧版固定示例 HTML")
    parser.add_argument("--port", type=int, default=8765, help="网页服务端口（默认 8765）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    if not args.cli and not args.demo:
        if not 0 <= args.port <= 65535:
            parser.error("端口必须在 0–65535 之间。")
        run_web(args.port, not args.no_browser)
        return
    try:
        start_date, tasks, slots = demo_input() if args.demo else collect_input()
        sessions, unscheduled = schedule(tasks, slots)
        path = save_calendar(start_date, slots, sessions, unscheduled)
    except (EOFError, KeyboardInterrupt):
        print("\n已取消输入。")
        return
    print(f"已生成日历：{path}")
    print(f"浏览器地址：{path.as_uri()}")
    for task in unscheduled:
        print(f'{task["subject"]}：剩余 {task["remaining_minutes"]} 分钟')


if __name__ == "__main__":
    main()
