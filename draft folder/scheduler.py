"""纯数据排程：date 使用 datetime.date，start/end 使用午夜起的分钟数。"""


def schedule(tasks, available_slots):
    """按考试日期稳定排序，返回 (sessions, unscheduled)，不修改输入。

    tasks: [{subject, exam_date, minutes}]
    available_slots: [{date, start, end}]，每段长度为 30 的整数倍。
    sessions: [{date, start, end, subject, subject_id}]
    unscheduled: [{subject, remaining_minutes}]
    subject_id 为输入序号，供日历区分同名科目。
    """
    free_slots = set()
    for slot in available_slots:
        if not (0 <= slot["start"] < slot["end"] <= 1440):
            raise ValueError("空闲时段必须在一天内，且开始早于结束。")
        if slot["start"] % 30 or slot["end"] % 30:
            raise ValueError("空闲时段必须在半小时边界上。")
        for start in range(slot["start"], slot["end"], 30):
            free_slots.add((slot["date"], start))

    ordered_slots = sorted(free_slots)
    used = set()
    sessions = []
    unscheduled = []
    ordered_tasks = sorted(enumerate(tasks), key=lambda item: item[1]["exam_date"])
    for subject_id, task in ordered_tasks:
        remaining = task["minutes"]
        if not isinstance(remaining, int) or remaining <= 0 or remaining % 30:
            raise ValueError("复习时长必须为正整数，且为 30 的整数倍。")
        for day, start in ordered_slots:
            if remaining == 0:
                break
            if day >= task["exam_date"] or (day, start) in used:
                continue
            sessions.append({"date": day, "start": start, "end": start + 30,
                             "subject": task["subject"], "subject_id": subject_id})
            used.add((day, start))
            remaining -= 30
        if remaining:
            unscheduled.append({"subject": task["subject"], "remaining_minutes": remaining})
    sessions.sort(key=lambda session: (session["date"], session["start"]))
    return sessions, unscheduled
