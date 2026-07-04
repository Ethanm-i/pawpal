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
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
