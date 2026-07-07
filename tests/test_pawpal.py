import sys
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pawpal_system import (
    Owner,
    Pet,
    Plan,
    Priority,
    ScheduledSlot,
    ScheduleStrategy,
    Task,
    TaskStatus,
    find_schedule_conflicts,
)


def test_complete_marks_done():
    task = Task("t1", "Walk", "p1", 20, Priority.HIGH)

    assert task.status == TaskStatus.NOT_STARTED
    assert not task.is_done()

    task.complete()

    assert task.status == TaskStatus.DONE
    assert task.is_done()


def test_start_marks_in_progress():
    task = Task("t1", "Walk", "p1", 20, Priority.HIGH)
    task.start()
    assert task.status == TaskStatus.IN_PROGRESS
    assert not task.is_done()


def test_add_task_appends_to_pet():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    assert len(pet.tasks) == 0

    pet.add_task(Task("t1", "Walk", "p1", 20, Priority.HIGH))
    assert len(pet.tasks) == 1

    pet.add_task(Task("t2", "Brush", "p1", 10, Priority.MEDIUM))
    assert len(pet.tasks) == 2


# --- Pet.get_info -----------------------------------------------------------------


def test_get_info_returns_pet_fields():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="o1")
    assert pet.get_info() == {
        "pet_id": "p1",
        "name": "Mochi",
        "species": "dog",
        "age": 3,
        "size": "medium",
        "owner_id": "o1",
    }


# --- Pet.add_task / remove_task -------------------------------------------------


def test_add_task_dedupes_by_id():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    pet.add_task(Task("t1", "Walk", "p1", 20, Priority.HIGH))
    pet.add_task(Task("t1", "Duplicate walk", "p1", 5, Priority.LOW))

    assert len(pet.tasks) == 1
    assert pet.tasks[0].name == "Walk"


def test_add_task_relinks_pet_id():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    task = Task("t1", "Walk", pet_id="wrong-pet", duration_minutes=20, priority=Priority.HIGH)

    pet.add_task(task)

    assert task.pet_id == "p1"


def test_remove_task_deletes_by_id():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    pet.add_task(Task("t1", "Walk", "p1", 20, Priority.HIGH))
    pet.add_task(Task("t2", "Brush", "p1", 10, Priority.MEDIUM))

    pet.remove_task("t1")

    assert [t.task_id for t in pet.tasks] == ["t2"]


def test_remove_task_missing_id_is_noop():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    pet.add_task(Task("t1", "Walk", "p1", 20, Priority.HIGH))

    pet.remove_task("does-not-exist")

    assert len(pet.tasks) == 1


# --- Pet.complete_task (completion + recurrence rollover) ----------------------


def test_complete_task_one_off_has_no_follow_up():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    task = Task("t1", "Vet visit", "p1", 30, Priority.HIGH)
    pet.add_task(task)

    result = pet.complete_task("t1")

    assert result is None
    assert task.is_done()
    assert len(pet.tasks) == 1


def test_complete_task_recurring_adds_follow_up():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    task = Task(
        "t1", "Feed", "p1", 10, Priority.MEDIUM,
        recurrence="daily", due_date=date(2024, 1, 5),
    )
    pet.add_task(task)

    follow_up = pet.complete_task("t1")

    assert follow_up is not None
    assert follow_up.due_date == date(2024, 1, 6)
    assert not follow_up.is_done()
    assert {t.task_id for t in pet.tasks} == {"t1", follow_up.task_id}


def test_complete_task_missing_id_returns_none():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    assert pet.complete_task("does-not-exist") is None


# --- Task.next_occurrence (recurrence date math) --------------------------------


def test_next_occurrence_none_for_once():
    assert Task("t1", "X", "p1", 5, Priority.LOW).next_occurrence() is None
    assert Task("t1", "X", "p1", 5, Priority.LOW, recurrence="once").next_occurrence() is None


