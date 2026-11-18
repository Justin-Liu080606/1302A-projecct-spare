"""Regression tests for morning/afternoon balance without losing other constraints."""

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
import unittest

from study_plan import generate_plan

START = date(2026, 11, 16)


def request(days=7, subjects=None, daily_windows=None, **changes):
    payload = {
        "start_date": START.isoformat(),
        "end_date": (START + timedelta(days=days - 1)).isoformat(),
        "subjects": subjects or [
            {"name": "Python", "hours": 10},
            {"name": "Mathematics", "hours": 8},
            {"name": "English", "hours": 6},
        ],
        "daily_windows": daily_windows or [
            {"start": "08:00", "end": "11:00"},
            {"start": "14:00", "end": "17:00"},
        ],
        "session_minutes": 60,
        "break_minutes": 10,
        "daily_subject_limit_minutes": 120,
    }
    payload.update(changes)
    return payload


class TimeWindowBalanceTests(unittest.TestCase):
    def test_one_day_uses_morning_and_afternoon_when_demand_exists(self):
        plan = generate_plan(request(days=1, subjects=[
            {"name": "Python", "hours": 1},
            {"name": "Math", "hours": 1},
        ]))
        hours = [s["start"] for s in plan["sessions"]]
        self.assertEqual(plan["summary"]["scheduled_minutes"], 120)
        self.assertTrue(any(480 <= t < 660 for t in hours))
        self.assertTrue(any(840 <= t < 1020 for t in hours))

    def test_full_week_allocates_similar_study_time_to_both_windows(self):
        plan = generate_plan(request())
        morning = sum(s["end"] - s["start"] for s in plan["sessions"] if s["start"] < 720)
        afternoon = sum(s["end"] - s["start"] for s in plan["sessions"] if s["start"] >= 720)
        self.assertEqual(plan["summary"]["remaining_minutes"], 0)
        self.assertGreater(morning, 0)
        self.assertGreater(afternoon, 0)
        self.assertLessEqual(abs(morning - afternoon), 180)
        self.assertTrue(any(s["date"] == "2026-11-22" for s in plan["sessions"]))

    def test_single_light_subject_alternates_windows_across_active_dates(self):
        plan = generate_plan(request(days=28, subjects=[{"name": "Light", "hours": 3}]))
        self.assertEqual(plan["summary"]["remaining_minutes"], 0)
        morning = sum(s["end"] - s["start"] for s in plan["sessions"] if s["start"] < 720)
        afternoon = sum(s["end"] - s["start"] for s in plan["sessions"] if s["start"] >= 720)
        self.assertEqual((morning, afternoon), (90, 90))
        days = {s["date"] for s in plan["sessions"]}
        self.assertGreaterEqual(len(days), 4)
        self.assertGreaterEqual(max(days), "2026-12-01")

    def test_unequal_windows_follow_capacity_instead_of_half_half(self):
        plan = generate_plan(request(days=1, subjects=[
            {"name": "A", "hours": 2}, {"name": "B", "hours": 2}
        ], daily_windows=[
            {"start": "08:00", "end": "09:00"},
            {"start": "14:00", "end": "17:00"},
        ], break_minutes=0))
        morning = sum(s["end"] - s["start"] for s in plan["sessions"] if s["start"] < 720)
        afternoon = sum(s["end"] - s["start"] for s in plan["sessions"] if s["start"] >= 720)
        self.assertEqual((morning, afternoon), (60, 180))

    def test_daily_limits_priority_and_exam_dates_still_hold(self):
        plan = generate_plan(request(days=10, subjects=[
            {"name": "Top", "hours": 100, "exam_date": "2026-11-21"},
            {"name": "Middle", "hours": 100},
            {"name": "Low", "hours": 100},
        ]))
        daily_subject = defaultdict(int)
        daily_events = defaultdict(list)
        for session in plan["sessions"]:
            daily_subject[(session["date"], session["subject_id"])] += session["end"] - session["start"]
            daily_events[session["date"]].append(session)
            if session["subject_id"] == 0:
                self.assertLess(session["date"], "2026-11-21")
        self.assertTrue(all(v <= 120 for v in daily_subject.values()))
        for sessions in daily_events.values():
            for earlier, later in zip(sessions, sessions[1:]):
                self.assertLessEqual(earlier["end"] + 10, later["start"])

    def test_day_specific_window_override_respected(self):
        plan = generate_plan(request(days=2, subjects=[{"name": "Python", "hours": 2}],
                                     date_overrides=[
                                         {"date": "2026-11-16", "windows": [
                                             {"start": "08:00", "end": "09:00"}]},
                                         {"date": "2026-11-17", "windows": [
                                             {"start": "14:00", "end": "15:00"}]},
                                     ]))
        self.assertEqual(plan["summary"]["remaining_minutes"], 0)
        self.assertEqual([(s["start_time"], s["date"]) for s in plan["sessions"]],
                         [("08:00", "2026-11-16"), ("14:00", "2026-11-17")])

    def test_break_is_respected_even_across_nearly_touching_windows(self):
        plan = generate_plan(request(days=1, subjects=[
            {"name": "A", "hours": 2}, {"name": "B", "hours": 2}
        ], daily_windows=[
            {"start": "08:00", "end": "09:00"},
            {"start": "09:05", "end": "10:35"},
        ]))
        for left, right in zip(plan["sessions"], plan["sessions"][1:]):
            self.assertGreaterEqual(right["start"] - left["end"], 10)

    def test_web_ui_describes_window_balancing_in_english(self):
        html = (Path(__file__).parents[1] / "study_plan/static/index.html").read_text()
        self.assertIn("balanced between morning, afternoon", html)


if __name__ == "__main__":
    unittest.main()
