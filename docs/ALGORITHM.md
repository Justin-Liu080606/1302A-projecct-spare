# Algorithm and novelty

## Problem

Traditional to-do lists usually record *what* to study, but leave the learner to calculate *when*. This package converts a desired workload into collision-free study sessions constrained by actual free-time windows.

## Algorithm, explained (v0.3.0)

1. Validate study subjects, deadlines and availability. Merge overlapping and adjacent availability windows.
2. Read `daily_subject_limit_minutes` (default **120 = 2 hours**). It is a **hard cap** per `(date, subject_id)`; even an urgent exam may not break it.
3. Traverse free windows chronologically. At each study session, consider only subjects with unfinished workload, before their exam date and below the daily cap.
4. **Priority-weighted fair queuing:** the first subject has the highest priority weight (`n` for `n` subjects); each next subject has a weight one lower. Select the eligible subject with the smallest ratio `total_scheduled_minutes / priority_weight`. Break ties by already scheduled minutes today and then input order. Alternate subjects within the same day whenever another eligible subject is available. Deadline dates constrain eligibility, but do not override the user's chosen ordering.
5. Limit each generated event by available time, unfinished demand, session length and remaining daily subject allowance. Add a configured break before scheduling the next event in the same window.
6. Report scheduled and remaining hours. For each subject, calculate a *theoretical upper bound* of `sum(min(daily_free_minutes, daily_subject_limit_minutes))` over dates before its exam. This bound deliberately ignores breaks and competition and must not be reported as a guaranteed allocation. Display warnings if required time exceeds the bound or if work remains unscheduled.

This intentionally favors a diverse and workable calendar over filling all free time. If only one subject remains and it has reached 2h that day, further time slots stay empty. The user may change the cap or extend dates, but the engine never silently violates the chosen cap.

The algorithm is deterministic and explainable, **not an AI predictor or an optimality guarantee**. It uses 30-minute workload increments, which may leave small gaps unused.

## Distinguishing reusable features

- `generate_plan(request)`: pure Python JSON-like input/output, independent of a GUI or notebook
- Hard configurable daily cap and input-order priority-weighted fair rotation across days
- Per-date availability overrides, overlapping-window handling, no-overlap guarantees
- Transparent unmet demand, theoretical per-subject capacity before exams, and completion percentage
- `render_week_html(plan)` for JupyterHub notebooks, `to_ics(plan)` for calendar import
- Optional polished local web UI using no third-party web framework

## Complexity

For `S` subjects, `D` planning dates, and `K` generated sessions, eligibility and priority selection take approximately O(K*S), plus O(S*D) to compute theoretical per-subject capacities. Inputs are bounded to 20 subjects and 63 dates.

## Limitations

The algorithm does not know study difficulty, individual energy levels or actual learning outcomes; user-supplied hours are estimates. Calendar exports use floating local times: importers assume their local timezone. It cannot guarantee the full plan fits when demand exceeds capacity.


## Priority order (v0.3.0)

Input order is meaningful: first subject is highest priority. The browser lets users move subject cards up and down; the JSON API uses the `subjects` list order.

Each subject receives a weight of `number_of_subjects - zero_based_index` (for example, 3 / 2 / 1). For each eligible time slot, the planner picks the subject with the lowest `(total_allocated_minutes / priority_weight)` value, with stable input-order tie-breaking. Whenever possible, it avoids selecting the same subject for two consecutive sessions on one day. This is **weighted fair scheduling**, subject to hard daily per-subject limits and exam-date cutoffs.

**Fairness qualification:** the system favors higher-ranked subjects when study time is scarce, but cannot guarantee strictly greater allocated hours or completion percentages in every scenario. If availability allows every subject to reach the daily cap, equal total hours are expected. No subject is scheduled on or after its exam date.
