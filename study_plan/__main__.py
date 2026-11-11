"""入口：交互和演示共用排程及日历函数。"""

import argparse
from datetime import date, timedelta

from .calendar_view import save_calendar
from .input_ui import collect_input
from .scheduler import schedule


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
    parser = argparse.ArgumentParser(description="生成 7 天复习周日历")
    parser.add_argument("--demo", action="store_true", help="使用固定的两科数据")
    args = parser.parse_args()
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
