"""Smart Study Planner: validate a form request and build an explainable timetable.

This module has no web framework dependencies. Dates are local calendar dates,
while time intervals use minutes since midnight (end exclusive).
"""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re

TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$|^24:00$")
MAX_DAYS = 63
MAX_SUBJECTS = 20
MAX_WINDOWS = 12


class InputError(ValueError):
    """Invalid user form values (safe to display in the interface)."""


def parse_date(value, label):
    if not isinstance(value, str):
        raise InputError(f"{label}必须是 YYYY-MM-DD 格式。")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise InputError(f"{label}不是有效日期。") from exc
    if parsed.isoformat() != value:
        raise InputError(f"{label}必须是 YYYY-MM-DD 格式。")
    return parsed


def parse_time(value, *, is_end=False):
    if not isinstance(value, str) or not TIME_RE.fullmatch(value):
        raise InputError("时间必须是 HH:MM 格式，例如 08:00。")
    if value == "24:00" and not is_end:
        raise InputError("24:00 只能作为结束时间。")
    h, m = map(int, value.split(":"))
    return h * 60 + m


def minute_label(value):
    return f"{value // 60:02d}:{value % 60:02d}"


def parse_windows(value, label):
    if not isinstance(value, list) or len(value) > MAX_WINDOWS:
        raise InputError(f"{label}最多设置 {MAX_WINDOWS} 个时间段。")
    windows = []
    for item in value:
        if not isinstance(item, dict):
            raise InputError(f"{label}存在无效时间段。")
        start = parse_time(item.get("start"))
        end = parse_time(item.get("end"), is_end=True)
        if end - start < 30:
            raise InputError(f"{label}每个时段至少需要 30 分钟。")
        windows.append((start, end))
    # Merge overlapping *and touching* windows so capacity is not counted twice.
    merged = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def parse_subjects(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SUBJECTS:
        raise InputError(f"请填写 1–{MAX_SUBJECTS} 门科目。")
    subjects = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise InputError(f"第 {index + 1} 门科目的内容无效。")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            raise InputError(f"第 {index + 1} 门科目名称不能为空且不能超过 80 个字符。")
        raw_hours = item.get("hours")
        try:
            hours = Decimal(str(raw_hours))
        except (InvalidOperation, ValueError) as exc:
            raise InputError(f"{name} 的复习时长不是有效数字。") from exc
        if not hours.is_finite() or not (Decimal("0") < hours <= Decimal("500")):
            raise InputError(f"{name} 的复习时长必须在 0–500 小时之间。")
        minutes = hours * 60
        if minutes % 30 != 0:
            raise InputError(f"{name} 的复习时长请以 0.5 小时为单位。")
        raw_deadline = item.get("exam_date")
        exam_date = parse_date(raw_deadline, f"{name} 的考试日期") if raw_deadline else None
        subjects.append({"id": index, "name": name.strip(), "minutes": int(minutes),
                         "exam_date": exam_date})
    return subjects


def parse_request(data):
    """Return normalized input; all error messages are suitable for the UI."""
    if not isinstance(data, dict):
        raise InputError("请求数据格式不正确。")
    start = parse_date(data.get("start_date"), "开始日期")
    end = parse_date(data.get("end_date"), "结束日期")
    if end < start:
        raise InputError("结束日期不能早于开始日期。")
    if (end - start).days + 1 > MAX_DAYS:
        raise InputError(f"一次最多规划 {MAX_DAYS} 天，避免日历过大。")
    subjects = parse_subjects(data.get("subjects"))
    daily = parse_windows(data.get("daily_windows", []), "默认空闲时段")
    raw_overrides = data.get("date_overrides", [])
    if not isinstance(raw_overrides, list) or len(raw_overrides) > MAX_DAYS:
        raise InputError("特定日期时段格式不正确。")
    overrides = {}
    for obj in raw_overrides:
        if not isinstance(obj, dict):
            raise InputError("特定日期时段格式不正确。")
        day = parse_date(obj.get("date"), "自定义日期")
        if not start <= day <= end:
            raise InputError(f"{day.isoformat()} 不在规划日期范围内。")
        if day in overrides:
            raise InputError(f"{day.isoformat()} 只能有一组自定义设置。")
        overrides[day] = parse_windows(obj.get("windows", []), f"{day} 的空闲时段")

    session_minutes = data.get("session_minutes", 60)
    break_minutes = data.get("break_minutes", 10)
    daily_subject_limit = data.get("daily_subject_limit_minutes", 120)
    if (type(daily_subject_limit) is not int or
            not 60 <= daily_subject_limit <= 480 or
            daily_subject_limit % 30 != 0):
        raise InputError("每日单科复习上限必须为 1–8 小时，且以半小时为单位。")
    if type(session_minutes) is not int or session_minutes not in (30, 60, 90):
        raise InputError("单次复习时长只能选择 30、60 或 90 分钟。")
    if type(break_minutes) is not int or break_minutes not in (0, 5, 10, 15):
        raise InputError("休息时间只能选择 0、5、10 或 15 分钟。")
    slots = []
    day = start
    while day <= end:
        for window_start, window_end in overrides.get(day, daily):
            slots.append({"date": day, "start": window_start, "end": window_end})
        day += timedelta(days=1)
    return {"start": start, "end": end, "subjects": subjects, "slots": slots,
            "session_minutes": session_minutes, "break_minutes": break_minutes,
            "daily_subject_limit_minutes": daily_subject_limit}


def plan_study(normalized):
    """Build a conflict-free timetable with *hard* per-subject daily limits.

    Fairness is the primary ranking: give the next session to a subject with
    fewer minutes scheduled *today*. Deadline pressure only breaks ties. This
    prevents impossible demands (such as 300 hours of one subject) from
    monopolizing every free slot. Session durations and break time are still
    respected, and the planner never schedules on/after an exam date.

    The daily limit is a constraint, not a promise to fill every free hour.
    """
    subjects = normalized["subjects"]
    slots = sorted(normalized["slots"], key=lambda s: (s["date"], s["start"]))
    remaining = {s["id"]: s["minutes"] for s in subjects}
    last_used = {s["id"]: -1 for s in subjects}
    per_day_used = {}
    scheduled = []
    duration = normalized["session_minutes"]
    rest = normalized["break_minutes"]
    daily_limit = normalized.get("daily_subject_limit_minutes", 120)
    session_number = 0

    # Theoretical individual upper bounds. These ignore breaks and competition
    # for free slots, so they are never presented as guaranteed allocations.
    available_by_day = {}
    for slot in slots:
        available_by_day[slot["date"]] = (available_by_day.get(slot["date"], 0)
                                         + slot["end"] - slot["start"])

    def individual_capacity(subject, from_day=None):
        deadline = subject["exam_date"]
        return sum(min(minutes, daily_limit) for day, minutes in available_by_day.items()
                   if (from_day is None or day >= from_day)
                   and (deadline is None or day < deadline))

    individual_caps = {s["id"]: individual_capacity(s) for s in subjects}

    for slot in slots:
        day, cursor, limit = slot["date"], slot["start"], slot["end"]
        while cursor + 30 <= limit:
            candidates = [s for s in subjects
                          if remaining[s["id"]] >= 30
                          and per_day_used.get((day, s["id"]), 0) < daily_limit
                          and (s["exam_date"] is None or day < s["exam_date"])]
            if not candidates:
                break

            def priority(subject):
                sid = subject["id"]
                # High demand / scarce time before deadline matters when two
                # subjects have the same minutes already assigned today.
                capacity_left = max(30, individual_capacity(subject, day)
                                    - per_day_used.get((day, sid), 0))
                pressure = remaining[sid] / capacity_left
                # If the exam is in the next two calendar days, take its
                # urgency into account. Otherwise pick the least recently
                # scheduled subject to rotate even across short study days.
                imminent_exam = (subject["exam_date"] is not None and
                                 0 < (subject["exam_date"] - day).days <= 2)
                return (per_day_used.get((day, sid), 0),
                        0 if imminent_exam else 1,
                        last_used[sid], -pressure,
                        subject["exam_date"] or date.max, sid)

            chosen = min(candidates, key=priority)
            sid = chosen["id"]
            free_today = daily_limit - per_day_used.get((day, sid), 0)
            work = min(duration, remaining[sid], free_today,
                       ((limit - cursor) // 30) * 30)
            if work < 30:
                break
            scheduled.append({"date": day, "start": cursor, "end": cursor + work,
                              "subject": chosen["name"], "subject_id": sid})
            remaining[sid] -= work
            per_day_used[(day, sid)] = per_day_used.get((day, sid), 0) + work
            last_used[sid] = session_number
            session_number += 1
            cursor += work + rest

    warnings = []
    for s in subjects:
        sid = s["id"]
        if remaining[sid] == 0:
            continue
        cap = individual_caps[sid]
        if s["minutes"] > cap:
            before_exam = "考试前" if s["exam_date"] else "规划期内"
            warnings.append(
                f"{s['name']}：需要 {s['minutes'] / 60:g}h，"
                f"按每日最多 {daily_limit / 60:g}h/科及实际空闲日期，"
                f"{before_exam}理论上最多可安排 {cap / 60:g}h（未扣除休息和科目竞争）；"
                f"至少 {max(0, s['minutes'] - cap) / 60:g}h 无法安排。"
            )
        else:
            warnings.append(
                f"{s['name']}：仍有 {remaining[sid] / 60:g}h 未安排。"
                "请检查总空闲时间、考试日期、休息间隔及其他科目的时间竞争。"
            )

    required = sum(s["minutes"] for s in subjects)
    planned = sum(s["end"] - s["start"] for s in scheduled)
    available = sum(s["end"] - s["start"] for s in slots)
    return {
        "sessions": [{**s, "date": s["date"].isoformat(),
                      "start_time": minute_label(s["start"]),
                      "end_time": minute_label(s["end"])} for s in scheduled],
        "subjects": [{"id": s["id"], "name": s["name"],
                      "required_minutes": s["minutes"],
                      "scheduled_minutes": s["minutes"] - remaining[s["id"]],
                      "remaining_minutes": remaining[s["id"]],
                      "individual_capacity_upper_bound_minutes": individual_caps[s["id"]],
                      "exam_date": s["exam_date"].isoformat() if s["exam_date"] else None}
                     for s in subjects],
        "availability": [{"date": s["date"].isoformat(), "start": s["start"],
                          "end": s["end"]} for s in slots],
        "start_date": normalized["start"].isoformat(),
        "end_date": normalized["end"].isoformat(),
        "settings": {"session_minutes": duration, "break_minutes": rest,
                     "daily_subject_limit_minutes": daily_limit},
        "warnings": warnings,
        "summary": {"required_minutes": required, "scheduled_minutes": planned,
                    "remaining_minutes": required - planned,
                    "available_minutes": available, "session_count": len(scheduled)}
    }


def generate_plan(request):
    """Convenience API for browser request bodies and unit tests."""
    return plan_study(parse_request(request))
