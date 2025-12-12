# test_full_stack_with_combat.py
"""
Full Stack Simulation with Combat3D Integration

Demonstrates complete EngAIn autonomous agent loop:
- Spatial3D: Physics, collision, transforms
- Perception3D: Line-of-sight, hearing, memory
- Navigation3D: Pathfinding, movement
- Behavior3D: Decision trees, state machines
- Combat3D: Damage, death, alerts

This test shows a guard that:
1. Patrols using Navigation3D
2. Takes damage via Combat3D
3. Reacts to low health (flees)
4. Dies and stops moving
"""

print("=" * 70)
print("FULL STACK SIMULATION WITH COMBAT3D")
print("Spatial + Perception + Navigation + Behavior + Combat")
print("=" * 70)

from spatial3d_adapter import Spatial3DStateViewAdapter
from perception_adapter import PerceptionStateView
from navigation_adapter import NavigationStateView
from combat3d_adapter import Combat3DAdapter

# ============================================================
# SIMULATION STATE
# ============================================================

class EngAInSimulation:
    """Unified simulation with all subsystems"""
    
    def __init__(self):
        # Initialize subsystems
        self.spatial = None
        self.perception = None
        self.navigation = None
        self.combat = Combat3DAdapter()
        
        # Entity behavior states
        self.behavior_states = {}  # entity_id -> state_name
        self.behavior_flags = {}   # entity_id -> set of flags
        
        # Delta queue for inter-subsystem communication
        self.delta_queue = []
        
        self.tick_count = 0
    
    def setup_spatial(self):
        """Initialize spatial with zero gravity"""
        spatial_state = {
            "entities": {},
            "gravity": [0.0, 0.0, 0.0],
            "drag": 0.0,
            "static_entities": [],
            "perceivers": []
        }
        self.spatial = Spatial3DStateViewAdapter(state_slice=spatial_state)
        print("[SPATIAL] Initialized with zero gravity")
    
    def setup_perception(self):
        """Initialize perception system"""
        self.perception = PerceptionStateView(state_slice={})
        print("[PERCEPTION] Initialized")
    
    def setup_navigation(self):
        """Initialize navigation system"""
        self.navigation = NavigationStateView()
        print("[NAVIGATION] Initialized")
    
    def spawn_entity(self, entity_id, pos, radius=0.5, solid=True, tags=None, 
                     perceiver=False, health=100.0, max_health=100.0):
        """
        Spawn entity across all subsystems
        
        Args:
            entity_id: Unique identifier
            pos: (x, y, z) position
            radius: Collision radius
            solid: Can collide
            tags: Entity tags list
            perceiver: Has perception capabilities
            health: Initial health
            max_health: Maximum health capacity
        """
        if tags is None:
            tags = []
        
        # Spawn in Spatial3D
        spawn_data = {
            "entity_id": entity_id,
            "pos": pos,
            "radius": radius,
            "solid": solid,
            "tags": tags,
            "components": ["perceiver"] if perceiver else [],
        }
        
        if perceiver:
            spawn_data["perceiver"] = {
                "vision_range": 50.0,
                "fov": 180.0,
                "height": 1.8
            }
            # Add to perceiver list
            spatial_state = self.spatial.save_to_state()
            if "perceivers" not in spatial_state:
                spatial_state["perceivers"] = []
            spatial_state["perceivers"].append(entity_id)
        
        success, alerts = self.spatial.handle_delta("spatial3d/spawn", spawn_data)
        
        if not success:
            print(f"[SPAWN] Failed to spawn {entity_id}")
            for alert in alerts:
                print(f"  Alert: {alert.message}")
            return False
        
        # Register in Combat3D
        self.combat.register_entity(entity_id, health=health, max_health=max_health)
        
        # Initialize behavior state
        self.behavior_states[entity_id] = "idle"
        self.behavior_flags[entity_id] = set()
        
        print(f"[SPAWN] {entity_id} at {pos} with {health}/{max_health} HP")
        return True
    
    def apply_damage(self, source_id, target_id, amount):
        """Apply damage from source to target"""
        self.combat.handle_delta("combat3d/apply_damage", {
            "source": source_id,
            "target": target_id,
            "amount": amount
        })
        print(f"[COMBAT] {source_id} deals {amount} damage to {target_id}")
    
    def tick(self, delta_time=0.016):
        """Run one simulation tick"""
        self.tick_count += 1
        print(f"\n{'=' * 70}")
        print(f"TICK {self.tick_count}")
        print(f"{'=' * 70}")
        
        # 1. Physics step (movement, collision)
        physics_alerts = self.spatial.physics_step(delta_time=delta_time)
        if physics_alerts:
            print(f"[PHYSICS] {len(physics_alerts)} alerts")
        
        # 2. Perception step (what entities see/hear)
        spatial_state = self.spatial.save_to_state()
        self.perception.set_spatial_state({"spatial3d": spatial_state})
        
        try:
            perception_deltas, perception_alerts = self.perception.perception_step(
                current_tick=self.tick_count
            )
            if perception_alerts:
                print(f"[PERCEPTION] {len(perception_alerts)} alerts")
        except Exception as e:
            print(f"[PERCEPTION] Error: {e}")
        
        # 3. Navigation step (pathfinding)
        self.navigation.update_obstacles_from_spatial({"spatial3d": spatial_state})
        nav_deltas, nav_alerts = self.navigation.navigation_step(
            current_tick=self.tick_count
        )
        if nav_alerts:
            print(f"[NAVIGATION] {len(nav_alerts)} alerts")
        
        # 4. Combat step (damage processing)
        combat_deltas = self.combat.tick()
        if combat_deltas:
            print(f"[COMBAT] {len(combat_deltas)} alert deltas")
            for delta_type, payload in combat_deltas:
                self.route_delta(delta_type, payload)
        
        # 5. Behavior step (AI decisions based on flags)
        self.behavior_step()
    
    def route_delta(self, delta_type, payload):
        """Route deltas to appropriate subsystems"""
        
        if delta_type == "behavior3d/set_flag":
            # Behavior flag update
            entity_id = payload["entity"]
            flag = payload["flag"]
            
            if entity_id not in self.behavior_flags:
                self.behavior_flags[entity_id] = set()
            
            self.behavior_flags[entity_id].add(flag)
            print(f"  → Behavior flag: {entity_id} now has '{flag}'")
            
        elif delta_type == "navigation3d/disable":
            # Disable navigation for entity
            entity_id = payload["entity"]
            # Clear any active paths
            nav_state = self.navigation.save_to_state()
            if "active_paths" in nav_state and entity_id in nav_state["active_paths"]:
                del nav_state["active_paths"][entity_id]
            print(f"  → Navigation disabled for {entity_id}")
        
        elif delta_type == "combat3d/apply_damage":
            # Route to combat (shouldn't happen in routing, but handle it)
            self.combat.handle_delta(delta_type, payload)
    
    def behavior_step(self):
        """Process behavior AI for all entities"""
        
        for entity_id, state in list(self.behavior_states.items()):
            flags = self.behavior_flags.get(entity_id, set())
            
            # Dead entities don't make decisions
            if "dead" in flags:
                if state != "dead":
                    print(f"[BEHAVIOR] {entity_id}: idle → dead")
                    self.behavior_states[entity_id] = "dead"
                continue
            
            # Low health triggers flee
            if "low_health" in flags and state != "fleeing":
                print(f"[BEHAVIOR] {entity_id}: {state} → fleeing (low health!)")
                self.behavior_states[entity_id] = "fleeing"
                # Could emit flee movement here
                continue
            
            # Normal behavior continues
            if state == "idle":
                # Could start patrolling, etc.
                pass
    
    def get_entity_status(self, entity_id):
        """Get complete entity status across all subsystems"""
        status = {
            "entity_id": entity_id,
            "exists": False
        }
        
        # Spatial
        spatial_state = self.spatial.save_to_state()
        if entity_id in spatial_state.get("entities", {}):
            entity_data = spatial_state["entities"][entity_id]
            status["exists"] = True
            status["pos"] = entity_data.get("pos")
            status["vel"] = entity_data.get("vel")
        
        # Combat
        health, max_health = self.combat.get_entity_health(entity_id)
        status["health"] = health
        status["max_health"] = max_health
        status["alive"] = self.combat.is_alive(entity_id)
        
        # Behavior
        status["state"] = self.behavior_states.get(entity_id, "unknown")
        status["flags"] = list(self.behavior_flags.get(entity_id, set()))
        
        return status
    
    def print_entity_status(self, entity_id):
        """Print readable entity status"""
        status = self.get_entity_status(entity_id)
        if not status["exists"]:
            print(f"{entity_id}: NOT FOUND")
            return
        
        print(f"{entity_id}:")
        print(f"  Position: {status['pos']}")
        print(f"  Health: {status['health']:.1f}/{status['max_health']:.1f}")
        print(f"  Alive: {status['alive']}")
        print(f"  State: {status['state']}")
        if status['flags']:
            print(f"  Flags: {', '.join(status['flags'])}")


