# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## ✨ Features

### Scheduling algorithms
- **Priority-weighted 0/1 knapsack** (`Plan._knapsack_select`) — selects the subset of tasks that fits the available time while maximizing total urgency, not just greedily filling by priority. Two medium-priority tasks can beat one high-priority task if they use the time budget better.
- **Task-count strategy** (`ScheduleStrategy.TASK_COUNT`) — the same knapsack, but every task is worth 1 regardless of priority, optimizing for "most things checked off" instead of "most important things done."
- **Fair-share round robin** (`Plan._fair_share_select`, `ScheduleStrategy.FAIR_SHARE`) — cycles through each pet's next most-urgent task in turn so one pet's backlog can't consume the whole day's budget; an oversized task is dropped without blocking that pet's turn in the rotation.

### Recurrence
- **Recurrence rules** (`Task.applies_on`) — `once`, `daily`, `weekdays`, `weekends`, and `weekly:<day>`, evaluated per calendar day.
- **Auto-advancing occurrences** (`Task.next_occurrence`, `Pet.complete_task`) — completing a recurring task creates its next occurrence automatically, stepping forward with `timedelta` so month/leap-year boundaries (e.g. Jan 31 → Feb 1) are handled correctly instead of manually incrementing a day-of-month integer.

### Urgency & fairness
- **Urgency scoring** (`Task.urgency_score`) — priority forms the base score; recurring tasks get a small bump (daily bumps more than weekly); tasks bumped from the schedule accumulate a `times_skipped` penalty so the same high-priority tasks can't perpetually starve out lower-priority ones.
- **Unscheduled-task explanations** (`Plan._build_unscheduled_reasons`) — every task that doesn't make the cut is tagged with why: too long to ever fit today, vs. bumped by higher-urgency tasks.

