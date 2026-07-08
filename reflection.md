# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.

    my inital design was to haver owner, pet, task and make plan as the classes 
    - owner with attributes like: name, owner id, avilable time and methods: set time avilable
    priorites, add pet, remove pet
    - pet with attributes like: pet name, pet id, size, kind and age and methodes: get information
    - tasks with attributes like: time and methods: add_task , remove task, completed, inprogress, and incomplete

- What classes did you include, and what responsibilities did you assign to each?

    Owner - getting the owner information, time avilable, adding and removing a pet
    pet - has the pet information
    task - owner can add and remove taskes, mark them complete, and in progress
    make_plan - takes all the information and makes a plan/schedule

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

    yes it changed turns out that i was missing some attributes in the owner class but it was being used or expected to be used in the pet class. I ended up adding this adding this to the owner added the owner_id, a method for recurrences added a plan.generer_plan methode to check for tasks and owners information to make a plan. and remover the plan pet paremeter and used ownerpets since one owner can have more than one pet.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

    My scheduling considers priority, time, turns

- How did you decide which constraints mattered most?

    Time was the hard constraint (a task either fits in the remaining minutes or it doesn't), so
    that had to be the thing the scheduler optimizes around. Priority mattered next because it's
    the signal the owner directly controls. if ignored it, HIGH-priority tasks could get
    starved out by a pile of LOW-priority ones that happen to fit better. "Turns" (fair share
    across pets) came last because it only matters once there's more than one pet competing for
    the same time budget; with a single pet it never triggers.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
    one of the trade off in the scheduler method in the  fair share method makes sure that all  pets are taken care of and fairly it makes sure that the high pority task for both pets are done firts.

- Why is that tradeoff reasonable for this scenario?

    This helps make sure that if the owner has more than one pet, all pets are taken care over spliting the avilable time and make sure that all the pets high prouity tasks are cared for. 

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

    I used AI mostly after the core classes already existed. To write a full pytest for the added methods/fuctions, to wire several backend methods I'd written but never
    actually called from `app.py`, and to bring `diagrams/uml.mmd` back in sync
    with what the code had grown into. 

    Detail and specific instructions where more helpful and faster to understand what AI was doin and made it easy to find bugs if there is any

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

    When I asked for a "Demo Walkthrough" section in the README, the first draft it produced was
    generic, steps with no real detail. I rejected it and asked specifically for
    the actual UI actions, a concrete add-pet/add-task/generate-schedule workflow, the scheduler
    behaviors worth calling out, and real CLI output. The rewrite was much more useful because it
    was tied to what the app actually does rather than a template. More generally, I verified
    AI-written tests by reading the assertions against the real method bodies myself and by actually running `pytest` and the Streamlit app to confirm behavior, rather than accepting a description of what the code
    "should" do.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

    I tested the task lifecycle (start/complete), recurrence date math across weekday/weekend
    boundaries and week-long rules, urgency scoring, the knapsack picking a better combined value over one big task, fair-share round-robining across pets instead of draining one first, and conflict detection at the exact boundary between "touching" and "overlapping" time slots. These mattered because they're exactly the
    places where an off-by-one or a wrong comparison operator would silently produce a plausible-
    looking but wrong schedule.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

    I'm fairly confident in the core scheduling logic now that it has 61 passing tests, including the exact overlap-boundary case. 

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

    I'm most satisfied with choosing an actual 0/1 knapsack over a greedy priority sort for
    scheduling. It was more work to implement, but it produces genuinely better schedules.
    two medium-priority tasks can beat one big high-priority task if they fit the time budget
    better

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

    I'd redesign the UI to make it look more proffessional and easy to use.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
    
    AI collaboration dramatically more useful. Where the reasoning was already written
    down and with specific things to fix or do instead of letting the AI to come up with general solutions. This make it fast and easier to understand and improve on what you a started with or already have

