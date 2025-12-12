# zonengine4d/zon4d/sim/sim_imports.py
"""Central import manager for sim subsystems"""

import time
from typing import Dict, List, Tuple, Any, Optional

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
    def load_from_state(self, state_slice: dict):
        self._state_slice = state_slice

class Delta:
    def __init__(self, id, type, payload, tags=None, priority=0):
        self.id = id
        self.type = type
        self.payload = payload
        self.tags = tags or []
        self.priority = priority

class APViolation(Exception):
    pass

Vec3 = Tuple[float, float, float]
