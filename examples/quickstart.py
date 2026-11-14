"""Install: pip install cs1302-study-planner-group06
Run: python examples/quickstart.py
"""

from study_plan import generate_plan, render_week_html, summarize_plan, to_ics

request = {
    "start_date": "2026-11-16",
    "end_date": "2026-11-22",
    "subjects": [
        {"name": "CS1302 Python", "hours": 5, "exam_date": "2026-11-21"},
        {"name": "Mathematics", "hours": 6},
        {"name": "English", "hours": 2},
    ],
    "daily_windows": [
        {"start": "08:00", "end": "11:00"},
        {"start": "14:00", "end": "17:00"},
    ],
    "date_overrides": [{"date": "2026-11-18", "windows": []}],
    "session_minutes": 60,
    "break_minutes": 10,
    "daily_subject_limit_minutes": 120,  # Two hours per subject per day
}

plan = generate_plan(request)
print(summarize_plan(plan))
with open("study_schedule.html", "w", encoding="utf-8") as f:
    f.write(render_week_html(plan))
with open("study_schedule.ics", "w", encoding="utf-8", newline="") as f:
    f.write(to_ics(plan))
print("Created study_schedule.html and study_schedule.ics")
