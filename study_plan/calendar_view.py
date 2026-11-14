"""Render a standalone offline HTML weekly calendar."""

from datetime import timedelta
from html import escape
from pathlib import Path


COLORS = ["#dbeafe", "#fce7f3", "#dcfce7", "#fef3c7", "#ede9fe", "#cffafe"]


def format_time(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def save_calendar(start_date, available_slots, sessions, unscheduled,
                  output_path="study_plan.html"):
    """Save HTML and return absolute path; subject names are escaped."""
    days = [start_date + timedelta(days=offset) for offset in range(7)]
    first = min((slot["start"] for slot in available_slots), default=9 * 60)
    last = max((slot["end"] for slot in available_slots), default=17 * 60)
    occupied = {(s["date"], s["start"]): s for s in sessions}
    free = set()
    for slot in available_slots:
        for minute in range(slot["start"], slot["end"], 30):
            free.add((slot["date"], minute))

    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>Study Planner · Weekly Calendar</title><style>',
             'body{font-family:system-ui,sans-serif;margin:24px;color:#172033}',
             '.calendar{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:900px}',
             'th,td{border:1px solid #cbd5e1;padding:10px;text-align:center;min-width:95px}',
             'th{background:#f1f5f9}td{height:42px}.unavailable{background:#e5e7eb;color:#64748b}',
             'small{display:block;margin-top:4px}li{margin:8px 0}',
             '</style></head><body><h1>Study Planner · 7-Day Plan</h1>',
             '<p>Each cell represents 30 minutes. Gray cells are unavailable; empty cells are free.</p>',
             '<div class="calendar"><table><thead><tr><th scope="col">Time</th>']
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day in days:
        parts.append(f'<th scope="col">{day.isoformat()}<br>{weekdays[day.weekday()]}</th>')
    parts.append('</tr></thead><tbody>')
    for minute in range(first, last, 30):
        label = f"{format_time(minute)}–{format_time(minute + 30)}"
        parts.append(f'<tr><th scope="row">{label}</th>')
        for day in days:
            session = occupied.get((day, minute))
            if session:
                color = COLORS[session["subject_id"] % len(COLORS)]
                # Beyond the palette, a distinct hue keeps additional subjects distinct.
                if session["subject_id"] >= len(COLORS):
                    color = f'hsl({session["subject_id"] * 137.508 % 360:.3f},70%,88%)'
                parts.append(f'<td style="background:{color}">{escape(session["subject"])}'
                             f'<small>{label}</small></td>')
            elif (day, minute) in free:
                parts.append('<td></td>')
            else:
                parts.append('<td class="unavailable">Unavailable</td>')
        parts.append('</tr>')
    parts.append('</tbody></table></div><h2>Unscheduled study time</h2>')
    if unscheduled:
        parts.append('<ul>')
        for task in unscheduled:
            parts.append(f'<li>{escape(task["subject"])} — {task["remaining_minutes"]} minutes remaining</li>')
        parts.append('</ul>')
    else:
        parts.append('<p>All requested study time has been scheduled (0 minutes remaining).</p>')
    parts.append('</body></html>')
    path = Path(output_path).resolve()
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
