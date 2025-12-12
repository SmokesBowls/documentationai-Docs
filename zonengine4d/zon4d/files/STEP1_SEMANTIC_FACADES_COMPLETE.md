# STEP 1 COMPLETE: Semantic Facades Added to task_system.py

## What We Built

**One Implementation (TaskTree), Six Semantic Facades:**

1. **Quest** - Player missions and objectives
2. **Behavior** - NPC AI routines and actions
3. **Sequence** - Cutscenes and scripted events
4. **Conversation** - Dialogue trees with branching
5. **Maintenance** - Engine cleanup (pocket tasks)
6. **Routine** - Recurring timed tasks

**All share the same underlying TaskTree implementation.**

---

## The Architecture

### Base Implementation (TaskTree)
```python
class TaskTree:
    steps: List[TaskTree]          # Child tasks
    current_step: int              # Current position
    completed_steps: Set[int]      # Finished steps
    state: TaskState               # PENDING/RUNNING/COMPLETED
    
    completion_condition: Callable # Custom completion logic
    on_complete: Callable          # Callback on success
    
    def add_step(step)             # Add child task
    def advance_step() -> TaskTree # Move to next step
    def mark_step_complete(index)  # Mark step done
    def complete()                 # Finish task
```

### Semantic Facades

Each facade wraps TaskTree with domain-specific meaning:

**Quest:**
```python
quest = Quest(
    quest_name="Find the Artifact",
    objectives=[...],              # Alias for steps
    reward_gold=100
)
quest.add_objective(task)         # Domain-specific method
```

**Behavior:**
```python
patrol = Behavior(
    npc_id="guard_01",
    actions=[...],                 # Alias for steps
    loop=True
)
patrol.add_action(task)           # Domain-specific method
```

**Sequence:**
```python
cutscene = Sequence(
    scenes=[...],                  # Alias for steps
    skippable=True
)
cutscene.skip()                   # Domain-specific method
```

**Conversation:**
```python
dialogue = Conversation(
    speaker="keen",
    lines=[...],                   # Alias for steps
    emotion="curious"
)
dialogue.branch(choice_index)     # Domain-specific method
```

**Maintenance:**
```python
cleanup = Maintenance(
    tasks=[...],                   # Alias for steps
    memory_threshold=0.8
)
cleanup.should_run(memory_usage)  # Domain-specific method
```

**Routine:**
```python
restock = Routine(
    interval_seconds=86400,
    tasks=[...]                    # Uses steps directly
)
restock.should_run(current_time)  # Domain-specific method
```

---

## Why This Works

### For Designers:
- "I'm creating a Quest" - clear meaning
- "I'm writing a Conversation" - obvious purpose
- Domain-specific helpers (add_objective, add_line, skip)

### For Runtime:
- All route through TaskRouter
- All execute the same way
- All clean memory on completion
- All emit deltas to ZON4D

### For Serialization:
- All are dataclasses
- All convert to/from ZW/ZON4D
- Meaningful field names for each domain

---

## Installation

```bash
# 1. Install updated task_system.py
cd ~/Downloads/EngAIn/zonengine4d/zon4d/ENGINALITY
cp ~/Downloads/task_system.py .

# 2. Install test file
cp ~/Downloads/test_semantic_facades.py .

# 3. Run tests
cd ~/Downloads/EngAIn/zonengine4d/zon4d
python3 -m ENGINALITY.test_semantic_facades
```

---

## Expected Output

```
SEMANTIC FACADES TEST SUITE
Same TaskTree, Different Meanings

============================================================
TEST 1: QUEST (Player Missions)
============================================================
Quest: The Lost Artifact
Objectives: 3
  1. talk_to_elder
  2. travel_to_ruins
  3. defeat_guardian
Reward: 100 gold + ['legendary_sword']
✅ Quest works

============================================================
TEST 2: BEHAVIOR (NPC AI)
============================================================
Behavior: guard_patrol
NPC: castle_guard_01
Actions: 3
  1. walk_to_waypoint_1
  2. wait
  3. walk_to_waypoint_2
Loop: True
Should loop? True
✅ Behavior works

... (6 more tests)

🔥 ALL SEMANTIC FACADE TESTS PASSED 🔥

What this proves:
  ✅ Quest - player missions
  ✅ Behavior - NPC AI
  ✅ Sequence - cutscenes
  ✅ Conversation - dialogue
  ✅ Maintenance - pocket tasks
  ✅ Routine - recurring tasks
  ✅ All use same TaskTree underneath
  ✅ All route through same TaskRouter

One implementation, many semantic meanings.
This is clean architecture.
```

---

## What Changed in task_system.py

### Added:
1. **TaskState enum** - PENDING/RUNNING/PAUSED/COMPLETED/FAILED/CANCELLED
2. **TaskTree base class** - Universal tree structure
3. **Six semantic facades** - Quest, Behavior, Sequence, Conversation, Maintenance, Routine

### Preserved:
- Task (flat task for execution)
- TaskDomain
- TaskPriority
- TaskRouter
- TaskHandler protocol
- All existing functionality

---

## Next Steps

Now that semantic facades exist:

### STEP 2: Wire Runtime Loop
- Runtime emits Maintenance tasks
- Tracks active Quests/Behaviors
- Advances task steps each tick

### STEP 3: Wire Performer
- Performer emits Sequence/Conversation tasks
- Converts to flat Tasks for execution

### STEP 4: Build Godot ABI
- Route Quest → UI system
- Route Behavior → NavAgent
- Route Conversation → DialogueManager
- Route Maintenance → Engine

---

## The Paradigm

**Before:**
- Runtime speaks Deltas
- Performer speaks PerformanceTasks
- Godot speaks node calls
- Everyone translates

**After:**
- Runtime speaks Task (Maintenance)
- Performer speaks Task (Sequence/Conversation)
- Godot speaks Task (routing)
- Quests speak Task (objectives)
- NPCs speak Task (behaviors)
- ONE LANGUAGE, no translation

---

## Files

[task_system.py](computer:///mnt/user-data/outputs/task_system.py) - Updated with semantic facades
[test_semantic_facades.py](computer:///mnt/user-data/outputs/test_semantic_facades.py) - Tests all 6 facades

---

## For GPT

Show GPT this output and say:

> "I asked where pocket tasks fit in the architecture.  
> You said 'tasks are everywhere, they're implicit.'  
>   
> I built TaskTree + 6 semantic facades:  
> - Quest (player missions)  
> - Behavior (NPC AI)  
> - Sequence (cutscenes)  
> - Conversation (dialogue)  
> - Maintenance (pocket tasks)  
> - Routine (recurring tasks)  
>   
> Same implementation, different semantic meanings.  
> All route through TaskRouter.  
> All ready for ZW/ZON4D serialization.  
>   
> This is what 'build the abstraction first' means.  
> Engineering over philosophy."

---

**STEP 1 COMPLETE ✅**

Semantic facades exist.  
Ready to wire Runtime, Performer, and Godot.
