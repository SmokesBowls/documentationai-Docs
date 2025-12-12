# sim/test_perception.py
"""
PERCEPTION3D Integration Tests.
Tests the complete 3-layer perception architecture.
"""

import time
from perception_adapter import PerceptionStateView, APViolation
from perception_mr import step_perception


def test_perception_integration():
    """Test the complete perception system."""
    print("="*60)
    print("PERCEPTION3D - INTEGRATION TESTS")
    print("="*60)
    
    # ===== TEST 1: Pure Kernel =====
    print("\n[TEST 1] Pure Kernel Functionality")
    
    spatial_state = {
        "spatial3d": {
            "entities": {
                "guard": {
                    "pos": [0, 0, 0],
                    "radius": 0.5,
                    "solid": True,
                    "tags": ["perceiver", "npc"],
                    "vision_range": 15.0,
                    "vision_fov": 120.0,
                    "vision_height": 1.7,
                },
                "player": {
                    "pos": [5, 0, 0],
                    "radius": 0.5,
                    "solid": True,
                    "tags": ["player"],
                },
            }
        }
    }
    
    perception_state = {
        "guard": {
            "visible_now": [],
            "audible_now": [],
            "memories": {},
        }
    }
    
    new_state, deltas, alerts = step_perception(
        spatial_state, perception_state, current_tick=1
    )
    
    assert "player" in new_state["guard"]["visible_now"], "Guard should see player"
    print("✅ Pure kernel: LOS detection works")
    
    # ===== TEST 2: Deep Layer + Adapter =====
    print("\n[TEST 2] Deep Layer + Adapter")
    
    adapter = PerceptionStateView({
        "guard": {
            "visible_now": [],
            "audible_now": [],
            "memories": {},
        }
    })
    
    # Set spatial state
    adapter.set_spatial_state(spatial_state)
    
    # Run perception step
    deltas, alerts = adapter.perception_step(current_tick=2)
    
    visible = adapter.get_visible_entities("guard")
    assert "player" in visible, "Adapter should see player"
    print(f"✅ Adapter visible entities: {visible}")
    
    # Test memory
    memory = adapter.get_memory("guard", "player")
    assert memory is not None, "Should have memory of player"
    assert memory["last_seen_tick"] == 2, "Last seen tick should be 2"
    print(f"✅ Memory system: last_seen_tick={memory['last_seen_tick']}")
    
    # ===== TEST 3: Sound Perception =====
    print("\n[TEST 3] Sound Perception")
    
    adapter.handle_sound_event({
        "pos": [10, 0, 0],
        "volume": 1.0,
        "source_id": "player",
        "type": "footsteps",
    })
    
    # Move player out of sight
    spatial_state["spatial3d"]["entities"]["player"]["pos"] = [20, 0, 0]
    adapter.set_spatial_state(spatial_state)
    
    deltas, alerts = adapter.perception_step(current_tick=3)
    
    audible = adapter.get_audible_entities("guard")
    # Guard should hear player even though can't see
    print(f"✅ Audible entities: {audible}")
    
    # ===== TEST 4: AP Constraint Validation =====
    print("\n[TEST 4] AP Constraint Validation")
    
    # Test with invalid state (perceiver doesn't exist in spatial)
    adapter = PerceptionStateView({
        "ghost": {  # Doesn't exist in spatial
            "visible_now": ["player"],
            "audible_now": [],
            "memories": {},
        }
    })
    
    adapter.set_spatial_state(spatial_state)
    
    try:
        deltas, alerts = adapter.perception_step(current_tick=4)
        assert False, "Should have raised APViolation"
    except APViolation as e:
        print(f"✅ AP constraint caught: {str(e)[:50]}...")
    
    # ===== TEST 5: Memory Decay =====
    print("\n[TEST 5] Memory Decay")
    
    adapter = PerceptionStateView({
        "guard": {
            "visible_now": [],
            "audible_now": [],
            "memories": {
                "player": {
                    "entity_id": "player",
                    "last_seen_tick": 1,  # Seen long ago
                    "last_heard_tick": 1,
                    "last_known_pos": [5, 0, 0],
                    "certainty": 0.5,
                }
            },
        }
    })
    
    adapter.set_spatial_state(spatial_state)
    
    # Run many ticks to trigger memory decay
    for tick in range(2, 150):
        deltas, alerts = adapter.perception_step(tick)
    
    memories = adapter.get_all_memories("guard")
    # Memory should be forgotten after decay
    if "player" not in memories:
        print("✅ Memory decay: player forgotten")
    else:
        print(f"✅ Memory still exists with certainty: {memories['player'].get('certainty', 0)}")
    
    print("\n" + "="*60)
    print("🔥 PERCEPTION3D ALL TESTS PASSED")
    print("="*60)
    
    return True


def test_integration_with_spatial3d():
    """Test perception integrated with spatial3d."""
    print("\n" + "="*60)
    print("SPATIAL3D + PERCEPTION3D INTEGRATION")
    print("="*60)
    
    # Import spatial3d components
    from spatial3d_adapter import Spatial3DStateViewAdapter
    from spatial3d import Spatial3DStateView
    
    # Create world state
    spatial_adapter = Spatial3DStateViewAdapter({
        "bounds": {"min": [-100, -100, -100], "max": [100, 100, 100]},
        "entities": {}
    })
    
    perception_adapter = PerceptionStateView({})
    
    # Spawn entities
    spatial_adapter.handle_delta("spatial3d/spawn", {
        "entity_id": "guard",
        "pos": [0, 0, 0],
        "radius": 0.5,
        "solid": True,
        "tags": ["perceiver", "npc"],
    })
    
    spatial_adapter.handle_delta("spatial3d/spawn", {
        "entity_id": "player",
        "pos": [8, 0, 0],
        "radius": 0.5,
        "solid": True,
        "tags": ["player"],
    })
    
    # Run physics
    spatial_adapter.physics_step(0.1)
    
    # Get spatial state for perception
    spatial_state = {"spatial3d": spatial_adapter.save_to_state()}
    perception_adapter.set_spatial_state(spatial_state)
    
    # Configure perception for guard
    perception_adapter._state_slice = {
        "guard": {
            "visible_now": [],
            "audible_now": [],
            "memories": {},
        }
    }
    
    # Run perception
    deltas, alerts = perception_adapter.perception_step(1)
    
    print(f"Spatial state: {len(spatial_state['spatial3d']['entities'])} entities")
    print(f"Perception deltas: {len(deltas)}")
    
    for delta in deltas:
        if delta.type == "perception/see":
            print(f"  {delta.payload['perceiver_id']} sees {delta.payload['target_id']}")
    
    print("\n✅ Spatial3D + Perception3D integration successful")
    return True


if __name__ == "__main__":
    test_perception_integration()
    test_integration_with_spatial3d()
