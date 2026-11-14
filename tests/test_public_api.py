"""Tests for the reusable PyPI/Jupyter API and export safety."""

import unittest
from study_plan import generate_plan, render_week_html, summarize_plan, to_ics


class PublicAPITests(unittest.TestCase):
    def setUp(self):
        self.plan = generate_plan({
            "start_date": "2026-11-16", "end_date": "2026-11-22",
            "subjects": [{"name": "Python & <Math>", "hours": 1.5}],
            "daily_windows": [{"start": "08:00", "end": "11:00"}],
            "session_minutes": 60, "break_minutes": 10,
        })

    def test_package_api_produces_json_ready_plan(self):
        self.assertEqual(self.plan["summary"]["scheduled_minutes"], 90)
        self.assertEqual(len(self.plan["sessions"]), 2)

    def test_summary_is_reusable(self):
        summary = summarize_plan(self.plan)
        self.assertEqual(summary["scheduled_hours"], 1.5)
        self.assertEqual(summary["subjects"][0]["completion_percentage"], 100.0)

    def test_calendar_markup_escapes_subject_names(self):
        html = render_week_html(self.plan)
        self.assertIn("Python &amp; &lt;Math&gt;", html)
        self.assertNotIn("Python & <Math>", html)
        self.assertIn("08:00", html)

    def test_calendar_export_midnight_uses_next_day(self):
        p = generate_plan({
            "start_date": "2026-11-16", "end_date": "2026-11-16",
            "subjects": [{"name": "Late", "hours": 1}],
            "daily_windows": [{"start": "23:00", "end": "24:00"}],
            "session_minutes": 60, "break_minutes": 0,
        })
        self.assertIn("DTEND:20261117T000000", to_ics(p))

    def test_calendar_export_contains_events(self):
        content = to_ics(self.plan)
        self.assertEqual(content.count("BEGIN:VEVENT"), 2)
        self.assertIn("DTSTART:20261116T080000", content)
        self.assertIn("SUMMARY:Study: Python & <Math>", content)
        self.assertTrue(content.endswith("END:VCALENDAR\r\n"))


if __name__ == "__main__":
    unittest.main()
