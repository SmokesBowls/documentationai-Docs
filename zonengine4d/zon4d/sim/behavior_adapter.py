#!/usr/bin/env python3
"""
behavior_adapter.py - Behavior3D Adapter Layer

Wraps behavior_mr kernel with state management and AP validation.
Integrates Spatial3D, Perception3D, Navigation3D into unified AI agent.
"""

import time
from typing import Dict, List, Tuple, Optional, Any

# Import base classes
try:
    from sim_imports import Alert, BaseStateView, Delta
except ImportError:
    class Alert:
        def __init__(self, level, step, message, tick, ts, payload=None):
            self.level = level
            self.step = step
            self.message = message
            self.tick = tick
            self.ts = ts
            self.payload = payload or {}
    
    class BaseStateView:
        DOMAIN = ""
        def __init__(self, state_slice: dict):
            self._state_slice = state_slice
        def save_to_state(self) -> dict:
            return self._state_slice
    
    class Delta:
        def __init__(self, id, type, payload, tags=None, priority=0):
            self.id = id
            self.type = type
            self.payload = payload
            self.tags = tags or []
            self.priority = priority

# Import mr kernel
from behavior_mr import (
    step_behavior, BehaviorState, BehaviorConfig, EntityState,
    PerceptionInput, BehaviorStateType, BehaviorAction
)


