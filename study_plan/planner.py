"""Smart Study Planner: validate a form request and build an explainable timetable.

This module has no web framework dependencies. Dates are local calendar dates,
while time intervals use minutes since midnight (end exclusive).
"""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re

TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$|^24:00$")
MAX_DAYS = 63
MAX_SUBJECTS = 20
MAX_WINDOWS = 12


class InputError(ValueError):
    """Invalid user form values (safe to display in the interface)."""


def parse_date(value, label):
    if not isinstance(value, str):
        raise InputError(f"{label} must use YYYY-MM-DD format.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise InputError(f"{label} is not a valid calendar date.") from exc
    if parsed.isoformat() != value:
        raise InputError(f"{label} must use YYYY-MM-DD format.")
    return parsed


def parse_time(value, *, is_end=False):
    if not isinstance(value, str) or not TIME_RE.fullmatch(value):
        raise InputError("Time must use HH:MM format, such as 08:00.")
    if value == "24:00" and not is_end:
        raise InputError("24:00 may only be used as an end time.")
    h, m = map(int, value.split(":"))
    return h * 60 + m


def minute_label(value):
    return f"{value // 60:02d}:{value % 60:02d}"


def parse_windows(value, label):
    if not isinstance(value, list) or len(value) > MAX_WINDOWS:
        raise InputError(f"{label} supports at most {MAX_WINDOWS} time windows.")
    windows = []
    for item in value:
        if not isinstance(item, dict):
            raise InputError(f"{label} contains an invalid time window.")
        start = parse_time(item.get("start"))
        end = parse_time(item.get("end"), is_end=True)
        if end - start < 30:
            raise InputError(f"{label} requires time windows of at least 30 minutes.")
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
        raise InputError(f"Please enter between 1 and {MAX_SUBJECTS} subjects.")
    subjects = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise InputError(f"Subject #{index + 1} is invalid.")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            raise InputError(f"Subject #{index + 1} must have a name of 1–80 characters.")
        raw_hours = item.get("hours")
        try:
            hours = Decimal(str(raw_hours))
        except (InvalidOperation, ValueError) as exc:
            raise InputError(f"{name}: required study hours must be a valid number.") from exc
        if not hours.is_finite() or not (Decimal("0") < hours <= Decimal("500")):
            raise InputError(f"{name}: required study hours must be more than 0 and at most 500.")
        minutes = hours * 60
        if minutes % 30 != 0:
            raise InputError(f"{name}: required study hours must be in 0.5-hour increments.")
        raw_deadline = item.get("exam_date")
        exam_date = parse_date(raw_deadline, f"{name} exam date") if raw_deadline else None
        subjects.append({"id": index, "name": name.strip(), "minutes": int(minutes),
                         "exam_date": exam_date})
    return subjects


def parse_request(data):
    """Return normalized input; all error messages are suitable for the UI."""
    if not isinstance(data, dict):
        raise InputError("Invalid request format.")
    start = parse_date(data.get("start_date"), "Start date")
    end = parse_date(data.get("end_date"), "End date")
    if end < start:
        raise InputError("End date cannot be before start date.")
    if (end - start).days + 1 > MAX_DAYS:
        raise InputError(f"A plan can cover at most {MAX_DAYS} days.")
    subjects = parse_subjects(data.get("subjects"))
    daily = parse_windows(data.get("daily_windows", []), "Default free time")
    raw_overrides = data.get("date_overrides", [])
    if not isinstance(raw_overrides, list) or len(raw_overrides) > MAX_DAYS:
        raise InputError("Invalid date-specific availability format.")
    overrides = {}
    for obj in raw_overrides:
        if not isinstance(obj, dict):
            raise InputError("Invalid date-specific availability format.")
        day = parse_date(obj.get("date"), "Custom date")
        if not start <= day <= end:
            raise InputError(f"{day.isoformat()} is outside the planning date range.")
        if day in overrides:
            raise InputError(f"Only one override is allowed for {day.isoformat()}.")
        overrides[day] = parse_windows(obj.get("windows", []), f"Availability on {day}")

    session_minutes = data.get("session_minutes", 60)
    break_minutes = data.get("break_minutes", 10)
    daily_subject_limit = data.get("daily_subject_limit_minutes", 120)
    if (type(daily_subject_limit) is not int or
            not 60 <= daily_subject_limit <= 480 or
            daily_subject_limit % 30 != 0):
        raise InputError("Daily per-subject limit must be between 1 and 8 hours, in 30-minute increments.")
    if type(session_minutes) is not int or session_minutes not in (30, 60, 90):
        raise InputError("Session length must be 30, 60, or 90 minutes.")
    if type(break_minutes) is not int or break_minutes not in (0, 5, 10, 15):
        raise InputError("Break length must be 0, 5, 10, or 15 minutes.")
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
    """Schedule sessions using explicit user-defined priority order.

    Subjects are ranked from highest to lowest in the incoming list. A
    priority-weighted fair-queuing score gives earlier subjects more total
    study time when capacity is scarce, while alternating subjects whenever
    possible. A hard per-subject daily limit prevents monopolization.

    Work is paced across the entire eligible date range rather than front-loaded.
    Within each date, study time is balanced over available windows, with
    alternating tie-breaks so light days do not always land in the morning.
    Priority never overrides availability, completion, or exam cutoffs.
    When capacities are abundant, subjects may receive equal hours because
    the planner does not waste usable time just to force unequal totals.
    """
    subjects = normalized["subjects"]
    slots = sorted(normalized["slots"], key=lambda s: (s["date"], s["start"]))
    remaining = {s["id"]: s["minutes"] for s in subjects}
    total_used = {s["id"]: 0 for s in subjects}
    per_day_used = {}
    scheduled = []
    duration = normalized["session_minutes"]
    rest = normalized["break_minutes"]
    daily_limit = normalized.get("daily_subject_limit_minutes", 120)

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

    # A cumulative, date-aware pacing target spreads shorter workloads across
    # the full selected period rather than filling the earliest dates first.
    # Targets count half-hour study units, respecting each subject's exam cutoff.
    # Days with more free time receive a proportionally larger share, while
    # days without availability receive nothing. A deadline naturally shortens
    # the pacing horizon to eligible dates before that exam.
    pacing_targets = {}
    for subject in subjects:
        sid = subject["id"]
        target_units = min(subject["minutes"], individual_caps[sid]) // 30
        eligible = [
            (day, min(minutes, daily_limit) // 30)
            for day, minutes in sorted(available_by_day.items())
            if minutes >= 30 and
            (subject["exam_date"] is None or day < subject["exam_date"])
        ]
        total_weight = sum(weight for _, weight in eligible)
        cumulative_weight = 0
        for day, weight in eligible:
            cumulative_weight += weight
            # Round to the nearest half-hour, using integer arithmetic to avoid
            # floating-point drift. The final eligible day gets the full target.
            pacing_targets[(day, sid)] = (
                (target_units * cumulative_weight * 2 + total_weight)
                // (2 * total_weight)
            ) * 30 if total_weight else 0

    # Work out WHICH dates need study first (pacing_targets above), then choose
    # WHERE within each date to place those sessions.  Filling each morning
    # window to completion before moving to the afternoon makes a calendar
    # appear lopsided even when the dates themselves are well balanced.
    slots_by_day = {}
    for slot in slots:
        slots_by_day.setdefault(slot["date"], []).append(slot)

    active_day_count = 0
    for day, day_slots in sorted(slots_by_day.items()):
        windows = [
            {"start": slot["start"], "end": slot["end"],
             "cursor": slot["start"], "used": 0, "capacity": slot["end"] - slot["start"]}
            for slot in day_slots
        ]
        day_sessions = []
        previous_subject = None
        # Rotate equal-utilization ties by date: when a day requires only one
        # session, it alternates between morning/afternoon across the week.
        rotation = active_day_count % len(windows)

        while True:
            candidates = [s for s in subjects
                          if remaining[s["id"]] >= 30
                          and per_day_used.get((day, s["id"]), 0) < daily_limit
                          and total_used[s["id"]] < pacing_targets.get((day, s["id"]), 0)
                          and (s["exam_date"] is None or day < s["exam_date"])]
            if not candidates:
                break

            # Choose a window with the smallest fraction already occupied by
            # actual study (rather than always the earliest window).  Larger
            # windows can naturally receive more sessions than shorter ones.
            # Also honor the configured break across nearly touching windows,
            # even when the windows were filled out of chronological order.
            available_windows = []
            for index, window in enumerate(windows):
                cursor, limit = window["cursor"], window["end"]
                for event in day_sessions:
                    if event["end"] <= cursor:
                        cursor = max(cursor, event["end"] + rest)
                    elif event["start"] >= window["end"]:
                        limit = min(limit, event["start"] - rest)
                if cursor + 30 <= limit:
                    available_windows.append((index, window, cursor, limit))
            if not available_windows:
                break

            index, window, cursor, limit = min(
                available_windows,
                key=lambda item: (Fraction(item[1]["used"], item[1]["capacity"]),
                                  (item[0] - rotation) % len(windows)),
            )

            # Prefer a different subject from the most recently chosen one,
            # without overriding exam eligibility, caps or pacing targets.
            alternate = [s for s in candidates if s["id"] != previous_subject]
            if alternate:
                candidates = alternate

            def priority(subject):
                sid = subject["id"]
                weight = len(subjects) - sid  # rank 1 gets the largest weight
                return (Fraction(total_used[sid], weight),
                        per_day_used.get((day, sid), 0), sid)

            chosen = min(candidates, key=priority)
            sid = chosen["id"]
            free_today = daily_limit - per_day_used.get((day, sid), 0)
            work = min(duration, remaining[sid], free_today,
                       pacing_targets[(day, sid)] - total_used[sid],
                       ((limit - cursor) // 30) * 30)
            if work < 30:
                break
            event = {"date": day, "start": cursor, "end": cursor + work,
                     "subject": chosen["name"], "subject_id": sid}
            scheduled.append(event)
            day_sessions.append(event)
            remaining[sid] -= work
            per_day_used[(day, sid)] = per_day_used.get((day, sid), 0) + work
            total_used[sid] += work
            previous_subject = sid
            window["cursor"] = cursor + work + rest
            window["used"] += work

        if day_sessions:
            active_day_count += 1

    # Windows may have been filled out of chronological order.  Public API,
    # calendar rendering, and ICS export all receive time-ordered sessions.
    scheduled.sort(key=lambda event: (event["date"], event["start"], event["subject_id"]))

    warnings = []
    for s in subjects:
        sid = s["id"]
        if remaining[sid] == 0:
            continue
        cap = individual_caps[sid]
        if s["minutes"] > cap:
            period = "before the exam" if s["exam_date"] else "in the planning period"
            warnings.append(
                f"Priority #{sid + 1} · {s['name']}: requires {s['minutes'] / 60:g}h. "
                f"With a {daily_limit / 60:g}h daily subject limit and the "
                f"available dates, the theoretical maximum {period} is "
                f"{cap / 60:g}h (before breaks and competing subjects). "
                f"At least {max(0, s['minutes'] - cap) / 60:g}h cannot fit."
            )
        else:
            warnings.append(
                f"Priority #{sid + 1} · {s['name']}: {remaining[sid] / 60:g}h "
                "remain unscheduled. Check available time, exam dates, "
                "breaks, and competing subjects."
            )

    required = sum(s["minutes"] for s in subjects)
    planned = sum(s["end"] - s["start"] for s in scheduled)
    available = sum(s["end"] - s["start"] for s in slots)
    return {
        "sessions": [{**s, "date": s["date"].isoformat(),
                      "start_time": minute_label(s["start"]),
                      "end_time": minute_label(s["end"])} for s in scheduled],
        "subjects": [{"id": s["id"], "name": s["name"],
                      "priority_rank": s["id"] + 1,
                      "priority_weight": len(subjects) - s["id"],
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
