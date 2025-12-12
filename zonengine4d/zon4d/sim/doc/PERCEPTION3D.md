Good. Layered, not blended. That’s the right move here.

Here’s the spec you asked for — you can drop this straight into something like:

`docs/PERCEPTION3D_SPEC.md` or `zonengine4d/zon4d/spec/PERCEPTION3D.md`.

---

# PERCEPTION3D SPEC v0.1 (Layered Architecture)

**Status:** Draft (Aligned with Spatial3D v1.0)
**Domain:** EngAIn / ZON4D / ENGINALITY
**Scope:** Perception (vision + hearing + memory) as a layered system:

* **Kernel layer (mr):** pure functional LOS + visibility math
* **Domain layer (deep):** ZON4D-native perception state, memory, hearing, and tasks
* **Adapter:** bridge that connects Spatial3D snapshots → mr kernel → deep state

---

## 1. Goals

Perception3D is responsible for answering, in a deterministic, rollback-safe way:

* **Who can see whom right now?** (instant LOS)
* **What has each agent recently seen or heard?** (memory)
* **How certain are they?** (certainty/decay)
* **Which perception changes should drive behavior?** (events/deltas)

Key principles:

1. **Layered** not merged:

   * mr = pure math, engine-agnostic
   * deep = ZON4D contract + AP constraints
   * adapter = glue

2. **Deterministic**:

   * No random
   * Snapshot-in → snapshot-out
   * All events reproducible from the same inputs

3. **Temporal**:

   * Perception is part of ZON4D snapshots
   * Memory evolves across ticks, can be rolled back

4. **Engine-agnostic kernels**:

   * mr layer can be ported to C++/Rust/GDExtension without touching deep.

---

## 2. Layer Overview

### 2.1 Dependencies

Perception3D depends on:

* **ZON4D Temporal Runtime**
* **Spatial3D domain** (already locked)
* **AP validator** (for constraints & rollback)
* **Task system** (for behavior integration)

Perception does **not** mutate Spatial3D directly. It only reads spatial state.

---

### 2.2 Layers

#### (A) Kernel: `perception_mr` (mr3d)

**Responsibility:**

* Given current Spatial3D state + previous perception state:

  * compute which entities see which other entities (LOS)
  * compute visibility changes (seen / lost events)
* Optionally add simple hearing hooks later (distance-based).

**Inputs:**

* `spatial_state: dict`

  * `bounds`: `{ "min": [x,y,z], "max": [x,y,z] }`
  * `entities`: `id -> { pos, radius, solid, tags, vision{enabled, range, fov_deg, forward} }`

* `perception_state: dict | None`

  * `{"visible": {"viewer_id": ["target1", "target2", ...]}}`

**Outputs:**

* `new_perception_state: dict`

  * same shape: `{"visible": {...}}`
* `events: List[PerceptionEvent]`

  * `{"kind": "seen"|"lost", "viewer_id": str, "target_id": str}`
* `alerts: List[PerceptionAlert]`

  * kernel-level issues (e.g., degenerate inputs, weird geometry)

**Contract:**

* Pure function: no side effects, no global state.
* Deterministic given same `spatial_state`, `perception_state`, `dt`.

---

#### (B) Adapter: `PerceptionStateViewAdapter`

**Responsibility:**

* Implement ZON4D **StateView** for perception.
* Hold perception domain slice: memory, visible_now, heard, etc.
* Call mr kernel every tick using the current spatial snapshot.
* Convert mr events into ZON4D-style deltas and runtime Alerts.

**Key methods:**

* `load_from_state(state_slice: dict)`
* `save_to_state() -> dict`
* `set_spatial_state(spatial_slice: dict)`  ← wired by runtime
* `perception_step(delta_time: float) -> (alerts: List[Alert], perception_deltas: List[dict])`

**Domain slice outline (deep side):**

