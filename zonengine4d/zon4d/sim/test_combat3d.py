# test_combat3d.py
"""
Combat3D Integration Test

Demonstrates:
- Entity registration
- Damage application
- Death detection
- Low health alerts
- Delta propagation to other subsystems
"""

from combat3d_adapter import Combat3DAdapter


def test_basic_damage():
    """Test simple damage application"""
    combat = Combat3DAdapter()
    
    # Register a test entity
    combat.register_entity("player", health=100.0, max_health=100.0)
    
    # Apply damage
    combat.handle_delta("combat3d/apply_damage", {
        "source": "enemy_1",
        "target": "player",
        "amount": 30.0
    })
    
    # Process tick
    deltas = combat.tick()
    
    # Check state
    health, max_health = combat.get_entity_health("player")
    assert health == 70.0, f"Expected 70.0, got {health}"
    assert combat.is_alive("player")
    print("✓ Basic damage application works")


def test_death_detection():
    """Test death alert generation"""
    combat = Combat3DAdapter()
    
    combat.register_entity("enemy", health=50.0, max_health=100.0)
    
    # Apply lethal damage
    combat.handle_delta("combat3d/apply_damage", {
        "source": "player",
        "target": "enemy",
        "amount": 60.0
    })
    
    deltas = combat.tick()
    
    # Should generate death deltas
    assert not combat.is_alive("enemy")
    assert any(d[0] == "behavior3d/set_flag" and d[1]["flag"] == "dead" for d in deltas)
    assert any(d[0] == "navigation3d/disable" for d in deltas)
    
    print("✓ Death detection and alert propagation works")
    print(f"  Generated deltas: {deltas}")


def test_low_health_alert():
    """Test low health threshold alert"""
    combat = Combat3DAdapter()
    
    combat.register_entity("boss", health=100.0, max_health=100.0)
    
    # Reduce to 20% health (below 25% threshold)
    combat.handle_delta("combat3d/apply_damage", {
        "source": "player",
        "target": "boss",
        "amount": 80.0
    })
    
    deltas = combat.tick()
    
    # Should generate low_health alert
    assert combat.is_alive("boss")
    health, _ = combat.get_entity_health("boss")
    assert health == 20.0
    assert any(d[0] == "behavior3d/set_flag" and d[1]["flag"] == "low_health" for d in deltas)
    
    print("✓ Low health alert works")


def test_multiple_damage_events():
    """Test processing multiple damage events in one tick"""
    combat = Combat3DAdapter()
    
    combat.register_entity("player", health=100.0, max_health=100.0)
    combat.register_entity("enemy_1", health=50.0, max_health=50.0)
    combat.register_entity("enemy_2", health=30.0, max_health=50.0)
    
    # Queue multiple damage events
    combat.handle_delta("combat3d/apply_damage", {
        "source": "enemy_1",
        "target": "player",
        "amount": 15.0
    })
    combat.handle_delta("combat3d/apply_damage", {
        "source": "player",
        "target": "enemy_1",
        "amount": 25.0
    })
    combat.handle_delta("combat3d/apply_damage", {
        "source": "player",
        "target": "enemy_2",
        "amount": 40.0  # Lethal
    })
    
    # Process all at once
    deltas = combat.tick()
    
    assert combat.get_entity_health("player")[0] == 85.0
    assert combat.get_entity_health("enemy_1")[0] == 25.0
    assert not combat.is_alive("enemy_2")
    
    print("✓ Multiple simultaneous damage events work")
    print(f"  Generated {len(deltas)} deltas")


def test_damage_to_dead_entity():
    """Test that dead entities ignore damage"""
    combat = Combat3DAdapter()
    
    combat.register_entity("enemy", health=10.0, max_health=50.0)
    
    # Kill it
    combat.handle_delta("combat3d/apply_damage", {
        "source": "player",
        "target": "enemy",
        "amount": 15.0
    })
    combat.tick()
    
    assert not combat.is_alive("enemy")
    
    # Try to damage again
    combat.handle_delta("combat3d/apply_damage", {
        "source": "player",
        "target": "enemy",
        "amount": 100.0
    })
    deltas = combat.tick()
    
    # Should not generate additional death alerts
    death_deltas = [d for d in deltas if d[0] == "behavior3d/set_flag" and d[1].get("flag") == "dead"]
    assert len(death_deltas) == 0
    
    print("✓ Dead entities ignore damage correctly")


def demo_integration_pattern():
    """Show how Combat3D integrates with other subsystems"""
    print("\n=== Integration Pattern Demo ===")
    
    combat = Combat3DAdapter()
    
    # Typical engine initialization
    combat.register_entity("player", health=100.0, max_health=100.0)
    combat.register_entity("orc_1", health=80.0, max_health=80.0)
    
    print("Registered entities")
    
    # Behavior3D would emit this when attack lands:
    print("\n1. Behavior3D emits attack delta:")
    print('   ("combat3d/apply_damage", {"source": "player", "target": "orc_1", "amount": 45.0})')
    
    combat.handle_delta("combat3d/apply_damage", {
        "source": "player",
        "target": "orc_1",
        "amount": 45.0
    })
    
    # Engine calls this each frame
    print("\n2. Engine calls combat.tick()")
    deltas = combat.tick()
    
    print(f"\n3. Combat3D generates {len(deltas)} alert deltas:")
    for delta_type, payload in deltas:
        print(f"   ({delta_type}, {payload})")
    
    print("\n4. Engine propagates deltas to other subsystems")
    print("   → Behavior3D receives low_health flag")
    print("   → AI can now flee, call for help, etc.")


if __name__ == "__main__":
    test_basic_damage()
    test_death_detection()
    test_low_health_alert()
    test_multiple_damage_events()
    test_damage_to_dead_entity()
    demo_integration_pattern()
    
    print("\n✅ All Combat3D tests passed")
    print("Combat3D ready for integration")
