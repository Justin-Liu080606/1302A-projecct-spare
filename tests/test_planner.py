"""New web planner input, algorithm and integration regression tests."""

from datetime import date, timedelta
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

from study_plan.planner import InputError, generate_plan
from study_plan.web_app import AppHandler


START = "2026-11-16"


def payload(**changes):
    result = {
        "start_date": START,
        "end_date": "2026-11-22",
        "subjects": [{"name": "Python", "hours": "6"}, {"name": "Math", "hours": "5"}],
        "daily_windows": [{"start": "08:00", "end": "11:00"},
                          {"start": "14:00", "end": "17:00"}],
        "date_overrides": [], "session_minutes": 60, "break_minutes": 10,
    }
    result.update(changes)
    return result


class PlannerTests(unittest.TestCase):
    def check_no_overlap(self, plan):
        by_day = {}
        for s in plan["sessions"]:
            key = s["date"]
            by_day.setdefault(key, []).append(s)
            self.assertGreaterEqual(s["end"] - s["start"], 30)
            self.assertEqual((s["end"] - s["start"]) % 30, 0)
            self.assertTrue(any(w["date"] == key and w["start"] <= s["start"]
                                and s["end"] <= w["end"] for w in plan["availability"]))
        for sessions in by_day.values():
            for a, b in zip(sessions, sessions[1:]):
                self.assertLessEqual(a["end"], b["start"])
        summary = plan["summary"]
        self.assertEqual(summary["required_minutes"],
                         summary["scheduled_minutes"] + summary["remaining_minutes"])
        self.assertEqual(summary["scheduled_minutes"],
                         sum(s["end"] - s["start"] for s in plan["sessions"]))

    def test_weekly_plan_balances_and_totals(self):
        plan = generate_plan(payload())
        self.assertEqual(plan["summary"]["required_minutes"], 660)
        self.assertEqual(plan["summary"]["remaining_minutes"], 0)
        self.check_no_overlap(plan)
        names = [s["subject"] for s in plan["sessions"][:4]]
        self.assertEqual(names, ["Python", "Math", "Python", "Math"])
        self.assertEqual(plan["availability"][0]["start"], 480)

    def test_urgent_exam_and_unfinished_work(self):
        req = payload(subjects=[{"name": "Soon", "hours": 20, "exam_date": "2026-11-18"},
                                {"name": "Later", "hours": 3, "exam_date": "2026-11-23"}],
                      daily_windows=[{"start": "08:00", "end": "11:00"}])
        plan = generate_plan(req)
        self.assertEqual(plan["sessions"][0]["subject"], "Soon")
        self.assertTrue(all(s["date"] < "2026-11-18" for s in plan["sessions"] if s["subject"] == "Soon"))
        self.assertGreater(plan["subjects"][0]["remaining_minutes"], 0)
        self.check_no_overlap(plan)

    def test_override_and_empty_day(self):
        req = payload(date_overrides=[
            {"date": "2026-11-16", "windows": []},
            {"date": "2026-11-17", "windows": [{"start": "12:30", "end": "14:00"}]}
        ])
        plan = generate_plan(req)
        self.assertFalse(any(w["date"] == "2026-11-16" for w in plan["availability"]))
        self.assertEqual([(w["start"], w["end"]) for w in plan["availability"]
                          if w["date"] == "2026-11-17"], [(750, 840)])
        self.check_no_overlap(plan)

    def test_overlapping_windows_merge(self):
        plan = generate_plan(payload(
            daily_windows=[{"start": "08:00", "end": "10:00"},
                           {"start": "09:00", "end": "11:00"},
                           {"start": "11:00", "end": "11:30"}]))
        first = [w for w in plan["availability"] if w["date"] == START]
        self.assertEqual(first, [{"date": START, "start": 480, "end": 690}])
        self.assertEqual(plan["summary"]["available_minutes"], 210 * 7)
        self.check_no_overlap(plan)

    def test_break_lengths_and_partial_session(self):
        plan = generate_plan(payload(subjects=[{"name": "A", "hours": "1.5"}],
                                     daily_windows=[{"start": "08:00", "end": "11:00"}]))
        self.assertEqual([(s["start"], s["end"]) for s in plan["sessions"]],
                         [(480, 540), (550, 580)])
        self.check_no_overlap(plan)

    def test_no_availability_and_expired_deadline(self):
        req = payload(daily_windows=[], subjects=[{"name": "Old", "hours": 2, "exam_date": START}])
        plan = generate_plan(req)
        self.assertEqual(plan["summary"]["scheduled_minutes"], 0)
        self.assertEqual(plan["summary"]["remaining_minutes"], 120)
        plan2 = generate_plan(payload(subjects=[{"name": "Old", "hours": 2, "exam_date": START}]))
        self.assertEqual(plan2["summary"]["scheduled_minutes"], 0)

    def test_invalid_request_cases(self):
        cases = [
            payload(start_date="2026-02-30"),
            payload(end_date="2026-11-15"),
            payload(end_date="2027-08-01"),
            payload(subjects=[]),
            payload(subjects=[{"name": "", "hours": "3"}]),
            payload(subjects=[{"name": "Math", "hours": "1.2"}]),
            payload(subjects=[{"name": "Math", "hours": "inf"}]),
            payload(daily_windows=[{"start": "24:00", "end": "24:00"}]),
            payload(daily_windows=[{"start": "23:00", "end": "02:00"}]),
            payload(date_overrides=[{"date": "2026-11-23", "windows": []}]),
            payload(date_overrides=[{"date": START, "windows": []},
                                    {"date": START, "windows": []}]),
            payload(session_minutes=31),
            payload(break_minutes=-1),
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(InputError):
                generate_plan(case)

    def test_identical_names_are_separate_subjects(self):
        plan = generate_plan(payload(subjects=[{"name": "Math", "hours": 1},
                                                {"name": "Math", "hours": 1}]))
        self.assertEqual(len(plan["subjects"]), 2)
        self.assertEqual({s["subject_id"] for s in plan["sessions"]}, {0, 1})

    def test_html_js_css_bundle_exists(self):
        root = Path(__file__).resolve().parents[1] / "study_plan" / "static"
        for filename in ["index.html", "style.css", "app.js"]:
            self.assertGreater((root / filename).stat().st_size, 500)


class WebApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.root = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_api_returns_plan_json(self):
        body = json.dumps(payload()).encode("utf-8")
        req = Request(self.root + "/api/generate", body,
                      {"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=3) as response:
            data = json.load(response)
            self.assertEqual(response.status, 200)
        self.assertGreater(len(data["sessions"]), 0)
        self.assertEqual(data["start_date"], START)

    def test_error_response_not_server_error(self):
        body = json.dumps(payload(daily_windows=[{"start": "30:00", "end": "12:00"}])).encode()
        req = Request(self.root + "/api/generate", body, method="POST")
        with self.assertRaises(HTTPError) as failure:
            urlopen(req, timeout=3)
        self.assertEqual(failure.exception.code, 400)
        self.assertIn("error", json.load(failure.exception))

    def test_page_and_assets_and_unknown_route(self):
        for uri in ["/", "/static/style.css", "/static/app.js"]:
            with urlopen(self.root + uri, timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertGreater(len(response.read()), 500)
        with self.assertRaises(HTTPError) as failure:
            urlopen(self.root + "/secrets.txt", timeout=3)
        self.assertEqual(failure.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
