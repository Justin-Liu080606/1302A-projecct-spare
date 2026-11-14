# Getting started — Smart Study Planner v0.3.0

## PyCharm (macOS / Windows)

1. Extract the ZIP file, and open the extracted folder containing `pyproject.toml` in PyCharm.
2. Configure a Python 3.9+ interpreter (a project-specific virtual environment is recommended).
3. Open PyCharm Terminal in the project root and run:

   ```bash
   python -m pip install -e .
   python -m unittest discover -s tests -v
   python run.py --port 8766
   ```

4. Open <http://127.0.0.1:8766/>. If port 8766 is occupied, choose another number.
5. Enter subjects **from highest to lowest priority** or use the ↑ / ↓ buttons to reorder them. The first subject is the highest priority.
6. Set required study hours, optional exam dates, planning dates, and free time. Click **Generate study plan**.
7. The 2-hour default daily per-subject cap is a hard limit; increasing priority does not override it.

## Priority behavior

The scheduler uses **priority-weighted fair scheduling**, not a strict subject-by-subject fill. When study time is limited, earlier subjects tend to receive more hours. Subjects rotate instead of dominating one day. If enough time exists for all subjects to hit their individual daily caps, totals may be equal: the planner does not intentionally leave time idle.

Priority and completion percentages are not identical: a subject needing 200 hours may show a lower completion percentage than a subject needing 20 hours even after receiving more scheduled hours.

## Testing and packaging

```bash
python -m unittest discover -s tests -v
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

Use a clean environment to test a built wheel before publishing. Publishing to PyPI or GitHub is **not** performed by this ZIP.

For international demos and PyPI instructions, see `README.md` and `docs/PUBLISHING_AND_DEMO.md`.
