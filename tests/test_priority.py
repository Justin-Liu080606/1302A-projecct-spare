"""Priority ordering, balanced allocations, deadline limits and internationalization."""

from collections import defaultdict
from pathlib import Path
import re
import unittest

from study_plan import generate_plan


def priority_request(subjects=None, **changes):
    request = {
        "start_date": "2026-11-16",
        "end_date": "2026-11-22",
        "subjects": subjects or [
            {"name": "First", "hours": 100},
            {"name": "Second", "hours": 100},
            {"name": "Third", "hours": 100},
        ],
        "daily_windows": [{"start": "08:00", "end": "11:00"}],
        "session_minutes": 60,
        "break_minutes": 0,
        "daily_subject_limit_minutes": 120,
    }
    request.update(changes)
    return request


class PrioritySchedulingTests(unittest.TestCase):
    def test_input_order_becomes_public_priority(self):
        plan = generate_plan(priority_request())
        self.assertEqual([(s["name"], s["priority_rank"], s["priority_weight"])
                          for s in plan["subjects"]],
                         [("First", 1, 3), ("Second", 2, 2), ("Third", 3, 1)])
        self.assertEqual(plan["sessions"][0]["subject"], "First")

    def test_higher_priority_gets_more_hours_under_shortage(self):
        plan = generate_plan(priority_request())
        hours = [s["scheduled_minutes"] for s in plan["subjects"]]
        self.assertGreater(hours[0], hours[1])
        self.assertGreater(hours[1], hours[2])
        self.assertEqual(sum(hours), 21 * 60)
        self.assertEqual({s["subject"] for s in plan["sessions"][:3]},
                         {"First", "Second", "Third"})

    def test_order_change_changes_allocation(self):
        old = generate_plan(priority_request())
        swapped = [
            {"name": "Third", "hours": 100},
            {"name": "Second", "hours": 100},
            {"name": "First", "hours": 100},
        ]
        new = generate_plan(priority_request(subjects=swapped))
        old_alloc = {s["name"]: s["scheduled_minutes"] for s in old["subjects"]}
        new_alloc = {s["name"]: s["scheduled_minutes"] for s in new["subjects"]}
        self.assertGreater(old_alloc["First"], old_alloc["Third"])
        self.assertGreater(new_alloc["Third"], new_alloc["First"])

    def test_input_priority_breaks_ties_over_exam_date(self):
        plan = generate_plan(priority_request(subjects=[
            {"name": "High", "hours": 20, "exam_date": "2026-12-01"},
            {"name": "Low", "hours": 20, "exam_date": "2026-11-18"},
        ]))
        self.assertEqual(plan["sessions"][0]["subject"], "High")
        self.assertTrue(all(s["date"] < "2026-11-18"
                            for s in plan["sessions"] if s["subject"] == "Low"))

    def test_daily_cap_and_no_overlap_still_apply(self):
        plan = generate_plan(priority_request(daily_windows=[
            {"start": "08:00", "end": "12:00"},
            {"start": "14:00", "end": "18:00"},
        ]))
        by_day = defaultdict(list)
        by_subject = defaultdict(int)
        for s in plan["sessions"]:
            by_day[s["date"]].append(s)
            by_subject[(s["date"], s["subject_id"])] += s["end"] - s["start"]
        for sessions in by_day.values():
            for a, b in zip(sessions, sessions[1:]):
                self.assertLessEqual(a["end"], b["start"])
        self.assertTrue(all(minutes <= 120 for minutes in by_subject.values()))

    def test_ample_capacity_does_not_waste_hours_to_force_inequality(self):
        plan = generate_plan(priority_request(daily_windows=[
            {"start": "08:00", "end": "14:00"},
        ]))
        hours = [s["scheduled_minutes"] for s in plan["subjects"]]
        self.assertEqual(hours, [14 * 60] * 3)

    def test_web_priority_hint_and_reorder_controls(self):
        html = (Path(__file__).parents[1] / "study_plan/static/index.html").read_text()
        js = (Path(__file__).parents[1] / "study_plan/static/app.js").read_text()
        self.assertIn("Please arrange subjects from highest to lowest priority", html)
        self.assertIn("move-subject-up", html)
        self.assertIn("move-subject-down", html)
        self.assertIn("insertBefore", js)
        self.assertIn('lang="en"', html)

    def test_packaged_text_sources_are_english_only(self):
        root = Path(__file__).parents[1]
        for subdir in (root / "study_plan", root / "docs", root / "examples"):
            for path in subdir.rglob("*"):
                if path.suffix in (".py", ".md", ".html", ".css", ".js", ".ipynb"):
                    with self.subTest(path=path):
                        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", path.read_text()))


if __name__ == "__main__":
    unittest.main()
