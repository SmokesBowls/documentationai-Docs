# combat3d_mr.py
"""
Combat3D MR Kernel - Pure Functional Combat Logic

Pure snapshot-in/snapshot-out combat processing.
No side effects, no state mutation, no engine dependencies.
Handles damage application, death detection, and combat alerts.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass(frozen=True)
class CombatEntity:
    """Immutable combat state for a single entity"""
    entity_id: str
    health: float
    max_health: float
    alive: bool = True
    stagger_timer: float = 0.0
    invuln_timer: float = 0.0

    def apply_damage(self, amount: float) -> "CombatEntity":
        """Apply damage and return new combat entity state"""
        if not self.alive:
            return self

        new_health = max(0.0, self.health - amount)
        alive = new_health > 0.0

        return CombatEntity(
            entity_id=self.entity_id,
            health=new_health,
            max_health=self.max_health,
            alive=alive,
            stagger_timer=self.stagger_timer,
            invuln_timer=self.invuln_timer,
        )


@dataclass(frozen=True)
class DamageEvent:
    """Single damage application request"""
    source_id: str
    target_id: str
    amount: float
    damage_type: str = "normal"  # placeholder; MR doesn't care yet.


@dataclass(frozen=True)
class CombatSnapshot:
    """Complete immutable combat world state"""
    entities: dict  # entity_id -> CombatEntity


@dataclass(frozen=True)
class CombatOutput:
    """Result of combat step processing"""
    new_snapshot: CombatSnapshot
    alerts: List[Tuple[str, str]]  # (entity_id, alert_type)
    # examples: ("orc_12", "died"), ("player", "low_health")


def step_combat(snapshot: CombatSnapshot, damage_events: List[DamageEvent]) -> CombatOutput:
    """
    Process all damage events for this tick and generate alerts.
    
    Args:
        snapshot: Current combat world state
        damage_events: All damage to apply this tick
        
    Returns:
        CombatOutput with updated snapshot and combat alerts
    """
    alerts = []
    new_entities = dict(snapshot.entities)

    for evt in damage_events:
        target = new_entities.get(evt.target_id)
        if target is None:
            continue

        updated = target.apply_damage(evt.amount)
        new_entities[evt.target_id] = updated

        # Alerts
        if updated.alive is False and target.alive is True:
            alerts.append((evt.target_id, "died"))
        elif updated.health <= updated.max_health * 0.25:
            alerts.append((evt.target_id, "low_health"))

    return CombatOutput(
        new_snapshot=CombatSnapshot(entities=new_entities),
        alerts=alerts,
    )
