"""Legacy data-only scheduler. Dates use datetime.date and times use minutes since midnight."""


def schedule(tasks, available_slots):
    """Sort by exam date and return (sessions, unscheduled) without changing inputs.

    tasks: [{subject, exam_date, minutes}]
    available_slots: [{date, start, end}]; every slot length is a multiple of 30 minutes.
    sessions: [{date, start, end, subject, subject_id}]
    unscheduled: [{subject, remaining_minutes}]
    subject_id is the input order, allowing separate events with equal names.
    """
    free_slots = set()
    for slot in available_slots:
        if not (0 <= slot["start"] < slot["end"] <= 1440):
            raise ValueError("Each availability window must be within one day, with start before end.")
        if slot["start"] % 30 or slot["end"] % 30:
            raise ValueError("Time windows must align to 30-minute boundaries.")
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
            raise ValueError("Study time must be positive and divisible by 30 minutes.")
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
