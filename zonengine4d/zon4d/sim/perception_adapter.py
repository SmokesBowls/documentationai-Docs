# sim/perception_adapter.py - FIXED IMPORTS
"""
PERCEPTION3D: Deep contract + adapter.
ZON4D-native perception system with AP constraints.
"""

import sys
import os

# Add the parent directory to the path so we can import ENGINALITY
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
from typing import Dict, List, Tuple, Optional, Any

from perception_mr import step_perception

try:
    from ENGINALITY.state.domain_views import BaseStateView
    from ENGINALITY.alerts import Alert
    from ENGINALITY.delta_types import Delta
    from ENGINALITY.tasks import Task
    ENGINALITY_AVAILABLE = True
except ImportError:
    # Fallback for testing
    ENGINALITY_AVAILABLE = False
    
    # Mock classes for testing
    from dataclasses import dataclass
    from typing import Any, Dict as TDict, List as TList
    
    @dataclass
    class Alert:
        level: str
        step: int
        message: str
        tick: int
        ts: float
        payload: TDict[str, Any] = None
        
        def __post_init__(self):
            if self.payload is None:
                self.payload = {}
    
    @dataclass 
    class Delta:
        id: str
        type: str
        payload: TDict[str, Any]
        tags: TList[str]
        priority: int
    
    @dataclass
    class Task:
        id: str
        type: str
        domain: str
        priority: int
        payload: TDict[str, Any]
    
    class BaseStateView:
        DOMAIN = ""
        def __init__(self, state_slice: dict):
            self._state_slice = state_slice.copy() if state_slice else {}
        
        def load_from_state(self, state_slice: dict):
            self._state_slice = state_slice.copy() if state_slice else {}
        
        def save_to_state(self) -> dict:
            return self._state_slice.copy()


