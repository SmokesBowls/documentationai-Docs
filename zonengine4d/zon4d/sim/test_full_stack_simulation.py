# test_full_stack_simulation.py - FIXED VERSION

print("============================================================")
print("FULL STACK SIMULATION - FINAL FIXED")
print("Spatial3D + Perception3D + Navigation3D")
print("============================================================")

from spatial3d_adapter import Spatial3DStateViewAdapter
from perception_adapter import PerceptionStateView
from navigation_adapter import NavigationStateView

# ============================================================
# 1. SPATIAL SETUP WITH PERCEIVER COMPONENT
# ============================================================
print("\n[SETUP] Creating Spatial3D with perceiver component...")

# Create spatial with explicit no gravity AND perceiver support
spatial_state = {
    "entities": {},
    "gravity": [0.0, 0.0, 0.0],
    "drag": 0.0,
    "static_entities": [],
    "perceivers": ["guard"]  # Explicit list of perceivers
}
spatial = Spatial3DStateViewAdapter(state_slice=spatial_state)

# ============================================================
# 2. SPAWN ENTITIES WITH PERCEIVER COMPONENT
# ============================================================
print("\n[SPAWN] Creating entities...")

# Spawn guard with perceiver component
spawn_data = {
    "entity_id": "guard",
    "pos": (0, 0, 0),
    "radius": 0.5,
    "solid": True,
    "tags": ["guard", "perceiver"],
    "components": ["perceiver"],  # Add perceiver component
    "perceiver": {  # Add perceiver data
        "vision_range": 50.0,
        "fov": 180.0,
        "height": 1.8
    }
}
success, alerts = spatial.handle_delta("spatial3d/spawn", spawn_data)
print(f"Spawned guard with perceiver component: {'✓' if success else '✗'}")

# Spawn player
spawn_data = {
    "entity_id": "player",
    "pos": (15, 0, 0),
    "radius": 0.5,
    "solid": True,
    "tags": ["player"],
    "mass": 1000.0,  # Heavy = static
    "static": True
}
success, alerts = spatial.handle_delta("spatial3d/spawn", spawn_data)
print(f"Spawned player (static): {'✓' if success else '✗'}")

# Spawn wall
spawn_data = {
    "entity_id": "wall",
    "pos": (5, 0, 0),
    "radius": 2.0,
    "solid": True,
    "tags": ["obstacle"],
    "mass": 1000.0,  # Heavy = static
    "static": True
}
success, alerts = spatial.handle_delta("spatial3d/spawn", spawn_data)
print(f"Spawned wall (static): {'✓' if success else '✗'}")

# Apply physics
alerts = spatial.physics_step(delta_time=0.0)
print(f"Physics step: {len(alerts)} alerts")

# Check final positions
spatial_state = spatial.save_to_state()
entities = spatial_state.get("entities", {})
print(f"\nInitial positions:")
for entity_id in ["guard", "player", "wall"]:
    if entity_id in entities:
        pos = entities[entity_id].get("pos", "unknown")
        print(f"  {entity_id}: {pos}")

# ============================================================
# 3. PERCEPTION SETUP WITH PROPER STATE
# ============================================================
print("\n[PERCEPTION] Setting up perception...")

# Create perception with empty state (let it initialize properly)
perception = PerceptionStateView(state_slice={})

# DEBUG: Check what perception state looks like
print(f"Perception initial state keys: {list(perception._state_slice.keys())}")

# Update spatial state with perceiver list
if "perceivers" not in spatial_state:
    spatial_state["perceivers"] = ["guard"]

# Provide spatial state to perception
perception.set_spatial_state({"spatial3d": spatial_state})
print(f"Set spatial state with perceivers: {spatial_state.get('perceivers', [])}")

# Try perception step
try:
    deltas, alerts = perception.perception_step(current_tick=1)
    print(f"Perception step succeeded: {len(alerts)} alerts")
    
    # Check what guard sees
    perception_state = perception.save_to_state()
    print(f"\nPerception state structure: {list(perception_state.keys())}")
    
    # Look for guard's perception data
    for key, value in perception_state.items():
        if key == "guard" or (isinstance(value, dict) and "visible" in value):
            print(f"Found guard perception data in key: {key}")
            if isinstance(value, dict):
                visible = value.get("visible", [])
                print(f"  Guard sees: {visible}")
                
