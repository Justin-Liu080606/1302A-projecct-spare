# CS1302 submission checklist / publication

The ZIP is **not a published PyPI release**. Members of the group must carry out the following steps in their **public** team GitHub repository and their own PyPI account.

## 1. Collaborate in public Git

- Keep the same public repository with all the Python package source files and `pyproject.toml` at its root.
- Each member works on features, tests, documentation or review, commits their own work and pushes to their own branch.
- Open pull requests, review changes and merge into the default branch. Do not manufacture or backdate commits.
- Before release, update the repository homepage in `pyproject.toml` if the real public URL is different.

## 2. Install locally (without PyPI)

From the project root in a fresh Python environment:

```bash
python -m pip install .
python -c "from study_plan import generate_plan; print(generate_plan)"
python -m unittest discover -s tests -v
study-plan --no-browser
```

Open http://127.0.0.1:8765/ on your own computer, not JupyterHub.

## 3. Build and publish to PyPI

First ensure the distribution name `cs1302-study-planner-group06` is available on PyPI. If taken, **change only the `[project].name` field** to a unique name; Python import still uses `study_plan`. Do not rename the package directory.

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

Use an account-authorized PyPI token or trusted publishing (recommended for CI). **Do not share tokens** in project files or chat. The project version is `0.3.0`. For later releases increase `version` before re-uploading; PyPI does not let you overwrite the same distribution version.

Verify the public PyPI project URL and README render after publishing.

## 4. Validate on your course JupyterHub

In a new notebook, install the **published name** (adjust if you renamed it):

```python
%pip install -U cs1302-study-planner-group06
```

Then run `examples/jupyterhub_demo.ipynb` or copy its example:

```python
from study_plan import generate_plan, render_week_html, summarize_plan
from IPython.display import HTML, display

req = {"start_date": "2026-11-16", "end_date": "2026-11-22",
       "subjects": [{"name": "Python", "hours": 2}],
       "daily_windows": [{"start": "08:00", "end": "11:00"}],
       "session_minutes": 60, "break_minutes": 10}
plan = generate_plan(req)
print(summarize_plan(plan))
display(HTML(render_week_html(plan)))
```

**Important:** the notebook demo uses an importable API and inline HTML; it does not require the JupyterHub server to expose a localhost port. The browser web UI is an optional local demonstration.

## 5. One-minute demo script

- 0–10 s: introduce the problem and show the PyPI package page / public repository
- 10–20 s: run `%pip install <your published name>` in JupyterHub
- 20–35 s: call `generate_plan()` with subjects, availability and exam date
- 35–50 s: show the weekly calendar and completion summary
- 50–60 s: explain the user-defined priorities, fairness rotation and unmet-demand reporting

Q&A preparation: why is the algorithm innovative? Why isn't the schedule globally optimal? What happens with insufficient time or duplicate windows? How does another Python project reuse your package?

## 6. Before final submission

Confirm public GitHub history, actual public PyPI page, setup/usage docs, notebook evidence and each member's spoken participation. Upload the actual submission required by the course. A local ZIP alone is insufficient.

## Daily-cap update in release candidate 0.3.0

Before your first public release, verify the `pyproject.toml` version is `0.3.0`
and that old release files are not mixed into `dist/`.
Demonstrate an infeasible MA1508-like scenario to show that the software
allocates different subjects and explains the remaining unscheduled workload.
A local `pip install -e .` and a successful wheel build alone do **not** satisfy
the rubric requiring a publicly published PyPI distribution, public Git history,
and clean install on course JupyterHub.
