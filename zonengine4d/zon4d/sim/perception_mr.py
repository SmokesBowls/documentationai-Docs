# sim/perception_mr.py
"""
PERCEPTION3D_MR: Pure functional perception kernel.
Deterministic, engine-agnostic, snapshot-in/snapshot-out.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional, Any
import math

Vec3 = Tuple[float, float, float]


@dataclass
class PerceptionEntity:
    """Entity data needed for perception calculations."""
    id: str
    pos: Vec3
    radius: float
    solid: bool
    tags: List[str]
    
    # Perception capabilities
    vision_range: float = 10.0
    vision_fov: float = 90.0  # degrees
    vision_height: float = 1.7  # eye height above position
    hearing_range: float = 15.0


@dataclass
class PerceptionWorld:
    """World state for perception calculations."""
    entities: Dict[str, PerceptionEntity] = field(default_factory=dict)
    perceivers: Dict[str, PerceptionEntity] = field(default_factory=dict)
    targets: Dict[str, PerceptionEntity] = field(default_factory=dict)
    
    obstacles: List[Tuple[Vec3, float]] = field(default_factory=list)
    sound_events: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class MemoryEntry:
    """Memory of a perceived entity."""
    entity_id: str
    last_seen_tick: int = 0
    last_heard_tick: int = 0
    last_known_pos: Vec3 = (0.0, 0.0, 0.0)
    certainty: float = 0.0  # 0.0-1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "last_seen_tick": self.last_seen_tick,
            "last_heard_tick": self.last_heard_tick,
            "last_known_pos": list(self.last_known_pos),
            "certainty": self.certainty,
        }


@dataclass
class PerceptionState:
    """Perception state for a single entity."""
    visible_now: Set[str] = field(default_factory=set)
    audible_now: Set[str] = field(default_factory=set)
    memories: Dict[str, MemoryEntry] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "visible_now": list(self.visible_now),
            "audible_now": list(self.audible_now),
            "memories": {mid: mem.to_dict() for mid, mem in self.memories.items()},
        }


@dataclass
class PerceptionDelta:
    """Perception event delta."""
    type: str  # "see", "lose_sight", "hear"
    perceiver_id: str
    target_id: str
    tick: int
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "perceiver_id": self.perceiver_id,
            "target_id": self.target_id,
            "tick": self.tick,
            "data": self.data,
        }


@dataclass
class PerceptionAlert:
    """Perception kernel alert."""
    level: str
    code: str
    message: str
    entity_ids: Tuple[str, ...] = field(default_factory=tuple)


# ===== PURE MATH FUNCTIONS =====

def vector_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vector_dot(a: Vec3, b: Vec3) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def vector_length(v: Vec3) -> float:
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])


def vector_normalize(v: Vec3) -> Vec3:
    length = vector_length(v)
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (v[0]/length, v[1]/length, v[2]/length)


def distance(a: Vec3, b: Vec3) -> float:
    """Euclidean distance."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def angle_between(v1: Vec3, v2: Vec3) -> float:
    """Angle between two vectors in degrees."""
    dot = vector_dot(v1, v2)
    len1 = vector_length(v1)
    len2 = vector_length(v2)
    
    if len1 == 0 or len2 == 0:
        return 0.0
    
    cos_angle = max(-1.0, min(1.0, dot / (len1 * len2)))
    return math.degrees(math.acos(cos_angle))


def line_of_sight(start: Vec3, end: Vec3, obstacles: List[Tuple[Vec3, float]]) -> bool:
    """
    Check if there's clear line of sight between two points.
    Simplified: checks if line segment intersects any obstacle sphere.
    """
    if start == end:
        return True
    
    dir_vec = vector_sub(end, start)
    dist = vector_length(dir_vec)
    
    if dist == 0:
        return True
    
    dir_norm = vector_normalize(dir_vec)
    
    # Check each obstacle
    for center, radius in obstacles:
        # Vector from start to sphere center
        oc = vector_sub(start, center)
        
        # Quadratic coefficients for ray-sphere intersection
        a = vector_dot(dir_norm, dir_norm)
        b = 2.0 * vector_dot(oc, dir_norm)
        c = vector_dot(oc, oc) - radius * radius
        
        discriminant = b * b - 4 * a * c
        
        if discriminant >= 0:
            sqrt_disc = math.sqrt(discriminant)
            t1 = (-b - sqrt_disc) / (2 * a)
            t2 = (-b + sqrt_disc) / (2 * a)
            
            # Check if intersection is between start and end
            if (0 <= t1 <= dist) or (0 <= t2 <= dist):
                return False
    
    return True


# ===== MAIN KERNEL FUNCTION =====

