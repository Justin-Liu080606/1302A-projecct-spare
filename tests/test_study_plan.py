"""可手算的排程、HTML 和输入校验案例；无需第三方测试库。"""

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
        # 每天 60 分钟，共 420；两科同日考试，输入顺序决定先后。
        tasks = [
            {"subject": '数学 <A> & "B"', "exam_date": date(2026, 11, 16), "minutes": 90},
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
        self.assertIn('数学 &lt;A&gt; &amp; &quot;B&quot;', html)
        self.assertIn(tasks[0]["subject"], text)
        self.assertIn("Python", text)
        self.assertIn("剩余 0 分钟", text)

    def test_shortage_deadlines_and_exam_priority(self):
        # 后输入的早考科优先：考前只有 60 分钟，需求 90，缺 30。
        # 晚考科在第二天用 60 分钟，需求 120，缺 60。
        tasks = [
            {"subject": "晚考 <script>alert(1)</script>",
             "exam_date": self.start + timedelta(days=2), "minutes": 120},
            {"subject": "早考 & Python", "exam_date": self.start + timedelta(days=1),
             "minutes": 90},
        ]
        sessions, missing = schedule(tasks, self.slots)
        self.assertEqual([s["subject_id"] for s in sessions], [1, 1, 0, 0])
        self.assertEqual(missing, [
            {"subject": "早考 & Python", "remaining_minutes": 30},
            {"subject": tasks[0]["subject"], "remaining_minutes": 60},
        ])
        self.check_invariants(tasks, sessions, missing)
        html, text = self.check_html(sessions, missing)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("早考 & Python：剩余 30 分钟", text)
        self.assertIn(tasks[0]["subject"] + "：剩余 60 分钟", text)

    def test_duplicate_slots_past_exams_and_midnight(self):
        slots = [{"date": self.start, "start": 1410, "end": 1440}] * 2
        tasks = [
            {"subject": "已考", "exam_date": self.start, "minutes": 30},
            {"subject": "未考", "exam_date": self.start + timedelta(days=1), "minutes": 60},
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
            "09:15", "10:00", "09:00",  # 结束早于开始，重新输入
            "09:00", "10:00",
            "09:30", "10:30",  # 与上一时段重叠
            "11:00", "12:00",
            "1", "", "数学", "invalid", "2026-11-12", "0", "-30", "45", "60",
        ]
        with patch("builtins.input", side_effect=answers), patch("builtins.print") as output:
            start, tasks, slots = collect_input()
        self.assertEqual(start, self.start)
        self.assertEqual(len(slots), 14)
        self.assertEqual(tasks[0]["minutes"], 60)
        self.assertGreaterEqual(output.call_count, 8)


if __name__ == "__main__":
    unittest.main()
