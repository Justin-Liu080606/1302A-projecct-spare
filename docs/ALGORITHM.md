# Algorithm and novelty

## Problem

Traditional to-do lists usually record *what* to study, but leave the learner to calculate *when*. This package converts a desired workload into collision-free study sessions constrained by actual free-time windows.

## Algorithm, explained (v0.5.0)

1. Validate study subjects, deadlines and availability. Merge overlapping and adjacent availability windows.
2. Read `daily_subject_limit_minutes` (default **120 = 2 hours**). It is a **hard cap** per `(date, subject_id)`; even an urgent exam may not break it.
3. **Pace the workload over the full eligible period.** For every subject, calculate its available dates and an individual capacity upper bound. Create cumulative study targets across these dates, proportional to the free time available on each date, rounded to 30-minute increments. Exam dates shorten that subject's eligible period. This prevents a short workload from being packed into the first few days of a long plan.
4. Group the available windows by day. At each study session, consider only subjects with unfinished workload, before their exam date, below the daily cap **and behind their cumulative pacing target**. Choose the available time window with the **lowest fraction of study time already allocated**. This balances morning, afternoon, and other windows according to their lengths, rather than filling the first window. Break equal-usage ties by rotating the preferred window across *active* study days.
5. **Priority-weighted fair queuing:** the first subject has the highest priority weight (`n` for `n` subjects); each next subject has a weight one lower. Select the eligible subject with the smallest ratio `total_scheduled_minutes / priority_weight`. Break ties by already scheduled minutes today and then input order. Alternate subjects within the same day whenever another eligible subject is available. Deadline dates constrain eligibility, but do not override the user's chosen ordering.
6. Limit each generated event by available time, unfinished demand, session length and remaining daily subject allowance. Add a configured break before the next event in the same or nearly touching windows. Since windows can be filled in a nonchronological order, sort the output sessions by date and start time before returning results.
7. Report scheduled and remaining hours. For each subject, calculate a *theoretical upper bound* of `sum(min(daily_free_minutes, daily_subject_limit_minutes))` over dates before its exam. This bound deliberately ignores breaks and competition and must not be reported as a guaranteed allocation. Display warnings if required time exceeds the bound or if work remains unscheduled.

This intentionally favors a diverse and workable calendar over filling all free time. If only one subject remains and it has reached 2h that day, further time slots stay empty. The user may change the cap or extend dates, but the engine never silently violates the chosen cap.

The algorithm is deterministic and explainable, **not an AI predictor or an optimality guarantee**. It uses 30-minute workload increments, which may leave small gaps unused.

## Distinguishing reusable features

- `generate_plan(request)`: pure Python JSON-like input/output, independent of a GUI or notebook
- Date-aware workload pacing across the full available period, with within-day time-window balance, hard daily caps and priority-weighted fair rotation
- Per-date availability overrides, overlapping-window handling, no-overlap guarantees
- Transparent unmet demand, theoretical per-subject capacity before exams, and completion percentage
- `render_week_html(plan)` for JupyterHub notebooks, `to_ics(plan)` for calendar import
- Optional polished local web UI using no third-party web framework

## Complexity

For `S` subjects, `D` planning dates, and `K` generated sessions, eligibility and priority selection take approximately O(K*S), plus O(S*D) to calculate subject pacing targets and theoretical capacity bounds. Inputs are bounded to 20 subjects and 63 dates.

## Limitations

The algorithm does not know study difficulty, individual energy levels or actual learning outcomes; user-supplied hours are estimates. Calendar exports use floating local times: importers assume their local timezone. It cannot guarantee the full plan fits when demand exceeds capacity.


## Priority order (v0.4.0)

Input order is meaningful: first subject is highest priority. The browser lets users move subject cards up and down; the JSON API uses the `subjects` list order.

Each subject receives a weight of `number_of_subjects - zero_based_index` (for example, 3 / 2 / 1). For each eligible time slot, the planner picks the subject with the lowest `(total_allocated_minutes / priority_weight)` value, with stable input-order tie-breaking. Whenever possible, it avoids selecting the same subject for two consecutive sessions on one day. This is **weighted fair scheduling**, subject to hard daily per-subject limits and exam-date cutoffs.

**Fairness qualification:** the system favors higher-ranked subjects when study time is scarce, but cannot guarantee strictly greater allocated hours or completion percentages in every scenario. If availability allows every subject to reach the daily cap, equal total hours are expected. No subject is scheduled on or after its exam date.

## Date-aware pacing (v0.4.0)

The old behavior filled the earliest days until all requested hours were consumed, leaving the rest of a long plan empty. Version 0.4.0 sets a **cumulative target per subject per date**, then allocates only the study time needed to stay on pace. For example, a 10-hour requirement over 28 eligible days is spread through several weeks, not scheduled in the first five days.

Pacing is weighted by each day's available minutes (capped by the per-subject daily limit), rather than assuming that every date offers equal time. Date-specific days off are ignored. Subjects with an exam date pace only until the day before the exam; after the deadline they cannot receive events. Short tasks are discretized into 30-minute units, so a very light workload over many weeks will naturally leave some days empty.

If study time is scarce, the priority-weighted scheduler still selects higher-ranked subjects more often when competing for the same available window. Actual completion may be lower than the theoretical pacing target because breaks, simultaneous subject demands and deadline conflicts can constrain feasibility. This is a heuristic: it is not a formal optimality guarantee.

## Within-day time-window balance (v0.5.0)

Earlier versions paced sessions across calendar dates but filled a day's first availability window before touching later windows. If a student had 08:00–11:00 and 14:00–17:00 available, all daily tasks could end up in the morning.

Version 0.5.0 tracks the actual study minutes assigned to each daily availability window and chooses the window with the **lowest utilization fraction** (`study_minutes_in_window / window_minutes`). For equal-length morning and afternoon windows, two sessions usually go to different halves of the day. Longer windows can receive more work than shorter ones. If a day has just one session, the preferred starting window rotates across active study days so the same time of day is not always chosen.

The daily workload is still governed by the existing cumulative pacing targets. The algorithm does not create extra hours, violate exam deadlines, overlap events, or bypass per-subject daily limits. Some windows may be empty if the total demand is small, availability is limited, or a session cannot fit into the remaining space.
