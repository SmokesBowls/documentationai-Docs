# combat3d_adapter.py
"""
Combat3D Adapter Layer

Imperative wrapper that:
- Queues damage deltas
- Calls pure MR kernel
- Converts MR alerts to engine-wide deltas
- Maintains mutable snapshot state

Follows the canonical EngAIn adapter pattern from Spatial3D/Perception3D.
"""

from collections import deque
from typing import Dict, Any, List, Tuple

from combat3d_mr import (
    CombatSnapshot,
    CombatEntity,
    DamageEvent,
    step_combat,
)


class Combat3DAdapter:
    """
    Adapter between engine delta system and pure Combat3D MR kernel.
    Handles queueing, state management, and alert translation.
    """
    
    def __init__(self):
        self.damage_queue = deque()
        self.snapshot = CombatSnapshot(entities={})

    def register_entity(self, entity_id: str, health: float, max_health: float):
        """
        Register a new entity in the combat system.
        Called by engine when loading or spawning an entity.
        
        Args:
            entity_id: Unique identifier for this entity
            health: Current health value
            max_health: Maximum health capacity
        """
        # Note: Mutates snapshot dict directly (adapter layer mutability)
        self.snapshot.entities[entity_id] = CombatEntity(
            entity_id=entity_id,
            health=health,
            max_health=max_health,
            alive=True,
        )

    def unregister_entity(self, entity_id: str):
        """Remove entity from combat tracking"""
        if entity_id in self.snapshot.entities:
            del self.snapshot.entities[entity_id]

    def handle_delta(self, delta_type: str, payload: Dict[str, Any]):
        """
        Queue incoming combat deltas for processing.
        Follows standard EngAIn delta handling pattern.
        
        Args:
            delta_type: Namespace/action identifier
            payload: Delta parameters
        """
        if delta_type == "combat3d/apply_damage":
            evt = DamageEvent(
                source_id=payload["source"],
                target_id=payload["target"],
                amount=payload["amount"],
                damage_type=payload.get("damage_type", "normal"),
            )
            self.damage_queue.append(evt)

    def tick(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Process all queued damage events and generate alert deltas.
        Called once per tick from the main EngAIn loop.
        
        Returns:
            List of (delta_type, payload) tuples for other subsystems
        """
        # Collect all damage for this tick
        damage_events = list(self.damage_queue)
        self.damage_queue.clear()

        # Call pure MR kernel
        output = step_combat(self.snapshot, damage_events)
        self.snapshot = output.new_snapshot

        # Convert MR alerts to engine-wide deltas
        deltas = []
        for (entity_id, alert_type) in output.alerts:
            if alert_type == "died":
                deltas.append(("behavior3d/set_flag", {
                    "entity": entity_id, 
                    "flag": "dead"
                }))
                deltas.append(("navigation3d/disable", {
                    "entity": entity_id
                }))
            elif alert_type == "low_health":
                deltas.append(("behavior3d/set_flag", {
                    "entity": entity_id, 
                    "flag": "low_health"
                }))

        return deltas

    def get_entity_health(self, entity_id: str) -> Tuple[float, float]:
        """
        Query current health state.
        
        Returns:
            (current_health, max_health) or (0.0, 0.0) if not found
        """
        entity = self.snapshot.entities.get(entity_id)
        if entity is None:
            return (0.0, 0.0)
        return (entity.health, entity.max_health)

    def is_alive(self, entity_id: str) -> bool:
        """Check if entity is alive"""
        entity = self.snapshot.entities.get(entity_id)
        return entity.alive if entity else False
