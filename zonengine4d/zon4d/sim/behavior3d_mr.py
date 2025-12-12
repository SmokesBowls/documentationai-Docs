# behavior3d_mr.py
"""
Behavior3D MR Kernel
Pure mathematical core for agent intent, escalation, alertness,
and commitment curves.
"""

from dataclasses import dataclass

@dataclass
class BehaviorState:
    intent: float = 0.0        # 0.0 → 1.0
    alertness: float = 0.0     # 0.0 → 1.0
    threat: float = 0.0        # 0.0 → 1.0
    aggression: float = 0.0    # static trait
    caution: float = 0.0       # static trait
    persistence: float = 0.0   # static trait

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def update_behavior_mr(prev: BehaviorState, spatial_slice, perception_slice, nav_slice):
    """
    Compute new intent, alertness, threat based on world slices.
    Deterministic — no randomness.
    """

    intent = prev.intent
    alertness = prev.alertness
    threat = prev.threat

    # ---------------------------
    # Threat increases if player in LOS
    # ---------------------------
    if perception_slice.get("visible_entities"):
        threat += 0.15
    else:
        threat -= 0.05

    # ---------------------------
    # Alertness rises from threat & aggression
    # ---------------------------
    alertness += threat * 0.1 + prev.aggression * 0.05

    # ---------------------------
    # Intent rises when alertness rises AND target exists
    # ---------------------------
    target = perception_slice.get("focus_target")
    if target:
        intent += alertness * 0.12
    else:
        intent -= 0.08

    # Persistence slows down decay
    decay_factor = (1.0 - prev.persistence)

    # ---------------------------
    # Apply decay
    # ---------------------------
    alertness -= 0.04 * decay_factor
    threat -= 0.03 * decay_factor
    intent -= 0.05 * decay_factor

    # Clamp all values
    return BehaviorState(
        intent=clamp(intent, 0.0, 1.0),
        alertness=clamp(alertness, 0.0, 1.0),
        threat=clamp(threat, 0.0, 1.0),
        aggression=prev.aggression,
        caution=prev.caution,
        persistence=prev.persistence,
    )
