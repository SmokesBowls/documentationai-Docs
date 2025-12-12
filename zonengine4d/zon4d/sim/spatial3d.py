# zonengine4d/zon4d/sim/spatial3d.py
"""
SPATIAL3D: Deep Layer Contract + AP Constraints
Canonical ZON4D domain interface - other subsystems depend on this.
"""

import math
from typing import Dict, List, Tuple, Any, Optional


class Alert:
    """Minimal Alert class for standalone use"""
    def __init__(self, level: str, step: int, message: str, tick: int, ts: float, payload: dict = None):
        self.level = level
        self.step = step
        self.message = message
        self.tick = tick
        self.ts = ts
        self.payload = payload or {}


class BaseStateView:
    """Minimal BaseStateView for standalone use"""
    DOMAIN = ""
    
    def __init__(self, state_slice: dict):
        self._state_slice = state_slice
    
    def save_to_state(self) -> dict:
        return self._state_slice
    
    def load_from_state(self, state_slice: dict):
        self._state_slice = state_slice


class Spatial3DStateView(BaseStateView):
    """Canonical ZON4D StateView for Spatial3D."""
    
    DOMAIN = "spatial3d"
    
    def __init__(self, state_slice: dict):
        super().__init__(state_slice)
    
    def handle_delta(self, delta_type: str, payload: dict) -> Tuple[bool, List[Alert]]:
        """Handle spatial deltas with AP pre-validation."""
        alerts = []
        
        if delta_type == "spatial3d/spawn":
            valid, alert = self._validate_spawn(payload)
            if not valid:
                return False, [alert] if alert else []
            # Queue for mr kernel
            return self._queue_spawn(payload), alerts
            
        elif delta_type == "spatial3d/move":
            valid, alert = self._validate_move(payload)
            if not valid:
                return False, [alert] if alert else []
            return self._queue_move(payload), alerts
            
        return False, [Alert(
            level="WARNING",
            step=0,
            message=f"Unknown spatial delta: {delta_type}",
            tick=0,
            ts=0
        )]
    
    def physics_step(self, delta_time: float) -> List[Alert]:
        """Called by runtime each tick - delegates to mr kernel via adapter."""
        # This will be overridden by adapter
        return []
    
    # ===== AP Constraints =====
    
    @staticmethod
    def _validate_spawn(payload: dict) -> Tuple[bool, Optional[Alert]]:
        """AP: Validate spawn request."""
        entity_id = payload.get("entity_id")
        if not entity_id:
            return False, Alert(
                level="CRITICAL", step=0, message="Missing entity_id", tick=0, ts=0
            )
        
        # Check bounds, etc.
        return True, None
    
    @staticmethod
    def _validate_move(payload: dict) -> Tuple[bool, Optional[Alert]]:
        """AP: Validate movement request."""
        entity_id = payload.get("entity_id")
        if not entity_id:
            return False, Alert(
                level="CRITICAL", step=0, message="Missing entity_id", tick=0, ts=0
            )
        
        target = payload.get("target_pos")
        if not target or len(target) != 3:
            return False, Alert(
                level="CRITICAL", step=0, message="Invalid target_pos", tick=0, ts=0
            )
        
        return True, None
    
    # ===== Stub implementations for adapter override =====
    
    def _queue_spawn(self, payload: dict) -> bool:
        return True
    
    def _queue_move(self, payload: dict) -> bool:
        return True


# ===== AP CONSTRAINTS =====

def spatial3d_no_overlap_constraint(state_snapshot: dict) -> Tuple[bool, str]:
    """Canonical AP constraint: No two solid entities may overlap."""
    spatial = state_snapshot.get("spatial3d", {})
    entities = spatial.get("entities", {})
    
    entity_list = []
    for eid, data in entities.items():
        if data.get("solid", True):
            entity_list.append((eid, data))
    
    for i, (id1, e1) in enumerate(entity_list):
        pos1 = tuple(e1["pos"])
        r1 = e1["radius"]
        
        for j in range(i + 1, len(entity_list)):
            id2, e2 = entity_list[j]
            pos2 = tuple(e2["pos"])
            r2 = e2["radius"]
            
            dx = pos1[0] - pos2[0]
            dy = pos1[1] - pos2[1]
            dz = pos1[2] - pos2[2]
            dist_sq = dx*dx + dy*dy + dz*dz
            
            if dist_sq < (r1 + r2) * (r1 + r2):
                return False, f"Entities {id1} and {id2} overlap"
    
    return True, ""


def spatial3d_velocity_limit_constraint(state_snapshot: dict) -> Tuple[bool, str]:
    """Canonical AP constraint: Velocity limit."""
    spatial = state_snapshot.get("spatial3d", {})
    entities = spatial.get("entities", {})
    
    for eid, data in entities.items():
        vel = data.get("vel", (0, 0, 0))
        speed = math.sqrt(vel[0]*vel[0] + vel[1]*vel[1] + vel[2]*vel[2])
        if speed > 100.0:  # Max speed
            return False, f"Entity {eid} exceeds max speed: {speed}"
    
    return True, ""
