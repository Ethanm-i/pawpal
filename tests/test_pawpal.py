import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pawpal_system import Pet, Priority, Task, TaskStatus


def test_complete_changes_task_status():
    task = Task("t1", "Walk", "p1", 20, Priority.HIGH)

    assert task.status == TaskStatus.NOT_STARTED
    assert not task.is_done()

    task.complete()

    assert task.status == TaskStatus.DONE
    assert task.is_done()


def test_add_task_increases_pets_task_count():
    pet = Pet("p1", "Mochi", "dog", 3, "medium", owner_id="")
    assert len(pet.tasks) == 0

    pet.add_task(Task("t1", "Walk", "p1", 20, Priority.HIGH))
    assert len(pet.tasks) == 1

    pet.add_task(Task("t2", "Brush", "p1", 10, Priority.MEDIUM))
    assert len(pet.tasks) == 2