except Exception as e:
    print(f"Perception error: {e}")
    # Try alternative approach - check if we need to initialize perception state differently
    
    # Let's check the perception adapter to see what state structure it expects
    print("\n[DEBUG] Checking perception adapter requirements...")
    
    # Try creating perception with guard already in state
    perception2 = PerceptionStateView(state_slice={
        "guard": {
            "visible": [],
            "memory": {},
            "last_seen": {}
        }
    })
    
    perception2.set_spatial_state({"spatial3d": spatial_state})
    
    try:
        deltas, alerts = perception2.perception_step(current_tick=1)
        print(f"Alternative perception step: {len(alerts)} alerts")
        
        perception_state = perception2.save_to_state()
        if "guard" in perception_state:
            guard_data = perception_state["guard"]
            visible = guard_data.get("visible", [])
            print(f"Guard sees: {visible}")
    except Exception as e2:
        print(f"Alternative also failed: {e2}")

# ============================================================
# 4. NAVIGATION (This was working)
# ============================================================
print("\n[NAVIGATION] Setting up navigation...")

navigation = NavigationStateView()

# Build grid from spatial
navigation.update_obstacles_from_spatial({"spatial3d": spatial_state})

# Get positions
guard_pos = entities.get("guard", {}).get("pos", (0, 0, 0))
player_pos = entities.get("player", {}).get("pos", (15, 0, 0))

print(f"Guard position: {guard_pos}")
print(f"Player position: {player_pos}")

# Request path
navigation.request_path(
    entity_id="guard",
    start=guard_pos,
    goal=player_pos,
    current_tick=2,
    priority=1
)

# Process navigation
nav_deltas, nav_alerts = navigation.navigation_step(current_tick=2)
print(f"Navigation: {len(nav_alerts)} alerts")

# Get path
if hasattr(navigation, 'get_active_path'):
    path = navigation.get_active_path("guard")
elif "active_paths" in navigation._state_slice:
    path = navigation._state_slice["active_paths"].get("guard")

if path:
    print(f"✅ Path found! {len(path)} waypoints")
    print(f"Path goes around wall by moving to y={path[3][1]} (wall at y=0)")

# ============================================================
# 5. MOVEMENT USING MOVE (not teleport)
# ============================================================
print("\n[MOVEMENT] Testing movement...")

if path and len(path) > 1:
    # Use move (not teleport) to first waypoint
    target_pos = path[1]  # (1.5, 0.5, 0.5)
    print(f"Moving guard from {guard_pos} to {target_pos}")
    
    success, alerts = spatial.handle_delta("spatial3d/move", {
        "entity_id": "guard",
        "target_pos": target_pos,
        "speed": 5.0
    })
    
    if success:
        # Apply physics with multiple small steps for smooth movement
        for i in range(10):
            movement_alerts = spatial.physics_step(delta_time=0.05)
        
        # Check new position
        new_state = spatial.save_to_state()
        new_pos = new_state.get("entities", {}).get("guard", {}).get("pos", guard_pos)
        print(f"Movement applied. New position: {new_pos}")
        
        # Check if we're moving in the right direction
        dx = new_pos[0] - guard_pos[0]
        dy = new_pos[1] - guard_pos[1]
        print(f"Movement vector: dx={dx:.2f}, dy={dy:.2f}")
        
        # Check if we're getting closer to the waypoint
        dist_before = ((target_pos[0] - guard_pos[0])**2 + 
                      (target_pos[1] - guard_pos[1])**2)**0.5
        dist_after = ((target_pos[0] - new_pos[0])**2 + 
                     (target_pos[1] - new_pos[1])**2)**0.5
        print(f"Distance to waypoint: {dist_before:.2f} → {dist_after:.2f}")
    else:
        print("Move request failed")
        for alert in alerts:
            print(f"  Alert: {alert.message}")

# ============================================================
# FINAL STATE
# ============================================================
print("\n" + "="*60)
print("FINAL STATE")
print("="*60)

# Spatial
final_spatial = spatial.save_to_state()
print("\nSpatial Entities:")
for entity_id in ["guard", "player", "wall"]:
    if entity_id in final_spatial.get("entities", {}):
        data = final_spatial["entities"][entity_id]
        pos = data.get("pos", "unknown")
        vel = data.get("vel", [0,0,0])
        print(f"  {entity_id}: pos={pos}, vel={vel}")

# Perception
try:
    final_perception = perception.save_to_state()
    print("\nPerception State:")
    for key, value in final_perception.items():
        if key in ["guard", "player"] or (isinstance(value, dict) and "visible" in value):
            if isinstance(value, dict):
                visible = value.get("visible", [])
                print(f"  {key}: sees {visible}")
except:
    print("\nPerception State: Not available")

# Navigation
final_nav = navigation.save_to_state()
print(f"\nNavigation: {len(final_nav.get('active_paths', {}))} active paths")

print("\n" + "="*60)
print("SIMULATION COMPLETE")
print("="*60)