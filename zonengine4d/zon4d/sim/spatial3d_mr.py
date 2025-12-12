# zonengine4d/zon4d/sim/spatial3d_mr.py
"""
SPATIAL3D_MR: Mr Layer - Pure Functional Physics Kernel
Deterministic, renderer-agnostic, snapshot-in/snapshot-out.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Iterable, Optional, Any
import math

Vec3 = Tuple[float, float, float]

@dataclass
class SpatialEntity:
    id: str
    pos: Vec3 = (0.0, 0.0, 0.0)
    vel: Vec3 = (0.0, 0.0, 0.0)
    radius: float = 0.5
    solid: bool = True
    tags: List[str] = field(default_factory=list)

@dataclass
class SpatialWorld:
    entities: Dict[str, SpatialEntity] = field(default_factory=dict)
    bounds_min: Vec3 = (-100.0, -100.0, -100.0)
    bounds_max: Vec3 = (100.0, 100.0, 100.0)

@dataclass 
class SpatialAlert:
    level: str
    code: str
    message: str
    entity_ids: Tuple[str, ...] = field(default_factory=tuple)


def step_spatial3d(
    snapshot_in: Dict[str, Any],
    deltas: Iterable[Dict[str, Any]],
    dt: float,
    gravity: Vec3 = (0.0, -9.81, 0.0),
) -> Tuple[Dict[str, Any], List[str], List[SpatialAlert]]:
    """
    Pure functional physics kernel.
    Deterministic, no side effects, engine-agnostic.
    
    Returns:
        snapshot_out: Updated spatial state
        accepted_delta_ids: Deltas that were processed
        alerts: Physics events
    """
    # Parse input
    spatial_data = snapshot_in.get("spatial3d", {})
    world = _parse_world(spatial_data)
    alerts: List[SpatialAlert] = []
    accepted: List[str] = []
    
    # Apply deltas
    for delta in deltas:
        if not delta.get("type", "").startswith("spatial/"):
            continue
            
        d_id = delta.get("id", "")
        if _apply_delta(world, delta, alerts):
            accepted.append(d_id)
    
    # Physics integration
    _integrate_physics(world, dt, gravity, alerts)
    
    # Collision resolution
    _resolve_collisions(world, alerts)
    
    # Bounds enforcement
    _enforce_bounds(world, alerts)
    
    # Convert back to snapshot format
    snapshot_out = _to_snapshot(world, snapshot_in)
    return snapshot_out, accepted, alerts


# ===== Internal Implementation =====

def _parse_world(data: dict) -> SpatialWorld:
    """Parse snapshot data into world representation."""
    world = SpatialWorld()
    
    # Parse bounds
    bounds = data.get("bounds", {})
    world.bounds_min = _to_vec3(bounds.get("min", (-100, -100, -100)))
    world.bounds_max = _to_vec3(bounds.get("max", (100, 100, 100)))
    
    # Parse entities
    entities_data = data.get("entities", {})
    for eid, ent_data in entities_data.items():
        world.entities[eid] = SpatialEntity(
            id=eid,
            pos=_to_vec3(ent_data.get("pos", (0, 0, 0))),
            vel=_to_vec3(ent_data.get("vel", (0, 0, 0))),
            radius=float(ent_data.get("radius", 0.5)),
            solid=bool(ent_data.get("solid", True)),
            tags=list(ent_data.get("tags", [])),
        )
    
    return world

def _apply_delta(world: SpatialWorld, delta: dict, alerts: list) -> bool:
    """Apply a single delta to the world."""
    d_type = delta.get("type", "")
    payload = delta.get("payload", {})
    
    if d_type == "spatial/spawn":
        return _delta_spawn(world, payload, alerts)
    elif d_type == "spatial/despawn":
        return _delta_despawn(world, payload, alerts)
    elif d_type == "spatial/teleport":
        return _delta_teleport(world, payload, alerts)
    elif d_type == "spatial/set_velocity":
        return _delta_set_velocity(world, payload, alerts)
    elif d_type == "spatial/apply_impulse":
        return _delta_apply_impulse(world, payload, alerts)
    
    alerts.append(SpatialAlert("WARNING", "UNKNOWN_DELTA", f"Unknown delta: {d_type}"))
    return False

def _delta_spawn(world: SpatialWorld, payload: dict, alerts: list) -> bool:
    """Spawn new entity."""
    entity_id = payload.get("entity_id")
    entity_data = payload.get("entity", {})
    
    if entity_id in world.entities:
        alerts.append(SpatialAlert("WARNING", "ENTITY_EXISTS", f"Entity {entity_id} already exists"))
        return False
    
    world.entities[entity_id] = SpatialEntity(
        id=entity_id,
        pos=_to_vec3(entity_data.get("pos", (0, 0, 0))),
        vel=_to_vec3(entity_data.get("vel", (0, 0, 0))),
        radius=float(entity_data.get("radius", 0.5)),
        solid=bool(entity_data.get("solid", True)),
        tags=list(entity_data.get("tags", [])),
    )
    
    alerts.append(SpatialAlert("INFO", "ENTITY_SPAWNED", f"Spawned {entity_id}", (entity_id,)))
    return True

def _delta_despawn(world: SpatialWorld, payload: dict, alerts: list) -> bool:
    """Remove entity."""
    entity_id = payload.get("entity_id")
    
    if entity_id not in world.entities:
        alerts.append(SpatialAlert("WARNING", "ENTITY_NOT_FOUND", f"Entity {entity_id} not found"))
        return False
    
    del world.entities[entity_id]
    alerts.append(SpatialAlert("INFO", "ENTITY_DESPAWNED", f"Despawned {entity_id}", (entity_id,)))
    return True

def _delta_teleport(world: SpatialWorld, payload: dict, alerts: list) -> bool:
    """Instant position change."""
    entity_id = payload.get("entity_id")
    target_pos = payload.get("pos")
    
    if entity_id not in world.entities:
        alerts.append(SpatialAlert("WARNING", "ENTITY_NOT_FOUND", f"Entity {entity_id} not found"))
        return False
    
    world.entities[entity_id].pos = _to_vec3(target_pos)
    world.entities[entity_id].vel = (0.0, 0.0, 0.0)  # Stop on teleport
    return True

def _delta_set_velocity(world: SpatialWorld, payload: dict, alerts: list) -> bool:
    """Set entity velocity."""
    entity_id = payload.get("entity_id")
    velocity = payload.get("velocity")
    
    if entity_id not in world.entities:
        alerts.append(SpatialAlert("WARNING", "ENTITY_NOT_FOUND", f"Entity {entity_id} not found"))
        return False
    
    world.entities[entity_id].vel = _to_vec3(velocity)
    return True

def _delta_apply_impulse(world: SpatialWorld, payload: dict, alerts: list) -> bool:
    """Apply impulse to entity."""
    entity_id = payload.get("entity_id")
    impulse = payload.get("impulse")
    mass = payload.get("mass", 1.0)
    
    if entity_id not in world.entities:
        alerts.append(SpatialAlert("WARNING", "ENTITY_NOT_FOUND", f"Entity {entity_id} not found"))
        return False
    
    entity = world.entities[entity_id]
    imp = _to_vec3(impulse)
    
    # F = ma, so a = F/m, dv = a*dt (dt=1 for impulse)
    entity.vel = (
        entity.vel[0] + imp[0] / mass,
        entity.vel[1] + imp[1] / mass,
        entity.vel[2] + imp[2] / mass,
    )
    return True

def _integrate_physics(world: SpatialWorld, dt: float, gravity: Vec3, alerts: list):
    """Integrate velocity to position, apply gravity."""
    gx, gy, gz = gravity
    
    for entity in world.entities.values():
        # Apply gravity
        vx = entity.vel[0] + gx * dt
        vy = entity.vel[1] + gy * dt
        vz = entity.vel[2] + gz * dt
        
        # Damping
        vx *= 0.98
        vy *= 0.98
        vz *= 0.98
        
        # Clamp speed
        speed_sq = vx*vx + vy*vy + vz*vz
        if speed_sq > 100*100:
            speed = math.sqrt(speed_sq)
            scale = 100.0 / speed
            vx *= scale
            vy *= scale
            vz *= scale
        
        # Update position
        px = entity.pos[0] + vx * dt
        py = entity.pos[1] + vy * dt
        pz = entity.pos[2] + vz * dt
        
        entity.vel = (vx, vy, vz)
        entity.pos = (px, py, pz)

def _resolve_collisions(world: SpatialWorld, alerts: list):
    """Resolve collisions deterministically."""
    ids = sorted(world.entities.keys())
    
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a = world.entities[ids[i]]
            b = world.entities[ids[j]]
            
            if not (a.solid and b.solid):
                continue
            
            dx = b.pos[0] - a.pos[0]
            dy = b.pos[1] - a.pos[1]
            dz = b.pos[2] - a.pos[2]
            dist_sq = dx*dx + dy*dy + dz*dz
            min_dist = a.radius + b.radius
            
            if dist_sq < min_dist * min_dist:
                # Collision - push both apart
                dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.001
                overlap = min_dist - dist
                
                nx = dx / dist if dist > 0 else 1.0
                ny = dy / dist if dist > 0 else 0.0
                nz = dz / dist if dist > 0 else 0.0
                
                # Move both entities apart
                push = overlap * 0.5
                a.pos = (a.pos[0] - nx * push, a.pos[1] - ny * push, a.pos[2] - nz * push)
                b.pos = (b.pos[0] + nx * push, b.pos[1] + ny * push, b.pos[2] + nz * push)
                
                # Damp velocity
                a.vel = (a.vel[0] * 0.5, a.vel[1] * 0.5, a.vel[2] * 0.5)
                b.vel = (b.vel[0] * 0.5, b.vel[1] * 0.5, b.vel[2] * 0.5)
                
                alerts.append(SpatialAlert(
                    "INFO", "COLLISION_RESOLVED",
                    f"Resolved collision {a.id} ↔ {b.id}",
                    (a.id, b.id)
                ))

def _enforce_bounds(world: SpatialWorld, alerts: list):
    """Keep entities within world bounds."""
    xmin, ymin, zmin = world.bounds_min
    xmax, ymax, zmax = world.bounds_max
    
    for entity in world.entities.values():
        px, py, pz = entity.pos
        r = entity.radius
        
        # Clamp to bounds with padding for radius
        if px - r < xmin:
            px = xmin + r
            entity.vel = (0.0, entity.vel[1], entity.vel[2])
        elif px + r > xmax:
            px = xmax - r
            entity.vel = (0.0, entity.vel[1], entity.vel[2])
            
        if py - r < ymin:
            py = ymin + r
            entity.vel = (entity.vel[0], 0.0, entity.vel[2])
        elif py + r > ymax:
            py = ymax - r
            entity.vel = (entity.vel[0], 0.0, entity.vel[2])
            
        if pz - r < zmin:
            pz = zmin + r
            entity.vel = (entity.vel[0], entity.vel[1], 0.0)
        elif pz + r > zmax:
            pz = zmax - r
            entity.vel = (entity.vel[0], entity.vel[1], 0.0)
        
        entity.pos = (px, py, pz)

def _to_snapshot(world: SpatialWorld, base_snapshot: dict) -> dict:
    """Convert world back to snapshot format."""
    snapshot = dict(base_snapshot)
    spatial: Dict[str, Any] = dict(snapshot.get("spatial3d", {}))
    
    spatial["bounds"] = {
        "min": list(world.bounds_min),
        "max": list(world.bounds_max),
    }
    
    ent_dict = {}
    for eid, ent in world.entities.items():
        ent_dict[eid] = {
            "pos": list(ent.pos),
            "vel": list(ent.vel),
            "radius": ent.radius,
            "solid": ent.solid,
            "tags": ent.tags.copy(),
        }
    
    spatial["entities"] = ent_dict
    snapshot["spatial3d"] = spatial
    return snapshot

def _to_vec3(value: Any) -> Vec3:
    """Convert to Vec3 tuple."""
    try:
        x, y, z = value
        return float(x), float(y), float(z)
    except:
        return (0.0, 0.0, 0.0)