```python
perception_state = {
    "visible_now": {   # instantaneous visibility graph
        "viewer_id": ["target_id", ...],
    },
    "memory": {        # long(er)-term memory of what was seen
        "viewer_id": {
            "target_id": {
                "last_seen_tick": int,
                "last_seen_pos": [x, y, z],
                "certainty": float,     # 0.0 – 1.0
            },
            ...
        },
    },
    "heard": {         # hearing events (optional in v0.1, planned)
        "listener_id": [
            {
                "source_id": str | None,
                "pos": [x, y, z],
                "strength": float,
                "tick": int,
            },
            ...
        ]
    },
}
```

**Perception deltas produced:**

Minimal v0.1:

```python
{
  "id": "perception_seen_<viewer>_<target>@<tick>",
  "type": "perception/seen",
  "payload": {"viewer_id": "...", "target_id": "..."},
  "priority": 0,
  "tags": ["perception"]
}

{
  "id": "perception_lost_<viewer>_<target>@<tick>",
  "type": "perception/lost",
  "payload": {"viewer_id": "...", "target_id": "..."},
  "priority": 0,
  "tags": ["perception"]
}
```

Later expansions (still same pattern): `perception/heard`, `perception/remembered`, etc.

---

#### (C) Deep Perception Domain

This is **the brain**. It sits fully inside ZON4D and ENGINALITY.

**Responsibilities:**

* Maintain `perception_state` in the world snapshot.
* Integrate mr events + existing memory:

  * update `visible_now`
  * update `memory` (last seen tick, pos, certainty)
  * decay certainty over time
  * purge stale entries
* Produce high-level deltas that drive behavior:

  * `"perception/suspicious"`, `"perception/investigate"`, etc. (future)

**Memory update rules (v0.1):**

When `seen(viewer, target)`:

* Set `visible_now[viewer].add(target)`
* `memory[viewer][target]`:

  * `last_seen_tick = current_tick`
  * `last_seen_pos = target.pos from Spatial3D`
  * `certainty = 1.0`

When `lost(viewer, target)`:

* Remove from `visible_now[viewer]`
* Keep memory entry but start decaying certainty over ticks.

Per tick (decay):

* For each `memory[viewer][target]` not in `visible_now`:

  ```python
  ticks_since = current_tick - last_seen_tick
  certainty = max(0.0, 1.0 - decay_rate * ticks_since)
  ```

* If `certainty <= threshold_min` → delete memory entry.

---

## 3. Data Contracts

### 3.1 Spatial3D Contract (Consumed by Perception)

Perception assumes **Spatial3D** provides:

```python
spatial3d = {
  "bounds": {
    "min": [x_min, y_min, z_min],
    "max": [x_max, y_max, z_max],
  },
  "entities": {
    "<entity_id>": {
      "pos": [x, y, z],
      "radius": float,
      "solid": bool,
      "tags": [str, ...],
      "vision": {
        "enabled": bool,
        "range": float,    # meters / units
        "fov_deg": float,  # 0–360
        "forward": [x,y,z] # optional, default +Z
      },
      # optional hearing config later:
      # "audition": { "range": float, "sensitivity": float }
    },
    ...
  }
}
```

No extra fields required. Perception ignores everything else.

---

### 3.2 Perception Slice (Stored in ZON4D Snapshot)

In the full world snapshot:

```python
snapshot = {
  ...,
  "spatial3d": {...},
  "perception": {
    "visible_now": {
      "viewer_id": ["target1", "target2", ...],
    },
    "memory": {
      "viewer_id": {
        "target_id": {
          "last_seen_tick": int,
          "last_seen_pos": [x, y, z],
          "certainty": float,  # 0.0–1.0
        }
      }
    },
    "heard": {
      "listener_id": [
        {
          "source_id": str | None,
          "pos": [x,y,z],
          "strength": float,
          "tick": int
        }
      ]
    }
  }
}
```

---

## 4. Tick Flow & Integration

Tick N:

1. **Spatial3D step**

   * Apply movement/physics deltas.
   * `Spatial3DStateViewAdapter.physics_step(dt)`
   * ZON4D snapshot updated with new positions.

2. **Perception3D step**

   * `perception_adapter.set_spatial_state(snapshot["spatial3d"])`
   * `alerts_mr, perception_events = step_perception(spatial3d, old_perception_state, dt)`
   * Deep layer:

     * Update `visible_now`
     * Update `memory` with decay + last_seen
   * Emit:

     * runtime Alerts from mr + deep
     * optional perception deltas into engine pipeline