class BehaviorStateView(BaseStateView):
    """Adapter for Behavior3D subsystem."""
    
    DOMAIN = "behavior3d"
    
    def __init__(self, state_slice: dict = None):
        if state_slice is None:
            state_slice = {
                "entities": {},
                "tick": 0.0
            }
        
        super().__init__(state_slice)
        
        # Runtime state
        self._config = BehaviorConfig()
        self._spatial_snapshot = {}
        self._perception_snapshot = {}
        self._navigation_snapshot = {}
        self._delta_counter = 0
    
    # ========================================
    # INPUT LOADING
    # ========================================
    
    def set_spatial_state(self, spatial_snapshot: dict):
        """Load spatial state for behavior decisions."""
        self._spatial_snapshot = spatial_snapshot
    
    def set_perception_state(self, perception_snapshot: dict):
        """Load perception state."""
        self._perception_snapshot = perception_snapshot
    
    def set_navigation_state(self, navigation_snapshot: dict):
        """Load navigation state."""
        self._navigation_snapshot = navigation_snapshot
    
    # ========================================
    # BEHAVIOR STEP
    # ========================================
    
    def behavior_step(self, current_tick: float, delta_time: float) -> Tuple[List[Delta], List[Alert]]:
        """Execute behavior AI for all entities."""
        deltas = []
        alerts = []
        
        # Get spatial entities
        spatial_entities = self._spatial_snapshot.get("entities", {})
        
        # Process each entity with behavior
        for entity_id, behavior_data in list(self._state_slice.get("entities", {}).items()):
            # Get spatial state
            if entity_id not in spatial_entities:
                continue
            
            spatial_entity = spatial_entities[entity_id]
            entity_state = EntityState(
                position=tuple(spatial_entity.get("pos", [0, 0, 0])),
                health=spatial_entity.get("health", 1.0),
                tags=tuple(spatial_entity.get("tags", []))
            )
            
            # Get perception input
            perception_input = self._build_perception_input(entity_id)
            
            # Get current behavior state
            behavior_state = self._load_behavior_state(entity_id, behavior_data)
            
            # Call mr kernel
            try:
                new_behavior_state, actions = step_behavior(
                    behavior_state,
                    entity_state,
                    perception_input,
                    self._config,
                    current_tick,
                    delta_time
                )
                
                # Save updated behavior state
                self._save_behavior_state(entity_id, new_behavior_state)
                
                # Convert actions to deltas
                for action in actions:
                    delta = self._action_to_delta(action, current_tick)
                    if delta:
                        deltas.append(delta)
                
            except Exception as e:
                alerts.append(Alert(
                    level="ERROR",
                    step="behavior_kernel",
                    message=f"Behavior error for {entity_id}: {str(e)}",
                    tick=current_tick,
                    ts=time.time()
                ))
        
        return deltas, alerts
    
    # ========================================
    # STATE CONVERSION
    # ========================================
    
    def _load_behavior_state(self, entity_id: str, behavior_data: dict) -> BehaviorState:
        """Convert stored state to BehaviorState."""
        target_pos = behavior_data.get("target_position")
        last_pos = behavior_data.get("last_known_position")
        
        return BehaviorState(
            entity_id=entity_id,
            current_state=BehaviorStateType(behavior_data.get("current_state", "idle")),
            target_entity=behavior_data.get("target_entity"),
            target_position=tuple(target_pos) if target_pos else None,
            last_known_position=tuple(last_pos) if last_pos else None,
            state_enter_time=behavior_data.get("state_enter_time", 0.0),
            time_since_target_seen=behavior_data.get("time_since_target_seen", 0.0),
            patrol_index=behavior_data.get("patrol_index", 0),
            patrol_points=tuple(tuple(p) for p in behavior_data.get("patrol_points", [])),
            alert_level=behavior_data.get("alert_level", 0.0)
        )
    
    def _save_behavior_state(self, entity_id: str, behavior_state: BehaviorState):
        """Save BehaviorState to storage."""
        if "entities" not in self._state_slice:
            self._state_slice["entities"] = {}
        
        self._state_slice["entities"][entity_id] = {
            "current_state": behavior_state.current_state.value,
            "target_entity": behavior_state.target_entity,
            "target_position": list(behavior_state.target_position) if behavior_state.target_position else None,
            "last_known_position": list(behavior_state.last_known_position) if behavior_state.last_known_position else None,
            "state_enter_time": behavior_state.state_enter_time,
            "time_since_target_seen": behavior_state.time_since_target_seen,
            "patrol_index": behavior_state.patrol_index,
            "patrol_points": [list(p) for p in behavior_state.patrol_points],
            "alert_level": behavior_state.alert_level
        }
    
    def _build_perception_input(self, entity_id: str) -> PerceptionInput:
        """Build perception input from perception snapshot."""
        # Get memory for this entity from perception
        memories = self._perception_snapshot.get("memory", {}).get(entity_id, {})
        
        visible = []
        audible = []
        positions = {}
        
        for other_id, memory in memories.items():
            if memory.get("certainty", 0) > 0.5:
                visible.append(other_id)
                if "last_pos" in memory:
                    positions[other_id] = tuple(memory["last_pos"])
        
        return PerceptionInput(
            visible_entities=tuple(visible),
            audible_entities=tuple(audible),
            entity_positions=positions
        )
    
    def _action_to_delta(self, action: BehaviorAction, tick: float) -> Optional[Delta]:
        """Convert BehaviorAction to Delta."""
        self._delta_counter += 1
        delta_id = f"behavior_delta_{self._delta_counter}"
        
        if action.action_type == "move_to":
            # Request path from Navigation3D
            return Delta(
                id=delta_id,
                type="navigation3d/request_path",
                payload={
                    "entity_id": action.entity_id,
                    "start": self._spatial_snapshot.get("entities", {}).get(action.entity_id, {}).get("pos", [0,0,0]),
                    "goal": list(action.target_position) if action.target_position else [0,0,0],
                    "tick": tick
                },
                tags=["behavior"]
            )
        
        elif action.action_type == "attack":
            # Emit attack delta (for future Combat3D)
            return Delta(
                id=delta_id,
                type="behavior3d/attack",
                payload={
                    "attacker": action.entity_id,
                    "target": action.target_entity
                },
                tags=["behavior", "combat"]
            )
        
        elif action.action_type == "wait":
            # No delta needed for waiting
            return None
        
        elif action.action_type == "patrol":
            # Request path to patrol point
            return Delta(
                id=delta_id,
                type="navigation3d/request_path",
                payload={
                    "entity_id": action.entity_id,
                    "start": self._spatial_snapshot.get("entities", {}).get(action.entity_id, {}).get("pos", [0,0,0]),
                    "goal": list(action.target_position) if action.target_position else [0,0,0],
                    "tick": tick
                },
                tags=["behavior", "patrol"]
            )
        
        return None
    
    # ========================================
    # ENTITY MANAGEMENT
    # ========================================
    
    def add_behavior_entity(
        self,
        entity_id: str,
        initial_state: BehaviorStateType = BehaviorStateType.IDLE,
        patrol_points: List[Tuple[float, float, float]] = None
    ) -> Tuple[bool, List[Alert]]:
        """Add entity to behavior system."""
        if entity_id in self._state_slice.get("entities", {}):
            return False, [Alert(
                level="ERROR",
                step="add_behavior",
                message=f"Entity {entity_id} already has behavior",
                tick=self._state_slice.get("tick", 0),
                ts=time.time()
            )]
        
        behavior_state = BehaviorState(
            entity_id=entity_id,
            current_state=initial_state,
            patrol_points=tuple(patrol_points) if patrol_points else tuple()
        )
        
        self._save_behavior_state(entity_id, behavior_state)
        
        return True, []
    
    def get_behavior_state(self, entity_id: str) -> Optional[dict]:
        """Query behavior state for entity."""
        return self._state_slice.get("entities", {}).get(entity_id)


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    print("Testing behavior_adapter...")
    
    # Create adapter
    adapter = BehaviorStateView()
    
    # Add entity with patrol
    success, alerts = adapter.add_behavior_entity(
        "guard",
        initial_state=BehaviorStateType.PATROL,
        patrol_points=[(0, 0, 0), (10, 0, 0), (10, 10, 0)]
    )
    
    print(f"Added guard: {success}, alerts: {len(alerts)}")
    
    # Set dummy spatial state
    adapter.set_spatial_state({
        "entities": {
            "guard": {"pos": [0, 0, 0], "health": 1.0, "tags": ["npc"]},
            "player": {"pos": [15, 0, 0], "health": 1.0, "tags": ["player"]}
        }
    })
    
    # Set dummy perception (guard sees player)
    adapter.set_perception_state({
        "memory": {
            "guard": {
                "player": {
                    "certainty": 1.0,
                    "last_pos": [15, 0, 0]
                }
            }
        }
    })
    
    # Run behavior step
    deltas, alerts = adapter.behavior_step(current_tick=1.0, delta_time=0.016)
    
    print(f"Behavior step complete:")
    print(f"  Deltas: {len(deltas)}")
    for delta in deltas:
        print(f"    {delta.type}: {delta.payload}")
    print(f"  Alerts: {len(alerts)}")
    
    # Check state
    guard_behavior = adapter.get_behavior_state("guard")
    print(f"  Guard state: {guard_behavior['current_state']}")
    print(f"  Alert level: {guard_behavior['alert_level']:.2f}")
    
    print("\n✅ Adapter test complete")
