"""PawPal+ core domain classes.

Mirrors diagrams/uml.mmd.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from typing import Optional


class Priority(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


# Lower number = scheduled first.
_PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}


class TaskStatus(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    DONE = auto()


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

    def start(self) -> None:
        """Mark this task as in progress."""
        self.status = TaskStatus.IN_PROGRESS

    def complete(self) -> None:
        """Mark this task as done."""
        self.status = TaskStatus.DONE

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

    def set_preference(self, key: str, value) -> None:
        """Store a preference value under the given key."""
        self.preferences[key] = value

    def get_preference(self, key: str):
        """Return the preference stored under the given key, if any."""
        return self.preferences.get(key)


class Plan:
    def __init__(self, day: date, available_time: int):
        """Create an empty plan for the given day and time budget."""
        self.date = day
        self.available_time = available_time
        self.tasks: list[Task] = []
        self.scheduled_tasks: list[Task] = []
        self.unscheduled_tasks: list[Task] = []

    def generate_plan(self, owner: Owner) -> None:
        """Build this plan by greedily scheduling owner's tasks into the time budget."""
        all_tasks = owner.get_all_tasks()
        relevant = [
            task for task in all_tasks if not task.is_done() and task.applies_on(self.date)
        ]
        relevant.sort(key=lambda t: (_PRIORITY_ORDER[t.priority], t.duration_minutes))

        self.tasks = relevant
        self.scheduled_tasks = []
        self.unscheduled_tasks = []

        remaining_time = self.available_time
        for task in relevant:
            if task.duration_minutes <= remaining_time:
                self.scheduled_tasks.append(task)
                remaining_time -= task.duration_minutes
            else:
                self.unscheduled_tasks.append(task)

    def display_plan(self) -> None:
        """Print this plan's scheduled and unscheduled tasks to the terminal."""
        print(f"Plan for {self.date} (available time: {self.available_time} min)")
        print("Scheduled:")
        for task in self.scheduled_tasks:
            print(f"  - {task.name} ({task.duration_minutes} min, {task.priority.name})")
        if self.unscheduled_tasks:
            print("Unscheduled (out of time):")
            for task in self.unscheduled_tasks:
                print(f"  - {task.name} ({task.duration_minutes} min, {task.priority.name})")

    def explain_plan(self) -> str:
        """Return a human-readable explanation of what was scheduled and why."""
        used = sum(t.duration_minutes for t in self.scheduled_tasks)
        lines = [
            f"Plan for {self.date}: {self.available_time} minutes available.",
            f"Scheduled {len(self.scheduled_tasks)} task(s), using {used} minute(s):",
        ]
        for task in self.scheduled_tasks:
            lines.append(f"  - {task.name}: {task.priority.name} priority, {task.duration_minutes} min")
        if self.unscheduled_tasks:
            lines.append(
                f"Could not fit {len(self.unscheduled_tasks)} task(s) into the remaining "
                f"{self.available_time - used} minute(s):"
            )
            for task in self.unscheduled_tasks:
                lines.append(f"  - {task.name}: {task.priority.name} priority, {task.duration_minutes} min")
        return "\n".join(lines)