3. **AP Validation**

   * Run AP constraints including Perception invariants.
   * On violation → rollback to last immutable anchor.

4. **TaskRouter / Behavior**

   * Consume perception deltas:

     * Guard AI reacts to `perception/seen` of player
     * NPC decides to search area after `lost` + non-zero certainty.

---

## 5. AP Constraints (Perception)

These are deep-level rules that **must hold** after perception_step.

### 5.1 Existence Consistency

```python
perception_consistency_constraint(snapshot):
    for viewer_id, targets in perception.visible_now.items():
        assert viewer_id in spatial3d.entities
        for target_id in targets:
            assert target_id in spatial3d.entities
```

On failure → AP violation (invalid perception graph).

---

### 5.2 Memory Consistency

Rules:

* If `memory[viewer][target]` exists:

  * `viewer` and `target` must exist in Spatial3D.
  * `last_seen_tick <= current_tick`.
  * `0.0 <= certainty <= 1.0`.

You can codify as:

```python
perception_memory_constraint(snapshot, current_tick):
    for viewer, targets in memory.items():
        if viewer not in spatial.entities: return False, ...
        for target, entry in targets.items():
            if target not in spatial.entities: return False, ...
            if entry["last_seen_tick"] > current_tick: return False, ...
            c = entry["certainty"]
            if not (0.0 <= c <= 1.0): return False, ...
```

---

### 5.3 Optional LOS Plausibility (v1.1+)

Later, you can add a constraint that replays a subset of LOS raycasts to verify:

* any `(viewer, target)` in `visible_now` must have unoccluded LOS.

For now, mr is considered ground truth, so this is optional.

---

## 6. Task & Delta Facades

### 6.1 Perception Deltas (from Adapter)

Core ones:

* `perception/seen`
* `perception/lost`

Optional later:

* `perception/heard`
* `perception/suspicious`
* `perception/investigate`

Standard shape:

```python
{
  "id": "perception_<kind>_<viewer>_<target>@<tick>",
  "type": "perception/<kind>",
  "payload": {...},
  "priority": 0,
  "tags": ["perception"],
}
```

### 6.2 Task Facade (Deep Convenience)

Example:

```python
class PerceptionTaskFacade:

    @staticmethod
    def create_forced_scan_task(entity_id: str, priority: int = 5) -> Task:
        return Task(
            id=f"perception_scan_{entity_id}",
            type="perception/scan",
            domain="PERCEPTION",
            priority=priority,
            payload={"entity_id": entity_id},
        )
```

Behavior systems can respond by biasing that entity’s perception or focusing them on a specific cone or direction.

---

## 7. Extensibility Plan

v0.1 (now):

* LOS-based visibility via mr kernel
* `visible_now` + basic memory entries
* seen/lost deltas
* existence/memory AP constraints

v0.2+:

* Add **hearing** model:

  * sound events from Spatial3D or separate Audio domain
  * hearing range, strength, occlusion
  * `perception/heard` deltas

* Add **uncertainty-driven behavior**:

  * `certainty` influences decision trees
  * AP constraints to keep certainty sane

* Add **profiles** (perception archetypes):

  * guard vs scout vs beast vs turret

* Add **temporal perception queries**:

  * “who saw X in the last N ticks?”
  * “where was X last seen by any ally?”

---

## 8. Invariants Summary

Perception layer must always respect:

1. **Determinism**
   Same spatial + perception state + tick index → same results.

2. **No write to Spatial3D**
   Perception reads spatial, writes only to its own domain.

3. **AP-safe**
   All perception state must be plausible relative to the current Spatial3D slice.

4. **Rollback-safe**
   Perception state is part of ZON4D snapshot; rollback restores both spatial and perception consistently.

---

If you want, next step after this spec is:

* Generate the **final folder layout**:

  * `zon4d/sim/perception_mr.py`
  * `zon4d/sim/perception_adapter.py`
  * `zon4d/spec/PERCEPTION3D_SPEC.md` (this)

and tighten any naming to match your current tree exactly.
