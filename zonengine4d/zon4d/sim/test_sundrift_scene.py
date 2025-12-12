# -------------------------------------------------------------
# Sundrift Gate Scene Test
# -------------------------------------------------------------
from scenes.sundrift_gate_scene import SCENE_SUNDRIFT_GATE
from scene_loader import SceneLoader

from spatial3d_adapter import Spatial3DStateViewAdapter
from perception_adapter import Perception3DStateViewAdapter
from navigation_adapter import Navigation3DStateViewAdapter
from behavior_adapter import BehaviorStateView

print("============================================================")
print("ENGAIN SCENE TEST — SUNDRIFT GATE")
print("============================================================")

# Initialize subsystems - ONLY CREATE ONE SPATIAL ADAPTER
spatial_adapter = Spatial3DStateViewAdapter()  # This is the unified adapter

perception = Perception3DStateViewAdapter({})
navigation = Navigation3DStateViewAdapter({})
behavior = BehaviorStateView({})

# Load the scene
loader = SceneLoader(spatial_adapter, behavior)
loader.load_scene(SCENE_SUNDRIFT_GATE)

print("[SIM] Starting 60-tick simulation.")

for tick in range(60):
    print(f"\n--- TICK {tick} ---")

    # Perception
    perception.set_spatial(spatial_adapter.save_to_state())
    p_deltas = perception.perception_step(tick)

    # Behavior
    behavior.set_inputs(
        spatial_adapter.save_to_state(),
        perception.save_to_state(),
        navigation.save_to_state(),
    )
    b_deltas, b_alerts = behavior.step(tick)

    # Handle behavior deltas
    for d in b_deltas:
        if d.type == "navigation3d/request_path":
            navigation.apply_delta(d)

    # Navigation
    n_deltas = navigation.navigation_step(tick)

    # Physics
    spatial_adapter.physics_step(0.016)

    # Print Tran + Guards
    for eid in ["tran", "guard_a", "guard_b"]:
        e = spatial_adapter.get_entity(eid)
        pos = e["pos"] if e else None
        print(f"  {eid}: {pos}")

print("\n============================================================")
print("SCENE SIM COMPLETE — SUNDSTRIFT GATE")
print("============================================================")
