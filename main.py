"""Demo script for PawPal+: builds a sample owner/pets/tasks and prints today's schedule."""

from datetime import date, time

from pawpal_system import Owner, Pet, Plan, Priority, Task, TaskStatus

owner = Owner(owner_id="o1", name="Jordan")

dog = Pet(pet_id="p1", name="Mochi", species="dog", age=3, size="medium", owner_id="")
cat = Pet(pet_id="p2", name="Luna", species="cat", age=5, size="small", owner_id="")
owner.add_pet(dog)
owner.add_pet(cat)

# Tasks are added out of order on purpose (mixed pets/priorities/durations) to
# show that generate_plan schedules by urgency, not by insertion order.
cat.add_task(Task("t4", "Play session", cat.pet_id, 15, Priority.LOW))
dog.add_task(Task("t2", "Brush coat", dog.pet_id, 10, Priority.MEDIUM))
cat.add_task(Task("t3", "Clean litter box", cat.pet_id, 5, Priority.HIGH))
evening_walk = Task("t5", "Evening walk", dog.pet_id, 15, Priority.MEDIUM)
dog.add_task(evening_walk)
dog.add_task(Task("t1", "Morning walk", dog.pet_id, 20, Priority.HIGH))

evening_walk.complete()  # already done today; exercises completion() filtering below

today = date.today()
owner.set_available_time(today, 30)

plan = Plan(today, owner.get_available_time(today))
plan.generate_plan(owner)

# The schedule comes back time-ordered already; reverse it here just for this
# demo so sort_by_time() has visible work to do.
plan.schedule.reverse()
print("Schedule before sort_by_time():")
for slot in plan.schedule:
    print(f"  - {slot.start.strftime('%H:%M')} {slot.task.name}")

plan.sort_by_time()
print()
print("Today's Schedule (sort_by_time applied)")
print("=" * 40)
plan.display_plan()

print()
print("owner.completion(status=TaskStatus.DONE):")
for task in owner.completion(status=TaskStatus.DONE):
    print(f"  - {task.name}")

print()
print("owner.completion(name='walk'):")
for task in owner.completion(name="walk"):
    print(f"  - {task.name} ({task.status.name})")

print()
print("=" * 40)
print("Conflict detection demo")
print("=" * 40)

# The combined plan above places every task back-to-back, so it can never
# conflict with itself no matter how it was generated.
print("plan.detect_conflicts():", plan.detect_conflicts())

# Building a separate plan per pet, both starting at the same time of day, is a
# realistic way two tasks end up scheduled at once: each plan is internally
# conflict-free, but together they can double-book the owner.
dog_plan = Plan(today, owner.get_available_time(today))
dog_plan.generate_plan(owner, pet_ids=[dog.pet_id], day_start=time(8, 0))

cat_plan = Plan(today, owner.get_available_time(today))
cat_plan.generate_plan(owner, pet_ids=[cat.pet_id], day_start=time(8, 0))

print()
print("Dog-only plan (starts 08:00):")
for slot in dog_plan.schedule:
    print(f"  - {slot.start.strftime('%H:%M')}-{slot.end.strftime('%H:%M')} {slot.task.name}")

print("Cat-only plan (also starts 08:00):")
for slot in cat_plan.schedule:
    print(f"  - {slot.start.strftime('%H:%M')}-{slot.end.strftime('%H:%M')} {slot.task.name}")

warnings = dog_plan.detect_conflicts(cat_plan)
print()
if warnings:
    print(f"Found {len(warnings)} conflict(s) -- program keeps running, just warns:")
    for warning in warnings:
        print(f"  ! {warning}")
else:
    print("No conflicts found.")
