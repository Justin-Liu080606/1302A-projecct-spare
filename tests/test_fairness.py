"""Regression tests for the heavy-MA1508 scenario reported by the team."""

from collections import defaultdict
import unittest

from study_plan import InputError, generate_plan


def example_request(**overrides):
    request = {
        "start_date": "2026-11-14", "end_date": "2026-12-24",
        "subjects": [
            {"name": "CS2115", "hours": 100, "exam_date": "2026-12-15"},
            {"name": "CS1302", "hours": 100, "exam_date": "2026-12-10"},
            {"name": "MA1508", "hours": 300, "exam_date": "2026-12-11"},
        ],
        "daily_windows": [
            {"start": "07:30", "end": "12:00"},
            {"start": "14:00", "end": "21:30"},
        ],
        "session_minutes": 90, "break_minutes": 0,
    }
    request.update(overrides)
    return request


class FairSchedulingTests(unittest.TestCase):
    def test_all_three_subjects_appear_in_the_same_week(self):
        plan = generate_plan(example_request())
        for day in ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19"]:
            self.assertEqual({s["subject"] for s in plan["sessions"] if s["date"] == day},
                             {"CS2115", "CS1302", "MA1508"})

    def test_hard_daily_limit_even_for_urgent_300_hour_subject(self):
        plan = generate_plan(example_request())
        per_day_subject = defaultdict(int)
        for session in plan["sessions"]:
            per_day_subject[(session["date"], session["subject_id"])] += (
                session["end"] - session["start"])
        self.assertTrue(per_day_subject)
        self.assertTrue(all(0 < mins <= 120 for mins in per_day_subject.values()))
        self.assertEqual(plan["settings"]["daily_subject_limit_minutes"], 120)

    def test_impossible_subject_has_explainable_warning(self):
        plan = generate_plan(example_request())
        math = next(s for s in plan["subjects"] if s["name"] == "MA1508")
        self.assertEqual(math["individual_capacity_upper_bound_minutes"], 54 * 60)
        self.assertGreater(math["remaining_minutes"], 0)
        self.assertTrue(any("MA1508" in w and "246h" in w for w in plan["warnings"]))
        self.assertEqual(plan["summary"]["required_minutes"],
                         plan["summary"]["scheduled_minutes"] +
                         plan["summary"]["remaining_minutes"])

    def test_custom_daily_limit_increases_capacity_but_is_still_enforced(self):
        req = example_request(daily_subject_limit_minutes=180)
        plan = generate_plan(req)
        math = next(s for s in plan["subjects"] if s["name"] == "MA1508")
        self.assertEqual(math["individual_capacity_upper_bound_minutes"], 81 * 60)
        per_day = defaultdict(int)
        for session in plan["sessions"]:
            per_day[(session["date"], session["subject_id"])] += session["end"] - session["start"]
        self.assertTrue(all(minutes <= 180 for minutes in per_day.values()))

    def test_short_days_rotate_across_multiple_days(self):
        req = example_request(
            start_date="2026-11-16", end_date="2026-11-22",
            daily_windows=[{"start": "08:00", "end": "09:00"}],
            session_minutes=60,
        )
        plan = generate_plan(req)
        self.assertEqual(len(plan["sessions"]), 7)
        self.assertEqual(len({s["subject"] for s in plan["sessions"]}), 3)
        self.assertNotEqual(plan["sessions"][0]["subject"], plan["sessions"][1]["subject"])

    def test_exam_date_respected_with_daily_limit(self):
        plan = generate_plan(example_request())
        deadlines = {s["id"]: s["exam_date"] for s in plan["subjects"]}
        self.assertTrue(all(not deadlines[s["subject_id"]] or
                            s["date"] < deadlines[s["subject_id"]]
                            for s in plan["sessions"]))

    def test_invalid_daily_limits(self):
        for invalid in [0, 59, 61, 481, -120, True, 120.0, "120", None]:
            with self.subTest(value=invalid), self.assertRaises(InputError):
                generate_plan(example_request(daily_subject_limit_minutes=invalid))

    def test_no_available_time_gives_clear_warning(self):
        plan = generate_plan(example_request(daily_windows=[]))
        self.assertEqual(plan["summary"]["scheduled_minutes"], 0)
        self.assertEqual(len(plan["warnings"]), 3)
        self.assertTrue(all(s["individual_capacity_upper_bound_minutes"] == 0
                            for s in plan["subjects"]))

    def test_existing_json_api_remains_compatible(self):
        plan = generate_plan(example_request(daily_subject_limit_minutes=120))
        for key in ["sessions", "subjects", "summary", "availability",
                    "start_date", "end_date"]:
            self.assertIn(key, plan)


if __name__ == "__main__":
    unittest.main()
