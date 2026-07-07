"""PawPal+ core domain classes.

Mirrors diagrams/uml.mmd.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, timedelta
from enum import Enum, auto
from typing import Optional


class Priority(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


# Higher value = more urgent / worth more in the scheduling knapsack.
_PRIORITY_VALUE = {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}


class TaskStatus(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    DONE = auto()


class ScheduleStrategy(Enum):
    """How Plan.generate_plan should choose which competing tasks make the cut."""

    PRIORITY = auto()    # maximize total urgency scheduled (priority + recurrence + skips)
    TASK_COUNT = auto()  # maximize the number of tasks scheduled
    FAIR_SHARE = auto()  # round-robin across pets so one pet's backlog can't hog the budget


@dataclass
class Pet:
    pet_id: str
    name: str
    species: str
    age: int
    size: str
    owner_id: str  # resolves to Owner.owner_id
    tasks: list[Task] = field(default_factory=list)

    def get_info(self) -> dict:
        """Return this pet's details as a dict."""
        return {
            "pet_id": self.pet_id,
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "size": self.size,
            "owner_id": self.owner_id,
        }

    def add_task(self, task: Task) -> None:
        """Add a task to this pet, linking it back by pet_id."""
        task.pet_id = self.pet_id
        if task.task_id not in {t.task_id for t in self.tasks}:
            self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove the task with the given task_id from this pet."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task done and, if it recurs, roll it forward to its next occurrence.

        Task.complete() only flips status -- it has no reference to this pet's task
        list to insert a follow-up into. This is the entry point that does both:
        mark the given task done, then (for daily/weekly/etc. tasks) add its
        successor here automatically. Returns the new follow-up Task, or None if
        the task was one-off or wasn't found.
        """
        task = next((t for t in self.tasks if t.task_id == task_id), None)
        if task is None:
            return None
        task.complete()
        next_task = task.next_occurrence()
        if next_task is not None:
            self.add_task(next_task)
        return next_task


@dataclass
class Task:
    task_id: str
    name: str
    pet_id: str
    duration_minutes: int
    priority: Priority
    status: TaskStatus = TaskStatus.NOT_STARTED
    recurrence: Optional[str] = None
    description: Optional[str] = None
    times_skipped: int = 0
    due_date: Optional[date] = None

    def start(self) -> None:
        """Mark this task as in progress."""
        self.status = TaskStatus.IN_PROGRESS

    def complete(self) -> None:
        """Mark this task as done."""
        self.status = TaskStatus.DONE

    def next_occurrence(self, from_date: Optional[date] = None) -> Optional["Task"]:
        """If this task recurs, return a fresh Task instance for its next due date.

        Starts from `from_date` (or this task's own due_date, or today) and steps
        forward one day at a time with timedelta(days=1), reusing `applies_on` to
        recognize a match instead of re-deriving each rule's date math by hand.
        timedelta is what makes this accurate across month/year boundaries --
        e.g. stepping from Jan 31 or across a leap day both just work, where
        manually incrementing a day-of-month integer would not. Returns None for
        one-off tasks ("once"/no recurrence), since there is no next occurrence.
        """
        if self.recurrence in (None, "once"):
            return None

        candidate = (from_date or self.due_date or date.today()) + timedelta(days=1)
        for _ in range(7):  # every supported rule repeats at least once a week
            if self.applies_on(candidate):
                break
            candidate += timedelta(days=1)
        else:
            return None

        return Task(
            task_id=f"{self.task_id}@{candidate.isoformat()}",
            name=self.name,
            pet_id=self.pet_id,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            recurrence=self.recurrence,
            description=self.description,
            due_date=candidate,
        )

    def is_done(self) -> bool:
        """Return whether this task's status is DONE."""
        return self.status == TaskStatus.DONE

    def applies_on(self, day: date) -> bool:
        """Whether this task (recurring or not) should appear in a plan for `day`."""
        if not self.recurrence or self.recurrence == "once":
            return True
        rule = self.recurrence.strip().lower()
        if rule == "daily":
            return True
        if rule == "weekdays":
            return day.weekday() < 5
        if rule == "weekends":
            return day.weekday() >= 5
        if rule.startswith("weekly:"):
            weekday_name = rule.split(":", 1)[1]
            return day.strftime("%A").lower() == weekday_name
        return True

    def urgency_score(self) -> int:
        """Higher = more worth scheduling: priority, plus a bump for recurring or
        repeatedly-skipped tasks so they don't get perpetually crowded out."""
        score = _PRIORITY_VALUE[self.priority] * 10
        if self.recurrence == "daily":
            score += 3
        elif self.recurrence not in (None, "once"):
            score += 1
        score += self.times_skipped * 3
        return score


class Owner:
    def __init__(self, owner_id: str, name: str):
        """Create an owner with no pets, available time, or preferences yet."""
        self.owner_id = owner_id
        self.name = name
        self.available_time: dict[date, int] = {}
        self.preferences: dict = {}
        self.pets: list[Pet] = []

    def set_available_time(self, day: date, minutes: int) -> None:
        """Record how many minutes this owner has free on the given day."""
        self.available_time[day] = minutes

    def get_available_time(self, day: date) -> int:
        """Return the owner's free minutes for the given day (0 if unset)."""
        return self.available_time.get(day, 0)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner, linking it back by owner_id."""
        pet.owner_id = self.owner_id
        if pet.pet_id not in {p.pet_id for p in self.pets}:
            self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        """Remove the pet with the given pet_id from this owner."""
        self.pets = [p for p in self.pets if p.pet_id != pet_id]

    def get_all_tasks(self) -> list[Task]:
        """Return all tasks across every pet this owner has."""
        return [task for pet in self.pets for task in pet.tasks]

    def completion(
        self, status: Optional[TaskStatus] = None, name: Optional[str] = None
    ) -> list[Task]:
        """Filter this owner's tasks by completion status and/or a name match.

        `status` matches exactly (e.g. TaskStatus.DONE). `name` is a case-insensitive
        substring match against each task's name. Passing both ANDs the two filters;
        passing neither returns every task.
        """
        tasks = self.get_all_tasks()
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if name is not None:
            needle = name.strip().lower()
            tasks = [t for t in tasks if needle in t.name.lower()]
        return tasks

    def set_preference(self, key: str, value) -> None:
        """Store a preference value under the given key."""
        self.preferences[key] = value

    def get_preference(self, key: str):
        """Return the preference stored under the given key, if any."""
        return self.preferences.get(key)


def _add_minutes(t: time, minutes: int) -> time:
    """Return the clock time `minutes` after `t`, wrapping past midnight."""
    total = (t.hour * 60 + t.minute + minutes) % (24 * 60)
    return time(hour=total // 60, minute=total % 60)


@dataclass
class ScheduledSlot:
    task: Task
    start: time
    end: time


def find_schedule_conflicts(*slot_lists: list[ScheduledSlot]) -> list[str]:
    """Check one or more schedules for tasks whose time windows overlap.

    Within a single Plan this will always come back empty -- _build_time_slots
    places tasks back-to-back, so one plan can never conflict with itself. This
    matters once you build separate plans per pet (or per owner) that might
    double-book the same person's time; pass each plan's `.schedule` in and any
    overlap across them is reported. Returns warning strings instead of raising,
    so a scheduling conflict is something a caller can display and route around
    rather than a crash.

    Runs an all-pairs check rather than a sweep-line: a day's task list is small
    (a handful of items), so O(n^2) is simpler to read and still effectively
    instant -- not worth the complexity of interval-sweep bookkeeping here.
    """
    all_slots = [slot for slots in slot_lists for slot in slots]
    warnings = []
    for i in range(len(all_slots)):
        a = all_slots[i]
        for j in range(i + 1, len(all_slots)):
            b = all_slots[j]
            if a.start < b.end and b.start < a.end:
                warnings.append(
                    f"Conflict: '{a.task.name}' ({a.start.strftime('%H:%M')}-{a.end.strftime('%H:%M')}) "
                    f"overlaps '{b.task.name}' ({b.start.strftime('%H:%M')}-{b.end.strftime('%H:%M')}) "
                    f"-- pet {a.task.pet_id} vs pet {b.task.pet_id}"
                )
    return warnings


class Plan:
    def __init__(self, day: date, available_time: int):
        """Create an empty plan for the given day and time budget."""
        self.date = day
        self.available_time = available_time
        self.tasks: list[Task] = []
        self.scheduled_tasks: list[Task] = []
        self.unscheduled_tasks: list[Task] = []
        self.schedule: list[ScheduledSlot] = []
        self.unscheduled_reasons: dict[str, str] = {}
        self._cache_key = None

    def generate_plan(
        self,
        owner: Owner,
        pet_ids: Optional[list[str]] = None,
        status_filter: Optional[set[TaskStatus]] = None,
        strategy: ScheduleStrategy = ScheduleStrategy.PRIORITY,
        day_start: time = time(8, 0),
    ) -> None:
        """Choose which of owner's tasks fit in the time budget, and when.

        `pet_ids` restricts consideration to those pets (default: all).
        `status_filter` restricts to those statuses (default: any not-done status).
        `strategy` controls how competing tasks are traded off against each other.
        """
        candidate_pets = (
            owner.pets if pet_ids is None else [p for p in owner.pets if p.pet_id in pet_ids]
        )
        relevant = [
            task
            for pet in candidate_pets
            for task in pet.tasks
            if not task.is_done()
            and task.applies_on(self.date)
            and (status_filter is None or task.status in status_filter)
        ]

        cache_key = (
            self.available_time,
            strategy,
            day_start,
            tuple(sorted(pet_ids)) if pet_ids else None,
            tuple(sorted(s.name for s in status_filter)) if status_filter else None,
            tuple((t.task_id, t.duration_minutes, t.priority, t.times_skipped) for t in relevant),
        )
        if cache_key == self._cache_key:
            return
        self._cache_key = cache_key

        self.tasks = relevant

        if strategy is ScheduleStrategy.FAIR_SHARE:
            scheduled, unscheduled = self._fair_share_select(candidate_pets, relevant)
        else:
            scheduled, unscheduled = self._knapsack_select(
                relevant, maximize_count=strategy is ScheduleStrategy.TASK_COUNT
            )
        scheduled.sort(key=lambda t: -t.urgency_score())

        self.scheduled_tasks = scheduled
        self.unscheduled_tasks = unscheduled

        for task in scheduled:
            task.times_skipped = 0
        for task in unscheduled:
            task.times_skipped += 1

        self._build_time_slots(day_start)
        self._build_unscheduled_reasons()

    def _knapsack_select(
        self, relevant: list[Task], maximize_count: bool
    ) -> tuple[list[Task], list[Task]]:
        """0/1 knapsack: pick the subset of `relevant` that fits `available_time`
        while maximizing total value (task count, or urgency-weighted priority)."""
        capacity = self.available_time
        n = len(relevant)
        weights = [t.duration_minutes for t in relevant]
        values = [1 if maximize_count else t.urgency_score() for t in relevant]

        dp = [[0] * (capacity + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            w, v = weights[i - 1], values[i - 1]
            for c in range(capacity + 1):
                dp[i][c] = dp[i - 1][c]
                if w <= c:
                    dp[i][c] = max(dp[i][c], dp[i - 1][c - w] + v)

        chosen = []
        c = capacity
        for i in range(n, 0, -1):
            if dp[i][c] != dp[i - 1][c]:
                chosen.append(relevant[i - 1])
                c -= weights[i - 1]
        chosen.reverse()

        chosen_ids = {t.task_id for t in chosen}
        skipped = [t for t in relevant if t.task_id not in chosen_ids]
        return chosen, skipped

    def _fair_share_select(
        self, pets: list[Pet], relevant: list[Task]
    ) -> tuple[list[Task], list[Task]]:
        """Round-robin across pets (each pet's most urgent task first) so one
        pet's backlog can't consume the whole time budget."""
        relevant_ids = {t.task_id for t in relevant}
        queues = {
            pet.pet_id: sorted(
                (t for t in pet.tasks if t.task_id in relevant_ids),
                key=lambda t: -t.urgency_score(),
            )
            for pet in pets
        }
        queues = {pid: q for pid, q in queues.items() if q}

        scheduled: list[Task] = []
        remaining = self.available_time
        while queues:
            made_progress = False
            for pid in list(queues.keys()):
                queue = queues[pid]
                # Drop any leading tasks that can never fit (remaining only shrinks
                # from here on) so one oversized task can't block this pet's turn.
                while queue and queue[0].duration_minutes > remaining:
                    queue.pop(0)
                if queue:
                    task = queue.pop(0)
                    scheduled.append(task)
                    remaining -= task.duration_minutes
                    made_progress = True
                if not queue:
                    del queues[pid]
            if not made_progress:
                break

        scheduled_ids = {t.task_id for t in scheduled}
        skipped = [t for t in relevant if t.task_id not in scheduled_ids]
        return scheduled, skipped

    def _build_time_slots(self, day_start: time) -> None:
        """Lay `self.scheduled_tasks` back-to-back starting at `day_start`.

        Tasks are already ordered by urgency at this point, so this just walks
        that order and stamps each one with a start/end time, advancing the
        cursor by each task's duration. Because slots never overlap or leave
        gaps, one plan can never conflict with itself (see find_schedule_conflicts).
        """
        self.schedule = []
        cursor = day_start
        for task in self.scheduled_tasks:
            end = _add_minutes(cursor, task.duration_minutes)
            self.schedule.append(ScheduledSlot(task=task, start=cursor, end=end))
            cursor = end

    def sort_by_time(self) -> None:
        """Sort this plan's schedule chronologically by each slot's start time.

        _build_time_slots already assigns times in order, so this is a no-op right
        after generate_plan runs. It's here for callers that reorder or rebuild
        `self.schedule` some other way and need it put back in time order. Accepts
        either a datetime.time or an "HH:MM" string for `start`, in case a caller
        swaps in slots built from formatted strings instead of time objects.
        """

        def _minutes_since_midnight(start) -> int:
            if isinstance(start, str):
                hours, minutes = (int(part) for part in start.split(":"))
                return hours * 60 + minutes
            return start.hour * 60 + start.minute

        self.schedule.sort(key=lambda slot: _minutes_since_midnight(slot.start))

    def detect_conflicts(self, *other_plans: "Plan") -> list[str]:
        """Check this plan's schedule for time overlaps against itself and,
        optionally, one or more other plans (e.g. a separate plan built for a
        different pet that shares the same owner's time). Returns a list of
        warning strings -- empty if there's nothing to flag -- so a caller can
        show them (st.warning, print, log) instead of the program crashing."""
        return find_schedule_conflicts(self.schedule, *(p.schedule for p in other_plans))

    def _build_unscheduled_reasons(self) -> None:
        """Give each unscheduled task a short reason: either it's too long to
        ever fit in today's budget, or it lost out to higher-urgency tasks."""
        self.unscheduled_reasons = {}
        for task in self.unscheduled_tasks:
            if task.duration_minutes > self.available_time:
                reason = "too long to fit in today's available time at all"
            else:
                reason = "bumped by higher-urgency tasks"
            self.unscheduled_reasons[task.task_id] = reason

    def display_plan(self) -> None:
        """Print this plan's scheduled and unscheduled tasks to the terminal."""
        print(f"Plan for {self.date} (available time: {self.available_time} min)")
        print("Scheduled:")
        for slot in self.schedule:
            t = slot.task
            print(
                f"  - {slot.start.strftime('%H:%M')}-{slot.end.strftime('%H:%M')} "
                f"{t.name} ({t.duration_minutes} min, {t.priority.name})"
            )
        if self.unscheduled_tasks:
            print("Unscheduled (out of time):")
            for task in self.unscheduled_tasks:
                reason = self.unscheduled_reasons.get(task.task_id, "")
                print(f"  - {task.name} ({task.duration_minutes} min, {task.priority.name}) - {reason}")

    def explain_plan(self) -> str:
        """Return a human-readable explanation of what was scheduled and why."""
        used = sum(t.duration_minutes for t in self.scheduled_tasks)
        lines = [
            f"Plan for {self.date}: {self.available_time} minutes available.",
            f"Scheduled {len(self.scheduled_tasks)} task(s), using {used} minute(s):",
        ]
        for slot in self.schedule:
            t = slot.task
            lines.append(
                f"  - {slot.start.strftime('%H:%M')}-{slot.end.strftime('%H:%M')} {t.name}: "
                f"{t.priority.name} priority, {t.duration_minutes} min"
            )
        if self.unscheduled_tasks:
            lines.append(
                f"Could not fit {len(self.unscheduled_tasks)} task(s) into the remaining "
                f"{self.available_time - used} minute(s):"
            )
            for task in self.unscheduled_tasks:
                reason = self.unscheduled_reasons.get(task.task_id, "")
                lines.append(
                    f"  - {task.name}: {task.priority.name} priority, {task.duration_minutes} min ({reason})"
                )
        return "\n".join(lines)
