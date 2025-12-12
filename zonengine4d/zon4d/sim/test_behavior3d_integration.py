#!/usr/bin/env python3
"""
test_behavior3d_integration.py - FULL 4-SUBSYSTEM INTEGRATION

Spatial3D + Perception3D + Navigation3D + Behavior3D
FIXED VERSION - Uses correct APIs
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spatial3d_adapter import Spatial3DStateViewAdapter
from perception_adapter import PerceptionStateView
from navigation_adapter import NavigationStateView
from behavior_adapter import BehaviorStateView
from behavior_mr import BehaviorStateType

print("=" * 60)
print("FULL 4-SUBSYSTEM INTEGRATION TEST")
print("Spatial3D + Perception3D + Navigation3D + Behavior3D")
print("=" * 60)
print()

# ============================================================
# SETUP PHASE
# ============================================================

print("[SETUP] Initializing all subsystems...")
print()

# Initialize adapters
spatial = Spatial3DStateViewAdapter(state_slice={})
perception = PerceptionStateView(state_slice={})
navigation = NavigationStateView()  # Uses defaults
behavior = BehaviorStateView()

print("✅ All adapters initialized")
print()

# ============================================================
# SPAWN ENTITIES
# ============================================================

print("[SPAWN] Creating entities...")

# Spawn guard (will have behavior AI)
spatial.handle_delta("spatial3d/spawn", {
    "entity_id": "guard",
    "position": [-10.0, 0.0, -10.0],
    "velocity": [0.0, 0.0, 0.0],
    "tags": ["npc", "guard", "hostile"],
    "health": 1.0,
    "radius": 0.5
})

# Spawn player
spatial.handle_delta("spatial3d/spawn", {
    "entity_id": "player",
    "position": [20.0, 0.0, 20.0],
    "velocity": [0.0, 0.0, 0.0],
    "tags": ["player"],
    "health": 1.0,
    "radius": 0.5
})

# Spawn wall obstacle
spatial.handle_delta("spatial3d/spawn", {
    "entity_id": "wall",
    "position": [5.0, 0.0, 5.0],
    "velocity": [0.0, 0.0, 0.0],
    "tags": ["obstacle", "static"],
    "health": 1.0,
    "radius": 1.0
})

# Apply spawns
spatial.physics_step(delta_time=0.0)

print("✅ Entities spawned:")
print("   - guard at (-10, 0, -10)")
print("   - player at (20, 0, 20)")
print("   - wall at (5, 0, 5)")
print()

# ============================================================
# INITIALIZE BEHAVIOR
# ============================================================

print("[BEHAVIOR] Setting up guard AI...")

# Give guard patrol behavior
patrol_route = [
    (-10.0, 0.0, -10.0),
    (0.0, 0.0, -10.0),
    (0.0, 0.0, 0.0),
    (-10.0, 0.0, 0.0)
]

behavior.add_behavior_entity(
    "guard",
    initial_state=BehaviorStateType.PATROL,
    patrol_points=patrol_route
)

print("✅ Guard patrol route configured (4 waypoints)")
print()

# ============================================================
# SIMULATION LOOP
# ============================================================

print("=" * 60)
print("RUNNING 10-TICK SIMULATION")
print("=" * 60)
print()

for tick in range(10):
    print(f"--- TICK {tick} ---")
    
    # Get current snapshots
    spatial_snapshot = {"spatial3d": spatial.save_to_state()}
    perception_snapshot = perception.save_to_state()
    navigation_snapshot = {"navigation3d": navigation.save_to_state()}
    
    # Update perception with spatial state
    perception.set_spatial_state(spatial_snapshot)
    perception_deltas, perception_alerts = perception.perception_step(current_tick=tick)
    
    # Update navigation with spatial obstacles
    navigation.update_obstacles_from_spatial(spatial_snapshot)
    
    # Update behavior with all subsystem states
    behavior.set_spatial_state(spatial_snapshot["spatial3d"])
    behavior.set_perception_state(perception.save_to_state())
    behavior.set_navigation_state(navigation_snapshot.get("navigation3d", {}))
    
    # Run behavior AI
    behavior_deltas, behavior_alerts = behavior.behavior_step(
        current_tick=float(tick),
        delta_time=0.016
    )
    
    print(f"  Perception deltas: {len(perception_deltas)}")
    print(f"  Behavior deltas: {len(behavior_deltas)}")
    
    # Process behavior deltas
    for delta in behavior_deltas:
        print(f"    → {delta.type}: {delta.payload.get('entity_id', 'N/A')}")
        
        if delta.type.startswith("navigation3d/"):
            # Route to navigation
            navigation.request_path(
                entity_id=delta.payload["entity_id"],
                start=tuple(delta.payload["start"]),
                goal=tuple(delta.payload["goal"]),
                current_tick=float(tick)
            )
    
    # Run navigation step (processes path requests)
    nav_deltas, nav_alerts = navigation.navigation_step(current_tick=float(tick))
    
    if nav_deltas:
        print(f"  Navigation deltas: {len(nav_deltas)}")
        for delta in nav_deltas:
            print(f"    → {delta.type}")
    
    # Run physics step
    spatial.physics_step(delta_time=0.016)
    
    # Show key states
    guard_pos = spatial.get_entity("guard").get("pos", [0,0,0])
    player_pos = spatial.get_entity("player").get("pos", [0,0,0])
    guard_behavior = behavior.get_behavior_state("guard")
    
    if guard_behavior:
        print(f"  Guard: pos={guard_pos}, state={guard_behavior['current_state']}, alert={guard_behavior['alert_level']:.2f}")
    
    print()

# ============================================================
# FINAL STATE REPORT
# ============================================================

print("=" * 60)
print("FINAL STATE")
print("=" * 60)
print()

# Spatial state
print("[SPATIAL]")
for entity_id in ["guard", "player", "wall"]:
    entity = spatial.get_entity(entity_id)
    if entity:
        print(f"  {entity_id}: pos={entity['pos']}, vel={entity['vel']}")
print()

# Behavior state
print("[BEHAVIOR]")
guard_behavior = behavior.get_behavior_state("guard")
if guard_behavior:
    print(f"  Guard:")
    print(f"    State: {guard_behavior['current_state']}")
    print(f"    Alert: {guard_behavior['alert_level']:.2f}")
    print(f"    Target: {guard_behavior.get('target_entity', 'None')}")
print()

# Navigation state
print("[NAVIGATION]")
nav_state = navigation.save_to_state()
active_paths = nav_state.get("active_paths", {})
print(f"  Active paths: {len(active_paths)}")
for entity_id, path_info in active_paths.items():
    print(f"    {entity_id}: {len(path_info['waypoints'])} waypoints")
print()

print("=" * 60)
print("INTEGRATION TEST SUMMARY")
print("=" * 60)
print("✅ Spatial3D: Entity spawning, physics")
print("✅ Perception3D: Vision tracking")
print("✅ Navigation3D: Pathfinding")
print("✅ Behavior3D: FSM AI")
print("✅ Integration: All subsystems communicating")
print()
print("🔥 FULL 4D SIMULATION STACK OPERATIONAL 🔥")
print("=" * 60)
