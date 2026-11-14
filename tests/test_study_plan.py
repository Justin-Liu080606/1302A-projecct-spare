"""Hand-computable scheduling, HTML escaping and validation tests; no third-party test framework."""

import copy
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from study_plan.calendar_view import save_calendar
from study_plan.input_ui import collect_input
from study_plan.scheduler import schedule


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def handle_data(self, data):
        self.text.append(data)


class StudyPlanTests(unittest.TestCase):
    def setUp(self):
        self.start = date(2026, 11, 9)
        self.slots = [
            {"date": self.start + timedelta(days=i), "start": 540, "end": 600}
            for i in range(7)
        ]

    def check_invariants(self, tasks, sessions, unscheduled, slots=None):
        slots = self.slots if slots is None else slots
        used = set()
        for session in sessions:
            key = (session["date"], session["start"])
            self.assertNotIn(key, used)
            used.add(key)
            self.assertEqual(session["end"] - session["start"], 30)
            self.assertLess(session["date"], tasks[session["subject_id"]]["exam_date"])
            self.assertTrue(any(slot["date"] == session["date"]
                                and slot["start"] <= session["start"]
                                and session["end"] <= slot["end"] for slot in slots))
        self.assertEqual(sum(task["minutes"] for task in tasks),
                         30 * len(sessions) + sum(t["remaining_minutes"] for t in unscheduled))

    def check_html(self, sessions, unscheduled):
        with tempfile.TemporaryDirectory() as folder:
            path = save_calendar(self.start, self.slots, sessions, unscheduled,
                                 Path(folder) / "study_plan.html")
            self.assertTrue(path.is_absolute())
            html = path.read_text(encoding="utf-8")
        parser = CalendarParser()
        parser.feed(html)
        self.assertEqual(parser.tags.count("table"), 1)
        self.assertNotIn("script", parser.tags)
        self.assertIn("2026-11-15", html)
        self.assertIn("09:00–09:30", html)
        return html, "".join(parser.text)

    def test_exact_capacity_and_stable_order(self):
        # Daily 60 minutes (420 total); for identical deadlines, input order decides.
        tasks = [
            {"subject": 'Math <A> & "B"', "exam_date": date(2026, 11, 16), "minutes": 90},
            {"subject": "Python", "exam_date": date(2026, 11, 16), "minutes": 330},
        ]
        original = copy.deepcopy((tasks, self.slots))
        sessions, missing = schedule(tasks, self.slots)
        self.assertEqual(len(sessions), 14)
        self.assertEqual(missing, [])
        self.assertEqual([s["subject_id"] for s in sessions], [0] * 3 + [1] * 11)
        self.assertEqual((tasks, self.slots), original)
        self.check_invariants(tasks, sessions, missing)
        html, text = self.check_html(sessions, missing)
        self.assertIn('Math &lt;A&gt; &amp; &quot;B&quot;', html)
        self.assertIn(tasks[0]["subject"], text)
        self.assertIn("Python", text)
        self.assertIn("0 minutes remaining", text)

    def test_shortage_deadlines_and_exam_priority(self):
        # Earlier exam on the second subject wins: 60 of 90 minutes are possible.
        # Later exam subject receives 60 of 120 requested minutes.
        tasks = [
            {"subject": "Later <script>alert(1)</script>",
             "exam_date": self.start + timedelta(days=2), "minutes": 120},
            {"subject": "Soon & Python", "exam_date": self.start + timedelta(days=1),
             "minutes": 90},
        ]
        sessions, missing = schedule(tasks, self.slots)
        self.assertEqual([s["subject_id"] for s in sessions], [1, 1, 0, 0])
        self.assertEqual(missing, [
            {"subject": "Soon & Python", "remaining_minutes": 30},
            {"subject": tasks[0]["subject"], "remaining_minutes": 60},
        ])
        self.check_invariants(tasks, sessions, missing)
        html, text = self.check_html(sessions, missing)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Soon & Python — 30 minutes remaining", text)
        self.assertIn(tasks[0]["subject"] + " — 60 minutes remaining", text)

    def test_duplicate_slots_past_exams_and_midnight(self):
        slots = [{"date": self.start, "start": 1410, "end": 1440}] * 2
        tasks = [
            {"subject": "Expired", "exam_date": self.start, "minutes": 30},
            {"subject": "Upcoming", "exam_date": self.start + timedelta(days=1), "minutes": 60},
        ]
        sessions, missing = schedule(tasks, slots)
        self.assertEqual(len(sessions), 1)
        self.assertEqual([t["remaining_minutes"] for t in missing], [30, 30])
        self.check_invariants(tasks, sessions, missing, slots)
        with tempfile.TemporaryDirectory() as folder:
            path = save_calendar(self.start, slots, sessions, missing, Path(folder) / "end.html")
            self.assertIn("23:30–24:00", path.read_text(encoding="utf-8"))

    def test_interactive_validation_and_multiple_windows(self):
        answers = [
            "2026-02-30", "2026-11-09", "0", "2",
            "09:15", "10:00", "09:00",  # End before start; should prompt again
            "09:00", "10:00",
            "09:30", "10:30",  # Overlaps with previous time window
            "11:00", "12:00",
            "1", "", "Math", "invalid", "2026-11-12", "0", "-30", "45", "60",
        ]
        with patch("builtins.input", side_effect=answers), patch("builtins.print") as output:
            start, tasks, slots = collect_input()
        self.assertEqual(start, self.start)
        self.assertEqual(len(slots), 14)
        self.assertEqual(tasks[0]["minutes"], 60)
        self.assertGreaterEqual(output.call_count, 8)


if __name__ == "__main__":
    unittest.main()