def test_next_occurrence_daily():
    task = Task("t1", "Feed", "p1", 10, Priority.MEDIUM, recurrence="daily", due_date=date(2024, 1, 5))
    nxt = task.next_occurrence()
    assert nxt.due_date == date(2024, 1, 6)


def test_next_occurrence_weekdays_skips_weekend():
    # 2024-01-05 is a Friday; the next weekday occurrence must land on Monday, not Saturday.
    task = Task("t1", "Walk", "p1", 20, Priority.HIGH, recurrence="weekdays", due_date=date(2024, 1, 5))
    nxt = task.next_occurrence()
    assert nxt.due_date == date(2024, 1, 8)


def test_next_occurrence_weekends_skips_weekday():
    # 2024-01-07 is a Sunday; the next weekend occurrence must land on Saturday, not Monday.
    task = Task("t1", "Play", "p1", 15, Priority.LOW, recurrence="weekends", due_date=date(2024, 1, 7))
    nxt = task.next_occurrence()
    assert nxt.due_date == date(2024, 1, 13)


def test_next_occurrence_weekly():
    task = Task(
        "t1", "Groom", "p1", 30, Priority.MEDIUM,
        recurrence="weekly:monday", due_date=date(2024, 1, 8),  # a Monday
    )
    nxt = task.next_occurrence()
    assert nxt.due_date == date(2024, 1, 15)


def test_next_occurrence_has_unique_id():
    task = Task("t1", "Feed", "p1", 10, Priority.MEDIUM, recurrence="daily", due_date=date(2024, 1, 5))
    nxt = task.next_occurrence()
    assert nxt.task_id == "t1@2024-01-06"
    assert nxt.task_id != task.task_id


# --- Task.applies_on (recurrence filtering for a given day) --------------------


def test_applies_on_daily_always_true():
    task = Task("t1", "Feed", "p1", 10, Priority.MEDIUM, recurrence="daily")
    assert task.applies_on(date(2024, 1, 5))
    assert task.applies_on(date(2024, 1, 6))


def test_applies_on_weekdays():
    task = Task("t1", "Walk", "p1", 20, Priority.HIGH, recurrence="weekdays")
    assert task.applies_on(date(2024, 1, 5))  # Friday
    assert not task.applies_on(date(2024, 1, 6))  # Saturday


def test_applies_on_weekends():
    task = Task("t1", "Play", "p1", 15, Priority.LOW, recurrence="weekends")
    assert task.applies_on(date(2024, 1, 6))  # Saturday
    assert not task.applies_on(date(2024, 1, 5))  # Friday


def test_applies_on_weekly():
    task = Task("t1", "Groom", "p1", 30, Priority.MEDIUM, recurrence="weekly:friday")
    assert task.applies_on(date(2024, 1, 5))  # Friday
    assert not task.applies_on(date(2024, 1, 6))  # Saturday


def test_applies_on_once_ignores_due_date():
    # Surprising edge case: a "once" task applies on ANY day, even one far past its
    # own due_date -- applies_on never checks due_date for the "once" rule. Worth
    # deciding on purpose whether a past-due one-off task should still show up.
    task = Task("t1", "Vet visit", "p1", 30, Priority.HIGH, due_date=date(2024, 1, 1))
    assert task.applies_on(date(2099, 1, 1))


# --- Task.urgency_score ----------------------------------------------------------


def test_urgency_score_by_priority():
    high = Task("t1", "X", "p1", 10, Priority.HIGH)
    medium = Task("t2", "X", "p1", 10, Priority.MEDIUM)
    low = Task("t3", "X", "p1", 10, Priority.LOW)
    assert high.urgency_score() > medium.urgency_score() > low.urgency_score()


def test_urgency_score_daily_bump():
    daily = Task("t1", "X", "p1", 10, Priority.MEDIUM, recurrence="daily")
    weekly = Task("t2", "X", "p1", 10, Priority.MEDIUM, recurrence="weekly:monday")
    assert daily.urgency_score() - weekly.urgency_score() == 2