class PerceptionStateView(BaseStateView):
    """
    Deep layer perception contract.
    Uses mr kernel via adapter pattern.
    Enforces AP constraints.
    """
    
    DOMAIN = "perception"
    
    def __init__(self, state_slice: dict):
        super().__init__(state_slice)
        self._spatial_state: Dict[str, Any] = {}
        self._sound_events: List[Dict[str, Any]] = []
    
    def set_spatial_state(self, spatial_state: dict):
        """Called by runtime to provide current spatial state."""
        self._spatial_state = spatial_state
    
    def handle_sound_event(self, sound_event: dict):
        """Queue sound event for next perception step."""
        self._sound_events.append(sound_event)
    
    def perception_step(self, current_tick: int) -> Tuple[List[Delta], List[Alert]]:
        """
        Execute perception step via mr kernel.
        
        Returns:
            deltas: Perception event deltas
            alerts: Runtime alerts
        """
        # Save old state for rollback
        old_state = self._state_slice.copy()
        
        # Run mr kernel
        try:
            new_state, mr_deltas, mr_alerts = step_perception(
                self._spatial_state,
                self._state_slice,
                current_tick,
                self._sound_events,
            )
        except Exception as e:
            # Kernel error - rollback
            self._state_slice = old_state
            raise APViolation(f"Perception kernel error: {e}")
        
        # Update state
        self._state_slice = new_state
        
        # Clear sound events
        self._sound_events.clear()
        
        # Validate AP constraints
        valid, msg = self._validate_perception_state(current_tick)
        if not valid:
            # Rollback on AP violation
            self._state_slice = old_state
            raise APViolation(f"Perception AP violation: {msg}")
        
        # Convert mr deltas to ZON4D deltas
        deltas = []
        for mr_delta in mr_deltas:
            deltas.append(Delta(
                id=f"perception_{mr_delta['type']}_{mr_delta['perceiver_id']}_{mr_delta['target_id']}@{current_tick}",
                type=f"perception/{mr_delta['type']}",
                payload={
                    "perceiver_id": mr_delta["perceiver_id"],
                    "target_id": mr_delta["target_id"],
                    "tick": mr_delta["tick"],
                    **mr_delta.get("data", {})
                },
                tags=["perception"],
                priority=10,  # Higher priority than spatial tasks
            ))
        
        # Convert mr alerts to runtime alerts
        alerts = []
        for mr_alert in mr_alerts:
            alerts.append(Alert(
                level=mr_alert["level"],
                step=0,
                message=f"[PERCEPTION] {mr_alert['code']}: {mr_alert['message']}",
                tick=current_tick,
                ts=time.time(),
                payload={"entity_ids": mr_alert["entity_ids"]}
            ))
        
        return deltas, alerts
    
    def get_visible_entities(self, perceiver_id: str) -> List[str]:
        """Query: Get entities currently visible to perceiver."""
        state = self._state_slice.get(perceiver_id, {})
        return state.get("visible_now", [])
    
    def get_audible_entities(self, perceiver_id: str) -> List[str]:
        """Query: Get entities currently audible to perceiver."""
        state = self._state_slice.get(perceiver_id, {})
        return state.get("audible_now", [])
    
    def get_memory(self, perceiver_id: str, target_id: str) -> Optional[Dict[str, Any]]:
        """Query: Get memory of target entity."""
        state = self._state_slice.get(perceiver_id, {})
        memories = state.get("memories", {})
        return memories.get(target_id)
    
    def get_all_memories(self, perceiver_id: str) -> Dict[str, Dict[str, Any]]:
        """Query: Get all memories for perceiver."""
        state = self._state_slice.get(perceiver_id, {})
        return state.get("memories", {}).copy()
    
    def _validate_perception_state(self, current_tick: int) -> Tuple[bool, str]:
        """
        AP constraint: Validate perception state consistency.
        
        Rules:
        1. All perceivers in perception state must exist in spatial state
        2. All remembered entities must exist in spatial state
        3. Memory timestamps cannot be in the future
        4. Certainty must be between 0 and 1
        """
        # Get spatial entities
        spatial_entities = self._spatial_state.get("spatial3d", {}).get("entities", {})
        
        for perceiver_id, state_data in self._state_slice.items():
            # Check perceiver exists
            if perceiver_id not in spatial_entities:
                return False, f"Perceiver {perceiver_id} not in spatial state"
            
            # Check visible entities exist
            for target_id in state_data.get("visible_now", []):
                if target_id not in spatial_entities:
                    return False, f"Visible entity {target_id} not in spatial state"
            
            # Check audible entities exist
            for target_id in state_data.get("audible_now", []):
                if target_id not in spatial_entities:
                    return False, f"Audible entity {target_id} not in spatial state"
            
            # Validate memories
            memories = state_data.get("memories", {})
            for target_id, memory in memories.items():
                # Target must exist
                if target_id not in spatial_entities:
                    return False, f"Remembered entity {target_id} not in spatial state"
                
                # Timestamp validation
                last_seen = memory.get("last_seen_tick", 0)
                last_heard = memory.get("last_heard_tick", 0)
                
                if last_seen < 0 or last_heard < 0:
                    return False, f"Negative timestamp in memory: {perceiver_id}->{target_id}"
                
                if last_seen > current_tick or last_heard > current_tick:
                    return False, f"Future timestamp in memory: {perceiver_id}->{target_id}"
                
                # Certainty validation
                certainty = memory.get("certainty", 0.0)
                if not 0.0 <= certainty <= 1.0:
                    return False, f"Invalid certainty {certainty} in memory: {perceiver_id}->{target_id}"
        
        return True, ""


class APViolation(Exception):
    """Signal AP constraint violation - triggers rollback."""
    pass


# ===== TASK FACADE =====

class PerceptionTaskFacade:
    """Task facade for perception operations."""
    
    @staticmethod
    def create_look_at_task(
        entity_id: str,
        target_id: str,
        duration: float = 2.0,
        priority: int = 20,
    ) -> Task:
        """Create a task to look at another entity."""
        return Task(
            id=f"perception_look_{entity_id}_at_{target_id}",
            type="perception/look_at",
            domain="PERCEPTION",
            priority=priority,
            payload={
                "entity_id": entity_id,
                "target_id": target_id,
                "duration": duration,
            }
        )