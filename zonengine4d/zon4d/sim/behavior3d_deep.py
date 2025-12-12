# behavior3d_deep.py
"""
Behavior3D Deep Contract Layer
- Wraps MR kernel
- Executes AP constraints
- Emits behavior deltas
"""

from dataclasses import dataclass
from behavior3d_mr import BehaviorState, update_behavior_mr

@dataclass
class BehaviorDelta:
    domain: str
    type: str
    agent_id: str
    payload: dict

class Behavior3DContract:
    DOMAIN = "behavior3d"

    def __init__(self, state_dict):
        self.state = {}
        for aid, data in state_dict.get("agents", {}).items():
            self.state[aid] = BehaviorState(
                intent=data.get("intent", 0.0),
                alertness=data.get("alertness", 0.0),
                threat=data.get("threat", 0.0),
                aggression=data.get("aggression", 0.0),
                caution=data.get("caution", 0.0),
                persistence=data.get("persistence", 0.0),
            )

    # ---------------------------
    # AP Constraints
    # ---------------------------
    def ap_check(self, prev: BehaviorState, new: BehaviorState):
        alerts = []

        # Alert: intent grows too fast
        if (new.intent - prev.intent) > 0.25:
            alerts.append(("behavior3d/intent_spike", new.intent))

        # Alert: threat cannot jump if no LOS
        if new.threat > prev.threat and new.threat > 0.8:
            alerts.append(("behavior3d/threat_high", new.threat))

        return alerts

    # ---------------------------
    # Delta creation
    # ---------------------------
    def derive_deltas(self, aid: str, prev: BehaviorState, new: BehaviorState):
        deltas = []

        # High intent triggers navigation path request
        if new.intent > 0.7:
            deltas.append(BehaviorDelta(
                domain="behavior3d",
                type="navigation3d/request_path",
                agent_id=aid,
                payload={"reason": "high_intent"},
            ))

        # High alertness triggers perception focus
        if new.alertness > 0.6:
            deltas.append(BehaviorDelta(
                domain="behavior3d",
                type="perception3d/focus",
                agent_id=aid,
                payload={"mode": "threat_scan"},
            ))

        return deltas

    # ---------------------------
    # Main step
    # ---------------------------
    def step(self, agent_id, spatial_slice, perception_slice, nav_slice):
        prev = self.state[agent_id]
        new = update_behavior_mr(prev, spatial_slice, perception_slice, nav_slice)

        alerts = self.ap_check(prev, new)
        deltas = self.derive_deltas(agent_id, prev, new)

        self.state[agent_id] = new
        return deltas, alerts