### Time & conflicts
- **Chronological slot building** (`Plan._build_time_slots`) — scheduled tasks are packed back-to-back starting from a configurable `day_start`, so a single plan can never overlap itself by construction.
- **Manual re-sort** (`Plan.sort_by_time`) — re-orders a schedule by start time for callers that rebuild `.schedule` out of order (e.g. merging several pets' plans into one combined timeline); accepts `datetime.time` or `"HH:MM"` strings.
- **Cross-plan conflict detection** (`find_schedule_conflicts`, `Plan.detect_conflicts`) — an all-pairs overlap check across one or more plans' schedules, for when each pet is scheduled independently and their times might collide. Returns warning strings instead of raising, so a caller can display and route around a conflict rather than crash.

### Filtering & lookup
- **Scope filters** (`Plan.generate_plan(pet_ids=, status_filter=)`) — restrict which pets and task statuses are even considered before the scheduling algorithm runs.
- **Search/filter** (`Owner.completion(status=, name=)`) — case-insensitive substring match on name and/or exact match on status, ANDed if both are given.

### Performance
- **Recompute caching** (`Plan._cache_key`) — `generate_plan` skips re-running the algorithm (and re-incrementing skip counts) if none of the relevant inputs changed since the last call on that `Plan` instance.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```
**sample out from the main.py**

Today's Schedule
========================================
Plan for 2026-07-01 (available time: 30 min)
Scheduled:
  - Clean litter box (5 min, HIGH)
  - Morning walk (20 min, HIGH)
Unscheduled (out of time):
  - Brush coat (10 min, MEDIUM)
  - Play session (15 min, LOW)

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

python -m pytest

# Run with coverage:
pytest --cov
```

- **Task lifecycle** — `start()`/`complete()` status transitions
- **Pet task management** — `add_task`/`remove_task` (dedup, re-linking, no-op removal), `get_info`
- **Recurrence** — `complete_task` rolling a daily task into tomorrow's occurrence; `next_occurrence` date math for daily/weekdays/weekends/weekly rules; `applies_on` filtering per rule (plus the "once tasks ignore due_date" edge case)
- **Urgency scoring** — priority ordering, recurrence bumps, skip-count escalation
- **Scheduling (`generate_plan`)** — empty/zero-budget cases, oversized tasks, the knapsack picking higher combined value over one big task, `TASK_COUNT` strategy, pet/status filters, excluding done/inapplicable tasks, skip-count updates, chronological output, and the caching-still-re-escalates-skips gotcha
- **Fair share** — round-robin across pets, dropping an oversized task while still fitting a smaller one
- **Conflict detection** — a plan never conflicts with itself, two plans double-booking, touching-but-not-overlapping slots (no conflict), identical duplicate slots (conflict)
- **Sorting** — `sort_by_time` on shuffled schedules and string `"HH:MM"` times
- **Owner** — `add_pet`/`remove_pet`, `available_time`, `preferences`, `completion` filtering by status/name
- **Plan output** — `explain_plan` and `display_plan` text content

Confidence level - 4 stars

Sample test output:

```
# Paste your pytest output here
```

===================================================================================== test session starts ======================================================================================
platform win32 -- Python 3.12.5, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\eth\OneDrive\Desktop\codepathai\pawpal
plugins: anyio-4.13.0
collected 61 items                                                                                                                                                                              

tests\test_pawpal.py .............................................................                                                                                                        [100%]

====================================================================================== 61 passed in 0.22s ======================================================================================


## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Priority/urgency-based scheduling | `Plan._knapsack_select`, `Task.urgency_score` | 0/1 knapsack maximizes total urgency-weighted value within the time budget, instead of greedily filling tasks in priority order — a combination of smaller tasks can beat one large HIGH-priority task if it uses the minutes better. |
| Maximize task count strategy | `Plan._knapsack_select` (`maximize_count=True`), `ScheduleStrategy.TASK_COUNT` | Same knapsack, but every task is worth 1 instead of its urgency score — optimizes for "most things checked off today" rather than importance. |
| Fair share across pets | `Plan._fair_share_select`, `ScheduleStrategy.FAIR_SHARE` | Round-robins each pet's most-urgent remaining task so one pet's backlog can't consume the whole time budget. |
| Task sorting (chronological) | `Plan._build_time_slots`, `Plan.sort_by_time`, `ScheduledSlot` | Scheduled tasks are packed back-to-back starting at a configurable `day_start`. `sort_by_time` re-sorts `schedule` by start time if it's ever rebuilt out of order — accepts either a `datetime.time` or an `"HH:MM"` string. |
| Filtering by pet / status | `Plan.generate_plan(pet_ids=..., status_filter=...)` | Restricts which pets and task statuses are even considered before scheduling runs. |
| Filtering by completion / name | `Owner.completion(status=..., name=...)` | Case-insensitive substring match on name, exact match on `TaskStatus`; pass either or both filters (ANDed), or neither to get everything. |
| Recurring tasks | `Task.applies_on`, `Task.recurrence` | Supports `once`, `daily`, `weekdays`, `weekends`, and `weekly:<day>` recurrence rules. |
| Auto-advancing recurring tasks | `Task.next_occurrence`, `Pet.complete_task` | Completing a recurring task automatically creates and adds its next occurrence, stepping forward with `timedelta` so month/year boundaries (e.g. Jan 31 → Feb 1) are handled correctly. |
| Conflict handling | `find_schedule_conflicts`, `Plan.detect_conflicts` | All-pairs overlap check across one or more plans' schedules. Returns warning strings instead of raising — a single plan can never conflict with itself by construction, but two separately-built plans (e.g. one per pet) sharing the same owner's time can. |
| Unscheduled explanations | `Plan._build_unscheduled_reasons` | Tags each bumped task with why it didn't make the cut: too long to ever fit today, vs. lost out to higher-urgency tasks. |
| Skip escalation | `Task.times_skipped`, `Task.urgency_score` | A task that gets bumped repeatedly accumulates urgency so it can't be perpetually crowded out by the same higher-priority tasks. |
| Recompute caching | `Plan._cache_key` | Skips re-running scheduling (and re-incrementing skip counts) if none of the relevant inputs changed since the last `generate_plan` call. |

## 📸 Demo Walkthrough

### What you can do in the app

- **Owner** — set the owner's name once; it persists for the session.
- **Pets** — add pets (name, species, age, size), view them in a table, remove one.
- **Tasks** — add a task to a pet with a duration, priority, and recurrence (`once`, `daily`, `weekdays`, `weekends`, or a specific weekday); search by name; filter by pet or status; mark a task **Start**ed, **Complete**d, or **Remove**d.
- **Build Schedule** — pick which pets to include, a strategy (maximize priority, maximize task count, or fair share across pets), a day-start time, and today's available minutes, then generate the plan.
- **Conflict check** — optionally schedule each pet independently and see whether their times collide.

### Example workflow

1. **Add a pet.** Under "Pets," enter a name/species/age/size and click **Add pet**. It appears in the pets table.
2. **Add a task.** Under "Tasks," pick the pet, set a title ("Morning walk"), duration (20 min), priority (HIGH), and recurrence (`daily`), then click **Add task**. Add a couple more tasks — mix priorities and durations so the scheduler has real choices to make.
3. **Generate today's schedule.** Under "Build Schedule," set the available time (e.g. 30 minutes) and click **Generate schedule**. The app prints which tasks were scheduled, when, and why — and which ones didn't fit and why not.
4. **Complete a task.** Back in "Tasks," select your daily task under "Update a task" and click **Complete** — a toast confirms tomorrow's occurrence was created automatically.

### Key scheduler behaviors you'll see

- The knapsack strategy can pick two smaller tasks over one larger high-priority task if it uses the available minutes better.
- A task that gets bumped from the schedule accumulates urgency (`times_skipped`) so it doesn't get bumped forever.
- Fair share round-robins between pets instead of letting one pet's backlog eat the whole budget.
- Building separate schedules per pet and checking them together surfaces real double-booked time slots.

### Sample CLI output (`python main.py`)

```
Schedule before sort_by_time():
  - 08:20 Clean litter box
  - 08:00 Morning walk

Today's Schedule (sort_by_time applied)
========================================
Plan for 2026-07-07 (available time: 30 min)
Scheduled:
  - 08:00-08:20 Morning walk (20 min, HIGH)
  - 08:20-08:25 Clean litter box (5 min, HIGH)
Unscheduled (out of time):
  - Brush coat (10 min, MEDIUM) - bumped by higher-urgency tasks
  - Play session (15 min, LOW) - bumped by higher-urgency tasks

owner.completion(status=TaskStatus.DONE):
  - Evening walk

owner.completion(name='walk'):
  - Evening walk (DONE)
  - Morning walk (NOT_STARTED)

========================================
Conflict detection demo
========================================
plan.detect_conflicts(): []

Dog-only plan (starts 08:00):
  - 08:00-08:20 Morning walk
  - 08:20-08:30 Brush coat
Cat-only plan (also starts 08:00):
  - 08:00-08:05 Clean litter box
  - 08:05-08:20 Play session

Found 2 conflict(s) -- program keeps running, just warns:
  ! Conflict: 'Morning walk' (08:00-08:20) overlaps 'Clean litter box' (08:00-08:05) -- pet p1 vs pet p2
  ! Conflict: 'Morning walk' (08:00-08:20) overlaps 'Play session' (08:05-08:20) -- pet p1 vs pet p2
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