def test_urgency_score_skip_bump():
    fresh = Task("t1", "X", "p1", 10, Priority.LOW, times_skipped=0)
    skipped_twice = Task("t2", "X", "p1", 10, Priority.LOW, times_skipped=2)
    assert skipped_twice.urgency_score() - fresh.urgency_score() == 6


# --- Plan.generate_plan / knapsack selection ------------------------------------


def _owner_with_pet(pet_id="p1"):
    owner = Owner("o1", "Jordan")
    pet = Pet(pet_id, "Mochi", "dog", 3, "medium", owner_id="")
    owner.add_pet(pet)
    return owner, pet


def test_generate_plan_no_tasks_is_empty():
    owner, _ = _owner_with_pet()
    plan = Plan(date(2024, 1, 5), available_time=60)
    plan.generate_plan(owner)

    assert plan.schedule == []
    assert plan.scheduled_tasks == []
    assert plan.unscheduled_tasks == []


def test_generate_plan_zero_budget_schedules_nothing():
    owner, pet = _owner_with_pet()
    pet.add_task(Task("t1", "Walk", pet.pet_id, 10, Priority.HIGH))
    plan = Plan(date(2024, 1, 5), available_time=0)
    plan.generate_plan(owner)

    assert plan.scheduled_tasks == []
    assert plan.unscheduled_reasons["t1"] == "too long to fit in today's available time at all"


def test_generate_plan_oversized_task_is_unschedulable():
    owner, pet = _owner_with_pet()
    pet.add_task(Task("t1", "Grooming", pet.pet_id, 45, Priority.HIGH))
    plan = Plan(date(2024, 1, 5), available_time=20)
    plan.generate_plan(owner)

    assert plan.scheduled_tasks == []
    assert plan.unscheduled_reasons["t1"] == "too long to fit in today's available time at all"


def test_generate_plan_knapsack_prefers_higher_value():
    # Classic knapsack counter-example: one HIGH task fills the whole budget (value 30),
    # but two MEDIUM tasks fill it just as exactly for more combined value (20+20=40).
    # A naive "sort by priority, take greedily" scheduler would get this wrong.
    owner, pet = _owner_with_pet()
    big_high = Task("big", "Big high-priority task", pet.pet_id, 10, Priority.HIGH)
    small_a = Task("a", "Small medium task A", pet.pet_id, 5, Priority.MEDIUM)
    small_b = Task("b", "Small medium task B", pet.pet_id, 5, Priority.MEDIUM)
    pet.add_task(big_high)
    pet.add_task(small_a)
    pet.add_task(small_b)

    plan = Plan(date(2024, 1, 5), available_time=10)
    plan.generate_plan(owner)

    assert {t.task_id for t in plan.scheduled_tasks} == {"a", "b"}
    assert plan.unscheduled_reasons["big"] == "bumped by higher-urgency tasks"


def test_generate_plan_task_count_strategy_maximizes_count():
    owner, pet = _owner_with_pet()
    big_high = Task("big", "One big task", pet.pet_id, 10, Priority.HIGH)
    for i in range(5):
        pet.add_task(Task(f"small{i}", f"Small task {i}", pet.pet_id, 2, Priority.LOW))
    pet.add_task(big_high)

    plan = Plan(date(2024, 1, 5), available_time=10)
    plan.generate_plan(owner, strategy=ScheduleStrategy.TASK_COUNT)

    assert len(plan.scheduled_tasks) == 5
    assert "big" not in {t.task_id for t in plan.scheduled_tasks}


