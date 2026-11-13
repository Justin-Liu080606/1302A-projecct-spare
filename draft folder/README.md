# Smart Study Planner · CS1302 Group 06

> **Installable Python package** for automatic, explainable exam-aware study scheduling, with a colored weekly calendar, optional local web UI, and `.ics` calendar export.

This is the **source code prepared for PyPI**. It has **not** been published by this ZIP: the team must publish a release from its own public repository and PyPI account before claiming the published rubric point.

## Motivation & innovation

Students often know how many hours they need to study but struggle to fit them into irregular daily availability. Existing calendar tools generally require users to arrange every event manually. Our package converts subject workloads, exam deadlines, available dates and breaks into a feasible schedule. The scheduling engine is reusable from Python/JupyterHub — not tied to the webpage. See [algorithm explanation](docs/ALGORITHM.md) for the heuristic's tradeoffs and limitations.

### Main features

- Schedule up to 20 subjects over up to 63 days with user-defined study hours.
- Multiple available windows per day; custom exceptions (including days off), with overlap merging.
- Exam deadlines influence prioritization; fair rotation reduces long blocks of one subject.
- Configurable study sessions and rest intervals; events never overlap or exceed availability.
- Report *unmet* study hours instead of promising an impossible timetable.
- Reuse results as JSON-compatible Python data, embedded JupyterHub HTML, or `.ics` calendar.
- Optional local browser UI with a colorful navigable weekly calendar, requiring no web framework.

## Installation

Python **3.9+** is required. No mandatory runtime third-party dependencies.

**Before the first PyPI release:** open a terminal in the project's root directory:

```bash
python -m pip install .
```

**After the group publishes to PyPI** (verify the distribution name before publishing):

```bash
python -m pip install cs1302-study-planner-group06
```

The distribution name in `pip install` differs from the Python **import name**, which remains `study_plan`.

## Python package usage (also works in JupyterHub)

```python
from study_plan import generate_plan, summarize_plan, render_week_html, to_ics

request = {
    "start_date": "2026-11-16",
    "end_date": "2026-11-22",
    "subjects": [
        {"name": "CS1302 Python", "hours": 5, "exam_date": "2026-11-21"},
        {"name": "Math", "hours": 6},
    ],
    "daily_windows": [
        {"start": "08:00", "end": "11:00"},
        {"start": "14:00", "end": "17:00"},
    ],
    "date_overrides": [{"date": "2026-11-18", "windows": []}],
    "session_minutes": 60,
    "break_minutes": 10,
}

plan = generate_plan(request)
print(summarize_plan(plan))
print(plan["sessions"][:2])
```

For **JupyterHub**, after installing the published package in a notebook cell, show the weekly calendar **inline**, without needing to expose a web port:

```python
from IPython.display import display, HTML
display(HTML(render_week_html(plan)))
```

For calendar apps, save an ICS file (times are floating local times, not automatically timezone-adjusted):

```python
from pathlib import Path
Path("my_plan.ics").write_bytes(to_ics(plan).encode("utf-8"))
```

See [`examples/quickstart.py`](examples/quickstart.py) and [`examples/jupyterhub_demo.ipynb`](examples/jupyterhub_demo.ipynb) for full examples.

## Web interface (PyCharm)

In PyCharm, open the entire extracted project folder and run `run.py`, or from a terminal:

```bash
python -m study_plan
# Equivalent after installation:
study-plan
```

The application opens at **http://127.0.0.1:8765/**. Enter subjects and planned hours, choose the date range and free time windows, then click **Generate Plan**. Review study sessions, subject progress and available/remaining hours in the weekly view. Use **Previous/Next Week** to navigate.

Options:

```bash
study-plan --no-browser    # print URL without opening a browser
study-plan --port 8766     # choose another port
study-plan --cli           # original terminal input mode
study-plan --demo          # original static HTML example
```

Press **Ctrl+C** in your terminal to shut down the server. It only binds to `127.0.0.1`, so it is designed for local use, not public deployment or remote JupyterHub hosting.

## Inputs, outputs and constraints

`generate_plan(request)` accepts a dictionary with these fields:

| Field | Description |
|---|---|
| `start_date`, `end_date` | Inclusive dates, `YYYY-MM-DD` |
| `subjects` | List of `{name, hours, exam_date?}` objects; hours in 0.5h increments |
| `daily_windows` | Default list of `{start, end}` windows in `HH:MM` local time |
| `date_overrides` | Optional list of `{date, windows}` replacing defaults for that date; `[]` means a day off |
| `session_minutes` | `30`, `60`, or `90` (default `60`) |
| `break_minutes` | `0`, `5`, `10`, or `15` (default `10`) |

The result includes `sessions`, `subjects`, `availability`, `start_date`, `end_date`, and `summary`. Each session has a subject, day, start/end times, and an integer subject ID. Errors raise `study_plan.InputError` for invalid requests. An examination on a particular date means the study must be scheduled **before** that date.

Output can be displayed in a notebook with `render_week_html(plan)`, summarized with `summarize_plan(plan)` or exported with `to_ics(plan)`.

## Development & testing

```bash
python -m unittest discover -s tests -v
python -m pip install .
study-plan --help
```

The package layout:

```text
pyproject.toml                 PyPI metadata, build config, console command
study_plan/                   Importable Python package
  planner.py                  Validation + exam-aware fair scheduling
  exports.py                  Jupyter HTML, ICS export, progress summary
  web_app.py                  Local HTTP interface
  static/                     Shipped HTML/CSS/JS assets
  __main__.py                 Command-line entry point
  scheduler.py                Original algorithm retained for compatibility
  input_ui.py                 Original terminal interface retained
  calendar_view.py            Original HTML export retained
tests/                        Standard-library unit and API tests
examples/                     Python and JupyterHub examples
docs/ALGORITHM.md             Algorithm, innovation, limitations
docs/PUBLISHING_AND_DEMO.md    Publish + verify on JupyterHub, 1-min presentation
run.py                        Simple PyCharm runner
```

## Publishing, teamwork and one-minute demo

**Please read [`docs/PUBLISHING_AND_DEMO.md`](docs/PUBLISHING_AND_DEMO.md).** The team must still (1) use its public Git repository with regular genuine contributions by members, (2) create a versioned wheel/source distribution, (3) upload those artifacts to PyPI with an authorized account, (4) verify fresh installation in course JupyterHub, and (5) submit/present as instructed by the course.

## Honest limitations

This is a deterministic heuristic, **not an AI predictor** or a guarantee of optimal scheduling. It cannot infer learning needs or solve impossible schedules. The included web UI runs locally and is separate from the importable package API. The package is a classroom project that may require further hardening for general production use.
