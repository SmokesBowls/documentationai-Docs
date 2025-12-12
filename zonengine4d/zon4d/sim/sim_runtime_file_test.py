#!/usr/bin/env python3
"""
sim_runtime_file_test.py - Simplified File-Based Test Version

This version writes snapshots to a file instead of stdout.
Use this to test the rendering logic before dealing with subprocess complexity.

Usage:
  Terminal 1: python3 sim_runtime_file_test.py
  Terminal 2: Open Godot scene, watch entities update
"""

import json
import time
import os
from spatial3d_adapter import Spatial3DStateViewAdapter
from perception_adapter import PerceptionStateView
from navigation_adapter import NavigationStateView
from combat3d_adapter import Combat3DAdapter


SNAPSHOT_FILE = "/tmp/engain_snapshot.json"
COMMAND_FILE = "/tmp/engain_command.json"


class EngAInFileTest:
    """File-based test version of EngAIn runtime"""
    
    def __init__(self):
        self.setup_spatial()
        self.setup_perception()
        self.setup_navigation()
        self.setup_combat()
        
        self.behavior_states = {}
        self.behavior_flags = {}
        self.tick_count = 0
        
        print("[FILE TEST] EngAIn simulation initialized")
    
    def setup_spatial(self):
        spatial_state = {
            "entities": {},
            "gravity": [0.0, 0.0, 0.0],
            "drag": 0.0,
            "static_entities": [],
            "perceivers": []
        }
        self.spatial = Spatial3DStateViewAdapter(state_slice=spatial_state)
    
    def setup_perception(self):
        self.perception = PerceptionStateView(state_slice={})
    
    def setup_navigation(self):
        self.navigation = NavigationStateView()
    
    def setup_combat(self):
        self.combat = Combat3DAdapter()
    
    def spawn_entity(self, entity_id, pos, radius=0.5, solid=True, tags=None,
                     perceiver=False, health=100.0, max_health=100.0):
        if tags is None:
            tags = []
        
        spawn_data = {
            "entity_id": entity_id,
            "pos": pos,
            "radius": radius,
            "solid": solid,
            "tags": tags,
            "components": ["perceiver"] if perceiver else [],
            "mass": 1000.0,  # Heavy mass = static (won't move)
            "static": True   # Explicitly mark as static
        }
        
        if perceiver:
            spawn_data["perceiver"] = {
                "vision_range": 50.0,
                "fov": 180.0,
                "height": 1.8
            }
            spatial_state = self.spatial.save_to_state()
            if "perceivers" not in spatial_state:
                spatial_state["perceivers"] = []
            spatial_state["perceivers"].append(entity_id)
        
        success, alerts = self.spatial.handle_delta("spatial3d/spawn", spawn_data)
        
        if success:
            self.combat.register_entity(entity_id, health=health, max_health=max_health)
            self.behavior_states[entity_id] = "idle"
            self.behavior_flags[entity_id] = set()
            print(f"[SPAWN] {entity_id} at {pos} with {health}/{max_health} HP")
        
        return success
    
    def tick(self, delta_time=0.016):
        self.tick_count += 1
        
        # Physics
        self.spatial.physics_step(delta_time=delta_time)
        
        # Perception
        spatial_state = self.spatial.save_to_state()
        self.perception.set_spatial_state({"spatial3d": spatial_state})
        try:
            self.perception.perception_step(current_tick=self.tick_count)
        except:
            pass
        
        # Navigation
        self.navigation.update_obstacles_from_spatial({"spatial3d": spatial_state})
        self.navigation.navigation_step(current_tick=self.tick_count)
        
        # Combat
        combat_deltas = self.combat.tick()
        for delta_type, payload in combat_deltas:
            self.route_delta(delta_type, payload)
        
        # Behavior
        self.behavior_step()
    
    def route_delta(self, delta_type, payload):
        if delta_type == "behavior3d/set_flag":
            entity_id = payload["entity"]
            flag = payload["flag"]
            if entity_id not in self.behavior_flags:
                self.behavior_flags[entity_id] = set()
            self.behavior_flags[entity_id].add(flag)
            
        elif delta_type == "navigation3d/disable":
            entity_id = payload["entity"]
            nav_state = self.navigation.save_to_state()
            if "active_paths" in nav_state and entity_id in nav_state["active_paths"]:
                del nav_state["active_paths"][entity_id]
    
    def behavior_step(self):
        for entity_id, state in list(self.behavior_states.items()):
            flags = self.behavior_flags.get(entity_id, set())
            
            if "dead" in flags:
                if state != "dead":
                    self.behavior_states[entity_id] = "dead"
                    print(f"[BEHAVIOR] {entity_id} → dead")
                continue
            
            if "low_health" in flags and state != "fleeing":
                self.behavior_states[entity_id] = "fleeing"
                print(f"[BEHAVIOR] {entity_id} → fleeing")
                continue
    
    def get_world_snapshot(self):
        snapshot = {
            "tick": self.tick_count,
            "entities": {}
        }
        
        spatial_state = self.spatial.save_to_state()
        entities = spatial_state.get("entities", {})
        
        for entity_id, entity_data in entities.items():
            snapshot["entities"][entity_id] = {
                "pos": entity_data.get("pos", [0, 0, 0]),
                "vel": entity_data.get("vel", [0, 0, 0]),
                "radius": entity_data.get("radius", 0.5),
                "tags": entity_data.get("tags", []),
                "health": self.combat.get_entity_health(entity_id)[0],
                "max_health": self.combat.get_entity_health(entity_id)[1],
                "alive": self.combat.is_alive(entity_id),
                "state": self.behavior_states.get(entity_id, "idle"),
                "flags": list(self.behavior_flags.get(entity_id, set()))
            }
        
        return snapshot
    
    def write_snapshot_to_file(self):
        """Write current snapshot to file for Godot to read (atomic write)"""
        snapshot = self.get_world_snapshot()
        
        # Write to temp file first, then atomic rename
        temp_file = SNAPSHOT_FILE + ".tmp"
        with open(temp_file, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        # Atomic rename (prevents Godot from reading partial file)
        os.replace(temp_file, SNAPSHOT_FILE)
    
    def read_command_from_file(self):
        """Read command file if it exists, then delete it"""
        if not os.path.exists(COMMAND_FILE):
            return None
        
        try:
            with open(COMMAND_FILE, 'r') as f:
                command = json.load(f)
            os.remove(COMMAND_FILE)
            return command
        except:
            return None
    
    def handle_command(self, command):
        """Process command from Godot"""
        cmd_type = command.get("type")
        
        if cmd_type == "attack":
            source = command.get("source", "unknown")
            target = command.get("target", "unknown")
            damage = command.get("damage", 25.0)
            
            print(f"\n[COMMAND] {source} attacks {target} for {damage} damage")
            self.combat.handle_delta("combat3d/apply_damage", {
                "source": source,
                "target": target,
                "amount": damage
            })
    
    def run_loop(self):
        """Main loop - tick and write snapshots"""
        print(f"\n[FILE TEST] Writing snapshots to: {SNAPSHOT_FILE}")
        print(f"[FILE TEST] Reading commands from: {COMMAND_FILE}")
        print("\nPress Ctrl+C to stop\n")
        
        tick_rate = 60  # 60 ticks per second
        tick_interval = 1.0 / tick_rate
        
        try:
            while True:
                start_time = time.time()
                
                # Check for commands
                command = self.read_command_from_file()
                if command:
                    self.handle_command(command)
                
                # Advance simulation
                self.tick()
                
                # Write snapshot
                self.write_snapshot_to_file()
                
                # Status every 60 ticks
                if self.tick_count % 60 == 0:
                    print(f"[TICK {self.tick_count}] Snapshot written")
                
                # Sleep to maintain tick rate
                elapsed = time.time() - start_time
                sleep_time = max(0, tick_interval - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n[FILE TEST] Shutting down...")


def main():
    # Create runtime
    runtime = EngAInFileTest()
    
    # Spawn test scene
    print("\n=== Spawning Test Scene ===")
    runtime.spawn_entity("guard", pos=[-3, 0, 0], perceiver=True, 
                        health=100.0, max_health=100.0)
    runtime.spawn_entity("enemy", pos=[3, 0, 0], 
                        health=50.0, max_health=50.0)
    runtime.spawn_entity("wall", pos=[0, 0, 0], radius=2.0)
    
    print("\n=== Test Commands ===")
    print("To test from terminal:")
    print('echo \'{"type":"attack","source":"enemy","target":"guard","damage":25}\' > /tmp/engain_command.json')
    print()
    
    # Run loop
    runtime.run_loop()


if __name__ == "__main__":
    main()