def test_generate_plan_pet_ids_filter():
    owner, pet1 = _owner_with_pet("p1")
    pet2 = Pet("p2", "Luna", "cat", 5, "small", owner_id="")
    owner.add_pet(pet2)
    pet1.add_task(Task("t1", "Walk", "p1", 10, Priority.HIGH))
    pet2.add_task(Task("t2", "Litter box", "p2", 10, Priority.HIGH))

    plan = Plan(date(2024, 1, 5), available_time=60)
    plan.generate_plan(owner, pet_ids=["p1"])

    assert [t.task_id for t in plan.tasks] == ["t1"]


def test_generate_plan_status_filter():
    owner, pet = _owner_with_pet()
    not_started = Task("t1", "Walk", pet.pet_id, 10, Priority.HIGH)
    in_progress = Task("t2", "Feed", pet.pet_id, 10, Priority.HIGH)
    in_progress.start()
    pet.add_task(not_started)
    pet.add_task(in_progress)

    plan = Plan(date(2024, 1, 5), available_time=60)
    plan.generate_plan(owner, status_filter={TaskStatus.NOT_STARTED})

    assert [t.task_id for t in plan.tasks] == ["t1"]


def test_generate_plan_excludes_done_tasks():
    owner, pet = _owner_with_pet()
    done = Task("t1", "Walk", pet.pet_id, 10, Priority.HIGH)
    done.complete()
    pet.add_task(done)

    plan = Plan(date(2024, 1, 5), available_time=60)
    plan.generate_plan(owner)

    assert plan.tasks == []


def test_generate_plan_excludes_inapplicable_recurrence():
    owner, pet = _owner_with_pet()
    pet.add_task(Task("t1", "Groom", pet.pet_id, 10, Priority.HIGH, recurrence="weekly:monday"))

    plan = Plan(date(2024, 1, 5), available_time=60)  # a Friday
    plan.generate_plan(owner)

    assert plan.tasks == []


def test_generate_plan_updates_skip_counts():
    owner, pet = _owner_with_pet()
    scheduled_task = Task("keep", "Fits", pet.pet_id, 5, Priority.HIGH, times_skipped=1)
    skipped_task = Task("skip", "Too big", pet.pet_id, 100, Priority.HIGH)
    pet.add_task(scheduled_task)
    pet.add_task(skipped_task)

    plan = Plan(date(2024, 1, 5), available_time=10)
    plan.generate_plan(owner)

    assert scheduled_task.times_skipped == 0
    assert skipped_task.times_skipped == 1


def test_generate_plan_is_chronological():
    # Tasks are added LOW -> MEDIUM -> HIGH (reverse of urgency order) so this can't
    # pass by accident from insertion order matching time order. generate_plan sorts
    # scheduled_tasks by urgency *before* stamping times, so the most urgent task
    # should land at day_start and each slot afterward should start later than the last.
    owner, pet = _owner_with_pet()
    low = Task("low", "Play", pet.pet_id, 10, Priority.LOW)
    medium = Task("medium", "Brush", pet.pet_id, 10, Priority.MEDIUM)
    high = Task("high", "Walk", pet.pet_id, 10, Priority.HIGH)
    pet.add_task(low)
    pet.add_task(medium)
    pet.add_task(high)

    plan = Plan(date(2024, 1, 5), available_time=30)
    plan.generate_plan(owner, day_start=time(8, 0))

    assert [slot.task.task_id for slot in plan.schedule] == ["high", "medium", "low"]
    start_times = [slot.start for slot in plan.schedule]
    assert start_times == sorted(start_times)
    assert plan.schedule[0].start == time(8, 0)
    assert plan.schedule[1].start == time(8, 10)
    assert plan.schedule[2].start == time(8, 20)


def test_generate_plan_cache_still_reescalates_skips():
    # This documents a real gotcha rather than a desired guarantee: _cache_key is
    # computed from each task's times_skipped BEFORE this call mutates it, so a
    # second call with literally nothing changed still counts as a cache miss and
    # bumps times_skipped again. In the Streamlit app, clicking "Generate schedule"
    # repeatedly with no new tasks will keep inflating unscheduled tasks' urgency.
    owner, pet = _owner_with_pet()
    task = Task("t1", "Too big to ever fit", pet.pet_id, 100, Priority.HIGH)
    pet.add_task(task)

    plan = Plan(date(2024, 1, 5), available_time=10)
    plan.generate_plan(owner)
    assert task.times_skipped == 1

    plan.generate_plan(owner)
    assert task.times_skipped == 2


