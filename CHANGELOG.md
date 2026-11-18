# Changelog

## 0.5.0 — Within-day availability balancing (PyPI release candidate)

- Spread sessions **across morning, afternoon, and other available time windows**, instead of filling the first window of each day first.
- Allocate study proportionally to window capacity; a three-hour afternoon window may receive more work than a one-hour morning window.
- Rotate tie-breaks across **active study days**, so light days with a single session do not always fall in the morning.
- Keep date-aware pacing, user-defined subject priority, study breaks, strict daily subject caps, and exam cutoffs.
- Sort all generated events chronologically before exporting the calendar.
- Add eight regression tests for time-window balance, overrides, pacing, and scheduling invariants.
- Bump version to 0.5.0; **not published to PyPI**.

## 0.4.0 — Date-aware balanced pacing (PyPI release candidate)

- Spread study requirements across the entire eligible planning period instead of filling the earliest days first.
- Preserve highest-first subject priority, subject rotation, hard daily caps, rest intervals, and exam cutoffs.
- Weight the target study pace by each date's availability; exclude days off and dates after exams.
- Explain date-aware pacing in the English web interface and package documentation.
- Add regression tests for long plans, exam dates, sparse availability, and scheduling invariants.
- Rebuild versioned source and wheel distributions; **not yet uploaded to PyPI**.

## v0.3.0 — Priority-aware international release candidate

- Subject list order now controls priority (first is highest); up/down buttons allow reordering.
- Priority-weighted fair queuing favors higher-ranked subjects under limited capacity, without abandoning rotation.
- Retains the strict per-subject daily cap and exam cutoff, including warnings for unscheduled work.
- Localized web UI, validation, command-line modes, and legacy HTML output to English.
- Added priority regression tests and updated documentation and onboarding guide.
- Build artifacts updated to 0.3.0; this package has **not** been published to PyPI.


## 0.3.0 — fairness and daily-limit update (PyPI release candidate)

- Fixed severe starvation where a high-demand subject (e.g. MA1508 at 300h) monopolized every day because its deadline pressure overrode rotation.
- Added **hard configurable per-subject daily study limit**, default 2h/day, from 1–8 hours.
- Fairly alternates subjects across sessions and across days, including days with only one available slot.
- Maintained exam awareness: exams occurring within two days influence equal-usage ties; no scheduling on/after exam dates.
- Added explicit feasibility warnings and per-subject theoretical maximum before exams (upper bound, not guaranteed).
- Added web form setting and visible warnings above the calendar.
- Added nine fairness/limits regression tests; all original tests retained.
- Bumped distribution and import versions to 0.3.0. **Not yet published to PyPI.**

## 0.1.0 — initial packaging candidate

- Turned original local planner into an installable standard-library Python distribution.
- Retained terminal and local browser interfaces.
- Added reusable importable API, Jupyter notebook HTML calendar, summary and ICS export.
- Added tests and documentation for PyPI, JupyterHub, algorithm and team workflow.

This is a packaging **candidate**, not proof of a published PyPI release.