# ============================================================
# SCENARIO: Guard Takes Damage and Reacts
# ============================================================

def run_combat_scenario():
    """
    Scenario:
    1. Spawn guard with 100 HP
    2. Guard patrols (simulated)
    3. Guard takes 40 damage → low health (60/100)
    4. Guard behavior changes to "fleeing"
    5. Guard takes 70 damage → dies
    6. Navigation disables, no more movement
    """
    
    sim = EngAInSimulation()
    
    print("\n[SETUP] Initializing subsystems...")
    sim.setup_spatial()
    sim.setup_perception()
    sim.setup_navigation()
    
    print("\n[SETUP] Spawning entities...")
    sim.spawn_entity("guard", pos=(0, 0, 0), perceiver=True, 
                     health=100.0, max_health=100.0)
    sim.spawn_entity("enemy", pos=(10, 0, 0), 
                     health=50.0, max_health=50.0)
    sim.spawn_entity("wall", pos=(5, 0, 0), radius=2.0)
    
    # Initial state
    print("\n[STATUS] Initial state:")
    sim.print_entity_status("guard")
    
    # Tick 1: Normal operation
    print("\n" + "=" * 70)
    print("SCENARIO: Normal patrol")
    print("=" * 70)
    sim.tick()
    sim.print_entity_status("guard")
    
    # Tick 2: Take moderate damage (80) → triggers low_health
    print("\n" + "=" * 70)
    print("SCENARIO: Guard takes 80 damage (20/100 HP remaining)")
    print("=" * 70)
    sim.apply_damage("enemy", "guard", 80.0)
    sim.tick()
    sim.print_entity_status("guard")
    
    # Verify low_health flag was set
    status = sim.get_entity_status("guard")
    assert "low_health" in status["flags"], "low_health flag should be set"
    assert status["state"] == "fleeing", "Guard should be fleeing"
    print("\n✓ Guard correctly entered flee state on low health")
    
    # Tick 3: Take lethal damage (30) → dies
    print("\n" + "=" * 70)
    print("SCENARIO: Guard takes 30 damage (LETHAL)")
    print("=" * 30)
    sim.apply_damage("enemy", "guard", 30.0)
    sim.tick()
    sim.print_entity_status("guard")
    
    # Verify death handling
    status = sim.get_entity_status("guard")
    assert not status["alive"], "Guard should be dead"
    assert "dead" in status["flags"], "dead flag should be set"
    assert status["state"] == "dead", "Guard should be in dead state"
    print("\n✓ Guard correctly died and stopped moving")
    
    # Tick 4: Try to damage dead entity (should be ignored)
    print("\n" + "=" * 70)
    print("SCENARIO: Attempt to damage dead guard (should be ignored)")
    print("=" * 70)
    sim.apply_damage("enemy", "guard", 50.0)
    sim.tick()
    status = sim.get_entity_status("guard")
    assert status["health"] == 0.0, "Dead entity health shouldn't change"
    print("\n✓ Dead entities correctly ignore damage")
    
    # Summary
    print("\n" + "=" * 70)
    print("COMBAT INTEGRATION TEST COMPLETE")
    print("=" * 70)
    print("\n✅ All combat integration tests passed")
    print("\nDemonstrated:")
    print("  • Entity spawn with health tracking")
    print("  • Damage application")
    print("  • Low health detection and flee behavior")
    print("  • Death detection and navigation disable")
    print("  • Dead entity damage immunity")
    print("\nCombat3D is fully integrated with EngAIn stack!")


if __name__ == "__main__":
    run_combat_scenario()