# --- Plan._fair_share_select (round robin across pets) --------------------------


def test_fair_share_round_robins_pets():
    owner = Owner("o1", "Jordan")
    pet1 = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    pet2 = Pet("p2", "Luna", "cat", 5, "small", owner_id="")
    owner.add_pet(pet1)
    owner.add_pet(pet2)

    a1 = Task("a1", "Pet1 task A", "p1", 5, Priority.MEDIUM)
    a2 = Task("a2", "Pet1 task B", "p1", 5, Priority.MEDIUM)
    b1 = Task("b1", "Pet2 task A", "p2", 5, Priority.MEDIUM)
    b2 = Task("b2", "Pet2 task B", "p2", 5, Priority.MEDIUM)
    pet1.add_task(a1)
    pet1.add_task(a2)
    pet2.add_task(b1)
    pet2.add_task(b2)

    plan = Plan(date(2024, 1, 5), available_time=20)
    scheduled, skipped = plan._fair_share_select([pet1, pet2], [a1, a2, b1, b2])

    assert [t.task_id for t in scheduled] == ["a1", "b1", "a2", "b2"]
    assert skipped == []


def test_fair_share_drops_oversized_task():
    _, pet = _owner_with_pet()
    big = Task("big", "Too big for the remaining budget", pet.pet_id, 20, Priority.HIGH)
    small = Task("small", "Fits fine", pet.pet_id, 5, Priority.LOW)
    pet.add_task(big)
    pet.add_task(small)

    plan = Plan(date(2024, 1, 5), available_time=10)
    scheduled, skipped = plan._fair_share_select([pet], [big, small])

    assert [t.task_id for t in scheduled] == ["small"]
    assert [t.task_id for t in skipped] == ["big"]


# --- Plan.detect_conflicts / find_schedule_conflicts ----------------------------


def test_plan_never_conflicts_with_itself():
    owner, pet = _owner_with_pet()
    pet.add_task(Task("t1", "Walk", pet.pet_id, 20, Priority.HIGH))
    pet.add_task(Task("t2", "Feed", pet.pet_id, 10, Priority.MEDIUM))

    plan = Plan(date(2024, 1, 5), available_time=60)
    plan.generate_plan(owner)

    assert plan.detect_conflicts() == []


def test_two_plans_same_start_time_conflict():
    owner = Owner("o1", "Jordan")
    dog = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    cat = Pet("p2", "Luna", "cat", 5, "small", owner_id="")
    owner.add_pet(dog)
    owner.add_pet(cat)
    dog.add_task(Task("t1", "Walk", "p1", 20, Priority.HIGH))
    cat.add_task(Task("t2", "Litter box", "p2", 15, Priority.HIGH))

    dog_plan = Plan(date(2024, 1, 5), available_time=60)
    dog_plan.generate_plan(owner, pet_ids=["p1"], day_start=time(8, 0))
    cat_plan = Plan(date(2024, 1, 5), available_time=60)
    cat_plan.generate_plan(owner, pet_ids=["p2"], day_start=time(8, 0))

    warnings = dog_plan.detect_conflicts(cat_plan)
    assert len(warnings) == 1
    assert "Walk" in warnings[0] and "Litter box" in warnings[0]


def test_adjacent_slots_dont_conflict():
    task_a = Task("t1", "First", "p1", 30, Priority.HIGH)
    task_b = Task("t2", "Second", "p1", 30, Priority.HIGH)
    slot_a = ScheduledSlot(task=task_a, start=time(8, 0), end=time(8, 30))
    slot_b = ScheduledSlot(task=task_b, start=time(8, 30), end=time(9, 0))

    assert find_schedule_conflicts([slot_a], [slot_b]) == []


