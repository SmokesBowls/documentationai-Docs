# zonengine4d/zon4d/sim/spatial3d_adapter.py

"""
Unified Spatial3D Adapter
- Canonical Deep-Layer API (handle_delta, save_to_state)
- Convenience API (spawn_entity, get_entity, move_entity)
- All paths route through the same AP → MR → State pipeline
"""

import time
from typing import Dict, List, Any, Tuple

from spatial3d import Spatial3DStateView, Alert
from spatial3d_mr import step_spatial3d, SpatialAlert


class APViolation(Exception):
    pass


class Spatial3DStateViewAdapter(Spatial3DStateView):

    def __init__(self, state_slice=None):
        # canonical deep-layer state slice
        super().__init__(state_slice or {"entities": {}})

        # pending MR deltas
        self._mr_deltas: List[Dict[str, Any]] = []
        self._delta_counter = 0


    # ===============================================================
    # CANONICAL DEEP-LAYER INTERFACE (Pattern A)
    # ===============================================================

    def handle_delta(self, delta_type: str, payload: dict):
        """
        AP pre-checks → queue MR delta → return alerts
        """
        success, alerts = super().handle_delta(delta_type, payload)
        if not success:
            return False, alerts

        mr_delta = self._convert_to_mr(delta_type, payload)
        if mr_delta:
            self._mr_deltas.append(mr_delta)

        return True, alerts


    def physics_step(self, delta_time: float) -> List[Alert]:
        """
        Executes MR → applies AP → updates deep-layer state.
        """

        snapshot_in = {"spatial3d": self._state_slice}

        snapshot_out, accepted, mr_alerts = step_spatial3d(
            snapshot_in,
            self._mr_deltas,
            delta_time
        )

        # update state
        self._state_slice = snapshot_out["spatial3d"]

        # clear deltas
        self._mr_deltas.clear()

        # convert MR alerts → runtime alerts
        alerts = []
        for a in mr_alerts:
            alerts.append(Alert(
                level=a.level,
                step=0,
                message=f"[SPATIAL3D] {a.code}: {a.message}",
                tick=0,
                ts=time.time(),
                payload={"entity_ids": a.entity_ids}
            ))

        return alerts


    # ===============================================================
    # CONVENIENCE API (Pattern B)
    # ===============================================================

    def spawn_entity(self, entity_id, pos, radius=0.5, solid=True, tags=None, has_perceiver=False):
        """Convenience method - routes to handle_delta internally."""
        payload = {
            "entity_id": entity_id,
            "pos": pos,
            "radius": radius,
            "solid": solid,
            "tags": tags or [],
        }
        success, alerts = self.handle_delta("spatial3d/spawn", payload)
        return success

    def move_entity(self, entity_id, target_pos, speed=5.0):
        """Convenience method - routes to handle_delta internally."""
        payload = {
            "entity_id": entity_id,
            "target_pos": target_pos,
            "speed": speed,
        }
        return self.handle_delta("spatial3d/move", payload)

    def get_entity(self, entity_id: str) -> dict:
        """Query entity state."""
        return self._state_slice.get("entities", {}).get(entity_id, {})


    # ===============================================================
    # DELTA CONVERSION (Deep → MR)
    # ===============================================================

    def _convert_to_mr(self, deep_type: str, payload: dict):

        self._delta_counter += 1
        delta_id = f"spatial_{self._delta_counter}"

        if deep_type == "spatial3d/spawn":
            return {
                "id": delta_id,
                "type": "spatial/spawn",
                "payload": {
                    "entity_id": payload["entity_id"],
                    "entity": {
                        "pos": payload.get("pos", (0, 0, 0)),
                        "radius": payload.get("radius", 0.5),
                        "solid": payload.get("solid", True),
                        "tags": payload.get("tags", []),
                    },
                },
            }

        if deep_type == "spatial3d/move":
            return {
                "id": delta_id,
                "type": "spatial/apply_impulse",
                "payload": {
                    "entity_id": payload["entity_id"],
                    # MR kernel computes actual physics; this is enough
                    "impulse": (payload.get("speed", 5.0), 0, 0),
                    "mass": 1.0,
                },
            }

        return None
