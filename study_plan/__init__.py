"""Reusable scheduling tools for the CS1302 Smart Study Planner.

Example::

    from study_plan import generate_plan
    plan = generate_plan({ ... })

The package uses only the Python standard library; a browser is optional.
"""

from .planner import InputError, generate_plan
from .exports import to_ics, render_week_html, summarize_plan

__version__ = "0.5.0"
__all__ = ["InputError", "generate_plan", "to_ics", "render_week_html", "summarize_plan"]