def test_duplicate_time_slots_conflict():
    task_a = Task("t1", "Walk", "p1", 20, Priority.HIGH)
    task_b = Task("t2", "Vet call", "p2", 20, Priority.HIGH)
    slot_a = ScheduledSlot(task=task_a, start=time(8, 0), end=time(8, 20))
    slot_b = ScheduledSlot(task=task_b, start=time(8, 0), end=time(8, 20))

    warnings = find_schedule_conflicts([slot_a], [slot_b])

    assert len(warnings) == 1
    assert "Walk" in warnings[0] and "Vet call" in warnings[0]


# --- Plan.sort_by_time -----------------------------------------------------------


def test_sort_by_time_reorders_schedule():
    plan = Plan(date(2024, 1, 5), available_time=60)
    late = ScheduledSlot(task=Task("t1", "Late", "p1", 10, Priority.LOW), start=time(18, 0), end=time(18, 10))
    early = ScheduledSlot(task=Task("t2", "Early", "p1", 10, Priority.LOW), start=time(7, 0), end=time(7, 10))
    plan.schedule = [late, early]

    plan.sort_by_time()

    assert [slot.task.task_id for slot in plan.schedule] == ["t2", "t1"]


def test_sort_by_time_accepts_string_times():
    plan = Plan(date(2024, 1, 5), available_time=60)
    late = ScheduledSlot(task=Task("t1", "Late", "p1", 10, Priority.LOW), start="18:00", end="18:10")
    early = ScheduledSlot(task=Task("t2", "Early", "p1", 10, Priority.LOW), start="07:00", end="07:10")
    plan.schedule = [late, early]

    plan.sort_by_time()

    assert [slot.task.task_id for slot in plan.schedule] == ["t2", "t1"]


# --- Owner.add_pet / remove_pet -----------------------------------------------


def test_add_pet_dedupes_by_id():
    owner = Owner("o1", "Jordan")
    owner.add_pet(Pet("p1", "Mochi", "dog", 3, "medium", owner_id=""))
    owner.add_pet(Pet("p1", "Duplicate", "cat", 1, "small", owner_id=""))

    assert len(owner.pets) == 1
    assert owner.pets[0].name == "Mochi"


def test_add_pet_relinks_owner_id():
    owner = Owner("o1", "Jordan")
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="wrong-owner")

    owner.add_pet(pet)

    assert pet.owner_id == "o1"


def test_remove_pet_deletes_by_id():
    owner = Owner("o1", "Jordan")
    owner.add_pet(Pet("p1", "Mochi", "dog", 3, "medium", owner_id=""))
    owner.add_pet(Pet("p2", "Luna", "cat", 5, "small", owner_id=""))

    owner.remove_pet("p1")

    assert [p.pet_id for p in owner.pets] == ["p2"]


def test_remove_pet_missing_id_is_noop():
    owner = Owner("o1", "Jordan")
    owner.add_pet(Pet("p1", "Mochi", "dog", 3, "medium", owner_id=""))

    owner.remove_pet("does-not-exist")

    assert len(owner.pets) == 1


# --- Owner.set_available_time / get_available_time -----------------------------


def test_get_available_time_defaults_to_zero():
    owner = Owner("o1", "Jordan")
    assert owner.get_available_time(date(2024, 1, 5)) == 0


def test_set_available_time_is_per_day():
    owner = Owner("o1", "Jordan")
    owner.set_available_time(date(2024, 1, 5), 30)

    assert owner.get_available_time(date(2024, 1, 5)) == 30
    assert owner.get_available_time(date(2024, 1, 6)) == 0


# --- Owner.set_preference / get_preference --------------------------------------


def test_get_preference_defaults_to_none():
    owner = Owner("o1", "Jordan")
    assert owner.get_preference("quiet_hours") is None


