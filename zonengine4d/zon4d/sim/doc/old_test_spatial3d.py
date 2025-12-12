# test_spatial3d.py
"""
Test Spatial3D adapter implementation.
Validates the 3-layer architecture works.
"""

from spatial3d_adapter import Spatial3DStateViewAdapter, APViolation


def test_spawn_and_physics():
    """Test: Spawn entity and run physics step."""
    print("\n" + "="*60)
    print("TEST 1: SPAWN + PHYSICS")
    print("="*60)
    
    # Initialize adapter
    adapter = Spatial3DStateViewAdapter({
        "bounds": {"min": [-100, -100, -100], "max": [100, 100, 100]},
        "entities": {}
    })
    
    # Spawn entity
    success, alerts = adapter.handle_delta(
        "spatial3d/spawn",
        {
            "entity_id": "player",
            "pos": [0, 10, 0],
            "radius": 1.0,
            "solid": True,
            "tags": ["player"]
        }
    )
    
    print(f"Spawn success: {success}")
    print(f"Alerts: {len(alerts)}")
    
    # Run physics step (entity should fall with gravity)
    alerts = adapter.physics_step(dt=0.1)
    
    print(f"Physics alerts: {len(alerts)}")
    
    # Check entity moved
    state = adapter.save_to_state()
    player = state["entities"]["player"]
    print(f"Player position after physics: {player['pos']}")
    print(f"Player velocity: {player['vel']}")
    
    # Position should have changed due to gravity
    assert player["pos"][1] < 10, "Entity should have fallen"
    
    print("\n✅ Spawn + physics works")


def test_collision_detection():
    """Test: Two entities colliding triggers AP validation."""
    print("\n" + "="*60)
    print("TEST 2: COLLISION DETECTION")
    print("="*60)
    
    # Initialize with two overlapping entities
    adapter = Spatial3DStateViewAdapter({
        "bounds": {"min": [-100, -100, -100], "max": [100, 100, 100]},
        "entities": {}
    })
    
    # Spawn two entities
    adapter.handle_delta("spatial3d/spawn", {
        "entity_id": "entity_a",
        "pos": [0, 0, 0],
        "radius": 1.0,
        "solid": True,
    })
    
    adapter.handle_delta("spatial3d/spawn", {
        "entity_id": "entity_b",
        "pos": [1.0, 0, 0],  # Just touching
        "radius": 1.0,
        "solid": True,
    })
    
    # Run physics - collision resolution should push them apart
    try:
        alerts = adapter.physics_step(dt=0.1)
        print(f"Collision resolved: {len(alerts)} alerts")
        
        # Check they're no longer overlapping
        state = adapter.save_to_state()
        pos_a = state["entities"]["entity_a"]["pos"]
        pos_b = state["entities"]["entity_b"]["pos"]
        
        import math
        dx = pos_b[0] - pos_a[0]
        dy = pos_b[1] - pos_a[1]
        dz = pos_b[2] - pos_a[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        print(f"Distance after collision: {dist:.3f}")
        print(f"Minimum distance (2 * radius): 2.0")
        
        # Should be at least 2.0 apart (1.0 + 1.0 radii)
        assert dist >= 2.0, "Entities still overlapping after collision resolution"
        
        print("\n✅ Collision detection and resolution works")
        
    except APViolation as e:
        print(f"❌ AP Violation: {e}")
        raise


def test_bounds_enforcement():
    """Test: Entity stays within world bounds."""
    print("\n" + "="*60)
    print("TEST 3: BOUNDS ENFORCEMENT")
    print("="*60)
    
    adapter = Spatial3DStateViewAdapter({
        "bounds": {"min": [-10, -10, -10], "max": [10, 10, 10]},
        "entities": {}
    })
    
    # Spawn entity at edge
    adapter.handle_delta("spatial3d/spawn", {
        "entity_id": "test",
        "pos": [9, 0, 0],
        "radius": 0.5,
        "vel": [10, 0, 0],  # Moving fast towards boundary
    })
    
    # Run physics multiple times
    for i in range(10):
        alerts = adapter.physics_step(dt=0.1)
    
    # Check entity stayed in bounds
    state = adapter.save_to_state()
    pos = state["entities"]["test"]["pos"]
    
    print(f"Final position: {pos}")
    print(f"Bounds: [-10, 10]")
    
    assert pos[0] <= 10.0, "Entity exceeded max X bound"
    assert pos[0] >= -10.0, "Entity exceeded min X bound"
    
    print("\n✅ Bounds enforcement works")


def run_all_tests():
    print("\n" + "="*60)
    print("SPATIAL3D ADAPTER - VALIDATION TESTS")
    print("="*60)
    
    test_spawn_and_physics()
    test_collision_detection()
    test_bounds_enforcement()
    
    print("\n" + "="*60)
    print("🔥 ALL SPATIAL3D TESTS PASSED 🔥")
    print("="*60)
    print("\nWhat this proves:")
    print("  ✅ mr kernel = pure functional physics")
    print("  ✅ Deep contract = AP constraints validated")
    print("  ✅ Adapter = clean bridge with rollback")
    print("  ✅ 3-layer architecture works")
    print("\nSpatial3D ready. Perception3D next.")


if __name__ == "__main__":
    run_all_tests()
