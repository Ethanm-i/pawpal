from datetime import date, time

import streamlit as st
from pawpal_system import Owner, Pet, Task, Plan, Priority, TaskStatus, ScheduleStrategy

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner")
owner_name = st.text_input("Owner name", value="Jordan")

# Build the Owner once per session; Streamlit reruns this script on every
# interaction, so without this guard a fresh Owner (losing its pets/tasks/
# preferences) would be created on every rerun instead of persisting.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(owner_id="owner-1", name=owner_name)

owner_obj = st.session_state.owner
owner_obj.name = owner_name

st.markdown("### Pets")
st.caption("Add one or more pets for this owner.")

if "pet_counter" not in st.session_state:
    st.session_state.pet_counter = 0

pcol1, pcol2, pcol3, pcol4 = st.columns(4)
with pcol1:
    pet_name = st.text_input("Pet name", value="Mochi")
with pcol2:
    species = st.selectbox("Species", ["dog", "cat", "other"])
with pcol3:
    age = st.number_input("Age", min_value=0, max_value=30, value=3)
with pcol4:
    size = st.selectbox("Size", ["small", "medium", "large"])

if st.button("Add pet"):
    st.session_state.pet_counter += 1
    new_pet = Pet(
        pet_id=f"pet-{st.session_state.pet_counter}",
        name=pet_name,
        species=species,
        age=int(age),
        size=size,
        owner_id=owner_obj.owner_id,
    )
    owner_obj.add_pet(new_pet)

if owner_obj.pets:
    st.write("Current pets:")
    st.table([p.get_info() for p in owner_obj.pets])
else:
    st.info("No pets yet. Add one above.")

pet_names_by_id = {p.pet_id: p.name for p in owner_obj.pets}

st.markdown("### Tasks")
st.caption("Add tasks to a pet. These feed into the scheduler below.")

if not owner_obj.pets:
    st.info("Add a pet above before adding tasks.")
else:
    if "task_counter" not in st.session_state:
        st.session_state.task_counter = 0

    pet_id_choice = st.selectbox(
        "Pet",
        options=[p.pet_id for p in owner_obj.pets],
        format_func=lambda pid: pet_names_by_id[pid],
    )
    pet_choice = next(p for p in owner_obj.pets if p.pet_id == pet_id_choice)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=2)
    with col4:
        recurrence_label = st.selectbox(
            "Repeats", ["once", "daily", "weekdays", "weekends", "weekly"]
        )

    recurrence_value = recurrence_label
    if recurrence_label == "weekly":
        weekday_choice = st.selectbox(
            "On which day",
            ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        )
        recurrence_value = f"weekly:{weekday_choice}"

    if st.button("Add task"):
        st.session_state.task_counter += 1
        new_task = Task(
            task_id=f"task-{st.session_state.task_counter}",
            name=task_title,
            pet_id=pet_choice.pet_id,
            duration_minutes=int(duration),
            priority=Priority[priority_label.upper()],
            recurrence=recurrence_value,
        )
        pet_choice.add_task(new_task)

    all_tasks = owner_obj.get_all_tasks()
    if all_tasks:
        st.write("Current tasks:")

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            pet_filter_ids = st.multiselect(
                "Filter by pet",
                options=[p.pet_id for p in owner_obj.pets],
                default=[p.pet_id for p in owner_obj.pets],
                format_func=lambda pid: pet_names_by_id[pid],
            )
        with filter_col2:
            status_filter_names = st.multiselect(
                "Filter by status",
                options=[s.name for s in TaskStatus],
                default=[s.name for s in TaskStatus],
            )

        visible_tasks = [
            t
            for t in all_tasks
            if t.pet_id in pet_filter_ids and t.status.name in status_filter_names
        ]
        if visible_tasks:
            st.table(
                [
                    {
                        "pet": pet_names_by_id[t.pet_id],
                        "task": t.name,
                        "duration_minutes": t.duration_minutes,
                        "priority": t.priority.name,
                        "status": t.status.name,
                        "repeats": t.recurrence or "once",
                    }
                    for t in visible_tasks
                ]
            )
        else:
            st.info("No tasks match the selected filters.")
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Builds today's schedule from the owner's pets and tasks.")

schedule_pet_ids = st.multiselect(
    "Include pets",
    options=[p.pet_id for p in owner_obj.pets],
    default=[p.pet_id for p in owner_obj.pets],
    format_func=lambda pid: pet_names_by_id[pid],
)

strategy_labels = {
    "Maximize priority / urgency": ScheduleStrategy.PRIORITY,
    "Maximize number of tasks": ScheduleStrategy.TASK_COUNT,
    "Fair share across pets": ScheduleStrategy.FAIR_SHARE,
}
strategy_choice = st.selectbox("Scheduling strategy", list(strategy_labels.keys()))

day_start_choice = st.time_input("Day starts at", value=time(8, 0))
available_minutes = st.number_input(
    "Available time today (minutes)", min_value=0, max_value=1440, value=60
)

if st.button("Generate schedule"):
    if not owner_obj.get_all_tasks():
        st.warning("Add at least one task before generating a schedule.")
    elif not schedule_pet_ids:
        st.warning("Select at least one pet to include in the schedule.")
    else:
        plan_obj = Plan(day=date.today(), available_time=int(available_minutes))
        plan_obj.generate_plan(
            owner_obj,
            pet_ids=schedule_pet_ids,
            strategy=strategy_labels[strategy_choice],
            day_start=day_start_choice,
        )

        st.success("Schedule generated.")
        st.text(plan_obj.explain_plan())