def test_set_preference_roundtrips():
    owner = Owner("o1", "Jordan")
    owner.set_preference("quiet_hours", (22, 6))

    assert owner.get_preference("quiet_hours") == (22, 6)


# --- Owner.completion -------------------------------------------------------------


def test_completion_filters_by_status():
    owner, pet = _owner_with_pet()
    done = Task("t1", "Walk", pet.pet_id, 10, Priority.HIGH)
    done.complete()
    pending = Task("t2", "Feed", pet.pet_id, 10, Priority.HIGH)
    pet.add_task(done)
    pet.add_task(pending)

    result = owner.completion(status=TaskStatus.DONE)

    assert [t.task_id for t in result] == ["t1"]


def test_completion_filters_by_name():
    owner, pet = _owner_with_pet()
    pet.add_task(Task("t1", "Morning Walk", pet.pet_id, 10, Priority.HIGH))
    pet.add_task(Task("t2", "Feed", pet.pet_id, 10, Priority.HIGH))

    result = owner.completion(name="WALK")

    assert [t.task_id for t in result] == ["t1"]


def test_completion_combines_filters():
    owner, pet = _owner_with_pet()
    done_walk = Task("t1", "Morning Walk", pet.pet_id, 10, Priority.HIGH)
    done_walk.complete()
    pending_walk = Task("t2", "Evening Walk", pet.pet_id, 10, Priority.HIGH)
    pet.add_task(done_walk)
    pet.add_task(pending_walk)

    result = owner.completion(status=TaskStatus.DONE, name="walk")

    assert [t.task_id for t in result] == ["t1"]


def test_completion_no_filters_returns_all():
    owner, pet = _owner_with_pet()
    pet.add_task(Task("t1", "Walk", pet.pet_id, 10, Priority.HIGH))
    pet.add_task(Task("t2", "Feed", pet.pet_id, 10, Priority.HIGH))

    result = owner.completion()

    assert {t.task_id for t in result} == {"t1", "t2"}


# --- Plan.explain_plan / display_plan -------------------------------------------


def _plan_with_fit_and_overflow():
    owner, pet = _owner_with_pet()
    pet.add_task(Task("fits", "Morning walk", pet.pet_id, 10, Priority.HIGH))
    pet.add_task(Task("overflow", "Grooming", pet.pet_id, 50, Priority.LOW))

    plan = Plan(date(2024, 1, 5), available_time=20)
    plan.generate_plan(owner)
    return plan


def test_explain_plan_shows_scheduled_task():
    plan = _plan_with_fit_and_overflow()

    explanation = plan.explain_plan()

    assert "Scheduled 1 task(s), using 10 minute(s):" in explanation
    assert "08:00-08:10 Morning walk: HIGH priority, 10 min" in explanation


def test_explain_plan_shows_unscheduled_reason():
    plan = _plan_with_fit_and_overflow()

    explanation = plan.explain_plan()

    assert "Could not fit 1 task(s)" in explanation
    assert "Grooming: LOW priority, 50 min (too long to fit in today's available time at all)" in explanation


def test_explain_plan_omits_unscheduled_section_when_empty():
    owner, _ = _owner_with_pet()
    plan = Plan(date(2024, 1, 5), available_time=60)
    plan.generate_plan(owner)

    explanation = plan.explain_plan()

    assert "Scheduled 0 task(s), using 0 minute(s):" in explanation
    assert "Could not fit" not in explanation


def test_display_plan_prints_both_sections(capsys):
    plan = _plan_with_fit_and_overflow()

    plan.display_plan()

    output = capsys.readouterr().out
    assert "Scheduled:" in output
    assert "08:00-08:10 Morning walk (10 min, HIGH)" in output
    assert "Unscheduled (out of time):" in output
    assert "Grooming (50 min, LOW) - too long to fit in today's available time at all" in output
