"""终端输入与基本校验；时间统一转换成从午夜起的分钟数。"""

from datetime import date, timedelta


def ask_date(prompt):
    while True:
        value = input(prompt).strip()
        try:
            result = date.fromisoformat(value)
            if result.isoformat() != value:
                raise ValueError
            return result
        except ValueError:
            print("请输入有效日期，格式为 YYYY-MM-DD，例如 2026-11-10。")


def ask_positive_integer(prompt, multiple=1):
    while True:
        try:
            value = int(input(prompt).strip())
            if value > 0 and value % multiple == 0:
                return value
        except ValueError:
            pass
        print(f"请输入正整数，且必须是 {multiple} 的整数倍。")


def ask_time(prompt):
    while True:
        value = input(prompt).strip()
        try:
            hour, minute = value.split(":")
            hour, minute = int(hour), int(minute)
            if 0 <= hour <= 23 and minute in (0, 30):
                return hour * 60 + minute
            if hour == 24 and minute == 0:
                return 1440
        except ValueError:
            pass
        print("请输入半小时边界的时间，如 09:00 或 09:30；24:00 只能用作结束时间。")


def collect_input():
    start_date = ask_date("计划开始日期 (YYYY-MM-DD)：")
    while start_date > date.max - timedelta(days=6):
        print("开始日期必须允许往后生成完整的 7 天。")
        start_date = ask_date("计划开始日期 (YYYY-MM-DD)：")

    count = ask_positive_integer("每天有几个默认空闲时段？")
    windows = []
    for index in range(count):
        while True:
            print(f"默认空闲时段 {index + 1}（每天重复）：")
            start = ask_time("开始时间 (HH:MM)：")
            end = ask_time("结束时间 (HH:MM)：")
            if start >= end:
                print("结束时间必须晚于开始时间，不能跨午夜。请重新输入。")
            elif any(start < old_end and old_start < end
                     for old_start, old_end in windows):
                print("空闲时段不能重叠。请重新输入。")
            else:
                windows.append((start, end))
                break

    tasks = []
    count = ask_positive_integer("要复习几科？")
    for index in range(count):
        name = ""
        while not name:
            name = input(f"第 {index + 1} 科名称：").strip()
            if not name:
                print("科目名称不能为空。")
        exam_date = ask_date("考试日期 (YYYY-MM-DD)：")
        minutes = ask_positive_integer("剩余复习时长（分钟，30 的整数倍）：", 30)
        tasks.append({"subject": name, "exam_date": exam_date, "minutes": minutes})

    slots = []
    for day_offset in range(7):
        day = start_date + timedelta(days=day_offset)
        for start, end in windows:
            slots.append({"date": day, "start": start, "end": end})
    return start_date, tasks, slots
