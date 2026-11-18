"""Reusable, dependency-free exports for notebooks, other apps and calendars."""

from datetime import date, timedelta, datetime, timezone
from html import escape
import re


def summarize_plan(plan):
    """Return clear, data-only completion metrics for an existing plan."""
    subjects = []
    for subject in plan["subjects"]:
        required = subject["required_minutes"]
        scheduled = subject["scheduled_minutes"]
        subjects.append({
            "name": subject["name"],
            "required_hours": round(required / 60, 2),
            "scheduled_hours": round(scheduled / 60, 2),
            "remaining_hours": round(subject["remaining_minutes"] / 60, 2),
            "completion_percentage": round(100 * scheduled / required, 1) if required else 100.0,
            "exam_date": subject["exam_date"],
        })
    return {
        "required_hours": round(plan["summary"]["required_minutes"] / 60, 2),
        "scheduled_hours": round(plan["summary"]["scheduled_minutes"] / 60, 2),
        "remaining_hours": round(plan["summary"]["remaining_minutes"] / 60, 2),
        "subjects": subjects,
    }


def _ical_escape(value):
    """Escape property text according to RFC 5545 for simple VEVENT output."""
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def to_ics(plan, calendar_name="Study Plan"):
    """Export the scheduled sessions as a calendar ICS string (floating local times).

    Times are intentionally *floating* local times because the input has no
    timezone. Importers will interpret them in their own default timezone.
    """
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CS1302 Group06//SmartStudyPlanner//EN",
             f"X-WR-CALNAME:{_ical_escape(calendar_name)}"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for idx, session in enumerate(plan["sessions"], 1):
        event_date = date.fromisoformat(session["date"])
        day = event_date.strftime("%Y%m%d")
        start = str(session["start_time"]).replace(":", "") + "00"
        end_time = str(session["end_time"])
        # RFC 5545 expects midnight at the start of the *next* calendar day.
        if end_time == "24:00":
            end_day = (event_date + timedelta(days=1)).strftime("%Y%m%d")
            end = "000000"
        else:
            end_day = day
            end = end_time.replace(":", "") + "00"
        if not re.fullmatch(r"\d{6}", start) or not re.fullmatch(r"\d{6}", end):
            raise ValueError("Invalid session time")
        lines.extend([
            "BEGIN:VEVENT", f"UID:study-{day}-{idx}@cs1302-group06",
            f"DTSTAMP:{stamp}", f"DTSTART:{day}T{start}",
            f"DTEND:{end_day}T{end}",
            f"SUMMARY:{_ical_escape('Study: ' + session['subject'])}", "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def render_week_html(plan, week_start=None):
    """Return notebook-friendly standalone HTML for a seven-day calendar.

    Run in JupyterHub with ``display(HTML(render_week_html(plan)))``.
    Subject names are HTML-escaped to prevent interpreted input.
    """
    first = date.fromisoformat(week_start or plan["start_date"])
    days = [first + timedelta(days=i) for i in range(7)]
    colors = ["#dbeafe", "#fce7f3", "#dcfce7", "#fef3c7", "#ede9fe", "#cffafe"]
    headers = "".join(f"<th style='padding:10px;background:#f1f5f9'>{d:%a %d %b}</th>" for d in days)
    columns = []
    for day in days:
        items = []
        for event in plan["sessions"]:
            if event["date"] != day.isoformat():
                continue
            color = colors[int(event["subject_id"]) % len(colors)]
            title = escape(event["subject"])
            start, end = escape(event["start_time"]), escape(event["end_time"])
            items.append(f"<div style='background:{color};border-left:4px solid #64748b;"
                         f"border-radius:8px;padding:8px;margin:5px 2px;text-align:left'>"
                         f"<strong>{title}</strong><br><small>{start}–{end}</small></div>")
        columns.append("<td style='vertical-align:top;min-width:120px;height:140px;"
                       "padding:5px;border:1px solid #d1d5db'>" + "".join(items) + "</td>")
    return ("<div style='font-family:Arial,sans-serif;color:#1e293b;overflow:auto'>"
            "<h3>Smart Study Planner · Weekly View</h3>"
            "<table style='border-collapse:collapse;width:100%;min-width:840px'><thead><tr>"
            + headers + "</tr></thead><tbody><tr>" + "".join(columns) +
            "</tr></tbody></table></div>")
