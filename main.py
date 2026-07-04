"""Demo script for PawPal+: builds a sample owner/pets/tasks and prints today's schedule."""

from datetime import date

from pawpal_system import Owner, Pet, Plan, Priority, Task

owner = Owner(owner_id="o1", name="Jordan")

dog = Pet(pet_id="p1", name="Mochi", species="dog", age=3, size="medium", owner_id="")
cat = Pet(pet_id="p2", name="Luna", species="cat", age=5, size="small", owner_id="")
owner.add_pet(dog)
owner.add_pet(cat)

dog.add_task(Task("t1", "Morning walk", dog.pet_id, 20, Priority.HIGH))
dog.add_task(Task("t2", "Brush coat", dog.pet_id, 10, Priority.MEDIUM))
cat.add_task(Task("t3", "Clean litter box", cat.pet_id, 5, Priority.HIGH))
cat.add_task(Task("t4", "Play session", cat.pet_id, 15, Priority.LOW))

today = date.today()
owner.set_available_time(today, 30)

plan = Plan(today, owner.get_available_time(today))
plan.generate_plan(owner)

print("Today's Schedule")
print("=" * 40)
plan.display_plan()
