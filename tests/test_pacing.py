"""Regression tests: dates should remain useful throughout a long plan."""

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
import unittest

from study_plan import generate_plan


START = date(2026, 11, 16)


def request(days=28, subjects=None, **kwargs):
    payload = {
        "start_date": START.isoformat(),
        "end_date": (START + timedelta(days=days - 1)).isoformat(),
        "subjects": subjects or [
            {"name": "Python", "hours": 10},
            {"name": "Mathematics", "hours": 8},
            {"name": "English", "hours": 6},
        ],
        "daily_windows": [
            {"start": "08:00", "end": "11:00"},
            {"start": "14:00", "end": "17:00"},
        ],
        "session_minutes": 60,
        "break_minutes": 10,
        "daily_subject_limit_minutes": 120,
    }
    payload.update(kwargs)
    return payload


class DatePacingTests(unittest.TestCase):
    def test_28_day_plan_uses_both_early_and_late_weeks(self):
        plan = generate_plan(request())
        self.assertEqual(plan["summary"]["remaining_minutes"], 0)
        used = {date.fromisoformat(s["date"]) for s in plan["sessions"]}
        self.assertTrue(any(day < START + timedelta(days=7) for day in used))
        self.assertTrue(any(day >= START + timedelta(days=21) for day in used))
        # Work is not exhausted in the first week.
        first_week = sum(s["end"]-s["start"] for s in plan["sessions"]
                         if s["date"] < (START+timedelta(days=7)).isoformat())
        self.assertLess(first_week, plan["summary"]["required_minutes"] // 2)

    def test_single_light_subject_spans_long_period(self):
        plan = generate_plan(request(days=28, subjects=[{"name": "Python", "hours": 3}]))
        days = sorted({date.fromisoformat(s["date"]) for s in plan["sessions"]})
        self.assertEqual(plan["summary"]["remaining_minutes"], 0)
        self.assertGreaterEqual((days[-1] - days[0]).days, 14)
        self.assertLessEqual(len(days), 6)  # 30-minute minimum means not daily

    def test_seven_day_plan_remains_active_on_last_day(self):
        plan = generate_plan(request(days=7))
        final = (START + timedelta(days=6)).isoformat()
        self.assertTrue(any(s["date"] == final for s in plan["sessions"]))
        self.assertEqual(plan["summary"]["remaining_minutes"], 0)

    def test_exam_deadline_shortens_spreading_horizon(self):
        plan = generate_plan(request(days=28, subjects=[
            {"name": "Early exam", "hours": 4, "exam_date": "2026-11-24"},
            {"name": "No exam", "hours": 4},
        ]))
        early = [s for s in plan["sessions"] if s["subject"] == "Early exam"]
        late = [s for s in plan["sessions"] if s["subject"] == "No exam"]
        self.assertTrue(early)
        self.assertTrue(all(s["date"] < "2026-11-24" for s in early))
        self.assertTrue(any(s["date"] >= "2026-12-06" for s in late))
        self.assertEqual(plan["summary"]["remaining_minutes"], 0)

    def test_days_off_are_never_used(self):
        blocked = [
            {"date": (START+timedelta(days=i)).isoformat(), "windows": []}
            for i in (0, 1, 3, 11, 12, 13, 21)
        ]
        plan = generate_plan(request(date_overrides=blocked))
        blocked_days = {d["date"] for d in blocked}
        self.assertTrue(all(s["date"] not in blocked_days for s in plan["sessions"]))
        self.assertTrue(any(s["date"] >= "2026-12-07" for s in plan["sessions"]))

    def test_priority_and_daily_subject_caps_survive_pacing(self):
        plan = generate_plan(request(days=14, subjects=[
            {"name": "Top", "hours": 100},
            {"name": "Middle", "hours": 100},
            {"name": "Low", "hours": 100},
        ], daily_windows=[{"start": "08:00", "end": "11:00"}], break_minutes=0))
        allocated = [s["scheduled_minutes"] for s in plan["subjects"]]
        self.assertGreaterEqual(allocated[0], allocated[1])
        self.assertGreaterEqual(allocated[1], allocated[2])
        daily = defaultdict(int)
        slots = defaultdict(list)
        for session in plan["sessions"]:
            daily[(session["date"], session["subject_id"])] += session["end"]-session["start"]
            slots[session["date"]].append(session)
        self.assertTrue(all(v <= 120 for v in daily.values()))
        for sessions in slots.values():
            sessions.sort(key=lambda s: s["start"])
            self.assertTrue(all(a["end"] <= b["start"]
                                for a, b in zip(sessions, sessions[1:])))

    def test_short_plan_still_respects_exact_work_and_breaks(self):
        plan = generate_plan(request(days=1, subjects=[{"name": "Short", "hours": 1.5}]))
        self.assertEqual(plan["summary"]["scheduled_minutes"], 90)
        self.assertEqual([(s["start"], s["end"]) for s in plan["sessions"]],
                         [(480, 540), (840, 870)])

    def test_web_explains_pacing_in_english(self):
        html = (Path(__file__).parents[1] / "study_plan/static/index.html").read_text()
        self.assertIn("spread across available dates", html)
        self.assertIn("Please arrange subjects from highest to lowest priority", html)


if __name__ == "__main__":
    unittest.main()