def step_perception(
    spatial_state: Dict[str, Any],
    perception_state: Dict[str, Any],
    current_tick: int,
    sound_events: List[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Pure functional perception kernel.
    
    Args:
        spatial_state: Spatial3D state snapshot
        perception_state: Current perception state
        current_tick: Current simulation tick
        sound_events: Sound events from audio system
        
    Returns:
        new_perception_state: Updated perception state
        deltas: Perception event deltas
        alerts: Kernel alerts
    """
    if sound_events is None:
        sound_events = []
    
    # Parse inputs
    world = _parse_world(spatial_state, sound_events)
    states = _parse_perception_state(perception_state)
    
    deltas: List[PerceptionDelta] = []
    alerts: List[PerceptionAlert] = []
    
    # Reset current perceptions
    for state in states.values():
        state.visible_now.clear()
        state.audible_now.clear()
    
    # Process each perceiver
    for perceiver_id, state in states.items():
        if perceiver_id not in world.entities:
            continue
        
        perceiver = world.entities[perceiver_id]
        
        # Vision checks
        for target_id, target in world.entities.items():
            if target_id == perceiver_id:
                continue
            
            # Check if target can be seen
            visible, certainty = _check_visibility(perceiver, target, world.obstacles)
            
            if visible:
                state.visible_now.add(target_id)
                
                # Update or create memory
                if target_id in state.memories:
                    mem = state.memories[target_id]
                    mem.last_seen_tick = current_tick
                    mem.last_known_pos = target.pos
                    mem.certainty = max(mem.certainty, certainty)
                else:
                    state.memories[target_id] = MemoryEntry(
                        entity_id=target_id,
                        last_seen_tick=current_tick,
                        last_known_pos=target.pos,
                        certainty=certainty,
                    )
                
                # Check if this is newly visible
                was_visible = target_id in perception_state.get(perceiver_id, {}).get("visible_now", [])
                if not was_visible:
                    deltas.append(PerceptionDelta(
                        type="see",
                        perceiver_id=perceiver_id,
                        target_id=target_id,
                        tick=current_tick,
                        data={
                            "certainty": certainty,
                            "distance": distance(perceiver.pos, target.pos),
                        }
                    ))
            else:
                # Check if just lost sight
                was_visible = target_id in perception_state.get(perceiver_id, {}).get("visible_now", [])
                if was_visible:
                    deltas.append(PerceptionDelta(
                        type="lose_sight",
                        perceiver_id=perceiver_id,
                        target_id=target_id,
                        tick=current_tick,
                        data={
                            "last_known_pos": list(target.pos),
                        }
                    ))
        
        # Hearing checks (simplified)
        for sound in world.sound_events:
            sound_pos = tuple(sound.get("pos", (0, 0, 0)))
            volume = sound.get("volume", 1.0)
            source_id = sound.get("source_id")
            
            # Check distance
            dist = distance(perceiver.pos, sound_pos)
            if dist <= perceiver.hearing_range:
                # Simple attenuation
                audible_volume = volume * (1.0 - (dist / perceiver.hearing_range))
                
                if audible_volume > 0.1:  # Hearing threshold
                    if source_id:
                        state.audible_now.add(source_id)
                        
                        # Update memory for source
                        if source_id in state.memories:
                            mem = state.memories[source_id]
                            mem.last_heard_tick = current_tick
                            # Update position if we can't see them
                            if current_tick - mem.last_seen_tick > 10:
                                mem.last_known_pos = sound_pos
                                mem.certainty = max(mem.certainty, audible_volume)
                        elif source_id in world.entities:
                            state.memories[source_id] = MemoryEntry(
                                entity_id=source_id,
                                last_heard_tick=current_tick,
                                last_known_pos=sound_pos,
                                certainty=audible_volume,
                            )
                        
                        deltas.append(PerceptionDelta(
                            type="hear",
                            perceiver_id=perceiver_id,
                            target_id=source_id,
                            tick=current_tick,
                            data={
                                "volume": audible_volume,
                                "sound_type": sound.get("type", "unknown"),
                            }
                        ))
        
        # Memory decay
        to_remove = []
        for target_id, memory in state.memories.items():
            ticks_since_seen = current_tick - memory.last_seen_tick
            ticks_since_heard = current_tick - memory.last_heard_tick
            
            if ticks_since_seen > 100 and ticks_since_heard > 100:  # Decay threshold
                to_remove.append(target_id)
        
        for target_id in to_remove:
            del state.memories[target_id]
            alerts.append(PerceptionAlert(
                level="INFO",
                code="MEMORY_FORGOTTEN",
                message=f"{perceiver_id} forgot about {target_id}",
                entity_ids=(perceiver_id, target_id),
            ))
    
    # Convert to output format
    new_state = _to_output_state(states)
    delta_dicts = [delta.to_dict() for delta in deltas]
    alert_dicts = [
        {
            "level": alert.level,
            "code": alert.code,
            "message": alert.message,
            "entity_ids": alert.entity_ids,
        }
        for alert in alerts
    ]
    
    return new_state, delta_dicts, alert_dicts


# ===== HELPER FUNCTIONS =====

def _parse_world(spatial_state: Dict[str, Any], sound_events: List[Dict[str, Any]]) -> PerceptionWorld:
    """Parse spatial state into perception world."""
    world = PerceptionWorld(sound_events=sound_events)
    
    entities_data = spatial_state.get("spatial3d", {}).get("entities", {})
    
    for eid, data in entities_data.items():
        # Create entity
        entity = PerceptionEntity(
            id=eid,
            pos=tuple(data["pos"]),
            radius=data.get("radius", 0.5),
            solid=data.get("solid", True),
            tags=data.get("tags", []),
            vision_range=data.get("vision_range", 10.0),
            vision_fov=data.get("vision_fov", 90.0),
            vision_height=data.get("vision_height", 1.7),
            hearing_range=data.get("hearing_range", 15.0),
        )
        
        world.entities[eid] = entity

        # Classify entity roles
        if "perceiver" in data.get("tags", []):
            world.perceivers[eid] = entity
        else:
            world.targets[eid] = entity
        
        # Add to obstacles if solid
        if data.get("solid", True) and "obstacle" in data.get("tags", []):
            world.obstacles.append((tuple(data["pos"]), data.get("radius", 0.5)))
    
    return world


def _parse_perception_state(perception_state: Dict[str, Any]) -> Dict[str, PerceptionState]:
    """Parse perception state."""
    states = {}
    
    for perceiver_id, data in perception_state.items():
        state = PerceptionState()
        
        # Parse visible now
        state.visible_now = set(data.get("visible_now", []))
        state.audible_now = set(data.get("audible_now", []))
        
        # Parse memories
        memories_data = data.get("memories", {})
        for target_id, mem_data in memories_data.items():
            state.memories[target_id] = MemoryEntry(
                entity_id=target_id,
                last_seen_tick=mem_data.get("last_seen_tick", 0),
                last_heard_tick=mem_data.get("last_heard_tick", 0),
                last_known_pos=tuple(mem_data.get("last_known_pos", (0, 0, 0))),
                certainty=mem_data.get("certainty", 0.0),
            )
        
        states[perceiver_id] = state
    
    return states


def _check_visibility(
    perceiver: PerceptionEntity,
    target: PerceptionEntity,
    obstacles: List[Tuple[Vec3, float]],
) -> Tuple[bool, float]:
    """
    Check if target is visible to perceiver.
    Returns (is_visible, certainty).

    OMNIVISION RULE:
    - If perceiver.forward is None → 360° vision (skip FOV test)
    """
    # Adjust for eye height
    eye_pos = (
        perceiver.pos[0],
        perceiver.pos[1] + perceiver.vision_height,
        perceiver.pos[2]
    )

    target_eye_pos = (
        target.pos[0],
        target.pos[1] + perceiver.vision_height,
        target.pos[2]
    )

    # Distance check
    dist = distance(eye_pos, target_eye_pos)
    if dist > perceiver.vision_range:
        return False, 0.0

    # FOV check — only when perceiver.forward exists
    if getattr(perceiver, "forward", None) is not None:
        to_target = vector_sub(target_eye_pos, eye_pos)
        angle = angle_between(perceiver.forward, to_target)
        if angle > perceiver.vision_fov / 2:
            return False, 0.0
    # else → omnivision: skip FOV entirely

    # Obstacle / LOS check
    if not line_of_sight(eye_pos, target_eye_pos, obstacles):
        return False, 0.0

    # Certainty calculation
    certainty = 1.0 - (dist / perceiver.vision_range)
    certainty = max(0.1, certainty)

    return True, certainty


def _to_output_state(states: Dict[str, PerceptionState]) -> Dict[str, Any]:
    """Convert PerceptionState dict to export format."""
    return {
        perceiver_id: state.to_dict()
        for perceiver_id, state in states.items()
    }



# ===== TEST FUNCTION =====

def test_perception_kernel():
    """Test the perception kernel."""
    print("Testing perception kernel...")
    
    # Create test spatial state
    spatial_state = {
        "spatial3d": {
            "entities": {
                "guard": {
                    "pos": [0, 0, 0],
                    "radius": 0.5,
                    "solid": True,
                    "tags": ["perceiver", "npc"],
                    "vision_range": 15.0,
                    "vision_fov": 120.0,
                },
                "player": {
                    "pos": [5, 0, 0],  # In front of guard
                    "radius": 0.5,
                    "solid": True,
                    "tags": ["player"],
                },
                "wall": {
                    "pos": [2.5, 0, 0],
                    "radius": 1.0,
                    "solid": True,
                    "tags": ["obstacle"],
                }
            }
        }
    }
    
    # Initial perception state
    perception_state = {
        "guard": {
            "visible_now": [],
            "audible_now": [],
            "memories": {},
        }
    }
    
    # Run perception step
    new_state, deltas, alerts = step_perception(
        spatial_state, perception_state, current_tick=1
    )
    
    print(f"Guard sees: {new_state.get('guard', {}).get('visible_now', [])}")
    print(f"Deltas: {len(deltas)}")
    for delta in deltas:
        print(f"  {delta['type']}: {delta['perceiver_id']} -> {delta['target_id']}")
    
    return new_state, deltas, alerts


if __name__ == "__main__":
    test_perception_kernel()
