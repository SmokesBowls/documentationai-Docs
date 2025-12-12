#!/usr/bin/env python3
"""
navigation_adapter.py - Navigation3D Deep/Domain Layer

The "deep" layer for Navigation3D subsystem.
Manages active path requests, integrates with Spatial3D, validates AP constraints.

Architecture:
- NavigationStateView: Deep contract (domain state)
- Calls navigation_mr kernel for pathfinding
- Validates AP constraints (entity existence, grid consistency)
- Emits deltas: path_request, path_ready, path_failed
"""

import time
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field

# Import from central sim_imports (when it exists)
try:
    from sim_imports import Alert, BaseStateView, Delta, APViolation
except ImportError:
    # Inline definitions for standalone testing
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
    
    class Delta:
        def __init__(self, id, type, payload, tags=None, priority=0):
            self.id = id
            self.type = type
            self.payload = payload
            self.tags = tags or []
            self.priority = priority
    
    class APViolation(Exception):
        pass

# Import navigation kernel
from navigation_mr import (
    NavGrid, PathResult, Vec3,
    find_path, raycast,
    create_empty_grid, add_obstacle_sphere,
    world_to_grid, grid_to_world
)


# ============================================================
# PATH REQUEST TRACKING
# ============================================================

@dataclass
class PathRequest:
    """Active path request."""
    entity_id: str
    start: Vec3
    goal: Vec3
    request_tick: int
    priority: int = 0
    allow_diagonal: bool = True


# ============================================================
# NAVIGATION STATE VIEW (Deep Contract)
# ============================================================

class NavigationStateView(BaseStateView):
    """Deep contract for Navigation3D domain.
    
    Manages:
    - Active path requests
    - Entity → path mappings
    - NavGrid construction from Spatial3D
    - Path caching
    - AP constraint validation
    """
    
    DOMAIN = "navigation3d"
    
    def __init__(self, state_slice: dict = None):
        if state_slice is None:
            state_slice = {
                "active_requests": {},      # entity_id → PathRequest
                "active_paths": {},          # entity_id → List[Vec3]
                "completed_paths": {},       # entity_id → PathResult
                "grid_resolution": 1.0,
                "grid_bounds_min": [-50.0, -10.0, -50.0],
                "grid_bounds_max": [50.0, 10.0, 50.0],
            }
        super().__init__(state_slice)
        
        # Runtime state (not persisted)
        self._nav_grid: Optional[NavGrid] = None
        self._spatial_snapshot: Optional[Dict] = None
        self._path_cache: Dict[Tuple[Vec3, Vec3], PathResult] = {}
        self._delta_counter = 0
    
    # ========================================
    # SPATIAL3D INTEGRATION
    # ========================================
    
    def update_obstacles_from_spatial(self, spatial_snapshot: Dict[str, Any]):
        """Rebuild NavGrid from Spatial3D state.
        
        Extracts entity positions/radii from spatial state and
        creates NavGrid with obstacles.
        """
        self._spatial_snapshot = spatial_snapshot
        
        # Get grid parameters
        resolution = self._state_slice["grid_resolution"]
        bounds_min = tuple(self._state_slice["grid_bounds_min"])
        bounds_max = tuple(self._state_slice["grid_bounds_max"])
        
        # Create empty grid
        grid = create_empty_grid(resolution, bounds_min, bounds_max)
        
        # Add obstacles from spatial entities
        entities = spatial_snapshot.get("spatial3d", {}).get("entities", {})
        
        for entity_id, entity_data in entities.items():
            # Only add solid entities as obstacles
            if not entity_data.get("solid", True):
                continue
            
            pos = tuple(entity_data.get("pos", [0, 0, 0]))
            radius = entity_data.get("radius", 0.5)
            
            # Add obstacle (creates new immutable grid)
            grid = add_obstacle_sphere(grid, pos, radius)
        
        self._nav_grid = grid
        
        # Clear path cache when obstacles change
        self._path_cache.clear()
    
    # ========================================
    # PATH REQUEST API
    # ========================================
    
    def request_path(
        self,
        entity_id: str,
        start: Vec3,
        goal: Vec3,
        current_tick: int,
        priority: int = 0,
        allow_diagonal: bool = True
    ):
        """Request a path for an entity.
        
        Creates PathRequest and adds to active requests.
        Will be processed in next navigation_step().
        """
        request = PathRequest(
            entity_id=entity_id,
            start=start,
            goal=goal,
            request_tick=current_tick,
            priority=priority,
            allow_diagonal=allow_diagonal
        )
        
        # Store request (convert to dict for persistence)
        self._state_slice["active_requests"][entity_id] = {
            "entity_id": entity_id,
            "start": list(start),
            "goal": list(goal),
            "request_tick": current_tick,
            "priority": priority,
            "allow_diagonal": allow_diagonal
        }
    
    def cancel_path(self, entity_id: str):
        """Cancel active path request for entity."""
        self._state_slice["active_requests"].pop(entity_id, None)
        self._state_slice["active_paths"].pop(entity_id, None)
        self._state_slice["completed_paths"].pop(entity_id, None)
    
    # ========================================
    # QUERY API
    # ========================================
    
    def get_active_path(self, entity_id: str) -> Optional[List[Vec3]]:
        """Get entity's active path."""
        path_data = self._state_slice["active_paths"].get(entity_id)
        if path_data:
            return [tuple(p) for p in path_data]
        return None
    
    def has_path_request(self, entity_id: str) -> bool:
        """Check if entity has active path request."""
        return entity_id in self._state_slice["active_requests"]
    
    def get_path_result(self, entity_id: str) -> Optional[PathResult]:
        """Get completed path result for entity."""
        result_data = self._state_slice["completed_paths"].get(entity_id)
        if result_data:
            return PathResult(
                success=result_data["success"],
                path=[tuple(p) for p in result_data["path"]],
                cost=result_data["cost"],
                nodes_explored=result_data["nodes_explored"]
            )
        return None
    
    # ========================================
    # STEP FUNCTION (Calls mr Kernel)
    # ========================================
    
    def navigation_step(self, current_tick: int) -> Tuple[List[Delta], List[Alert]]:
        """Process navigation requests and emit deltas.
        
        Core step function:
        1. Validate AP constraints
        2. Process active path requests
        3. Call navigation_mr kernel for pathfinding
        4. Emit path_ready or path_failed deltas
        5. Update state
        """
        deltas = []
        alerts = []
        
        # AP pre-validation
        valid, msg = self._validate_navigation_state(current_tick)
        if not valid:
            raise APViolation(f"Navigation AP violation: {msg}")
        
        # Process each active request
        requests_to_remove = []
        
        for entity_id, request_data in self._state_slice["active_requests"].items():
            # Reconstruct PathRequest
            request = PathRequest(
                entity_id=request_data["entity_id"],
                start=tuple(request_data["start"]),
                goal=tuple(request_data["goal"]),
                request_tick=request_data["request_tick"],
                priority=request_data.get("priority", 0),
                allow_diagonal=request_data.get("allow_diagonal", True)
            )
            
            # Check if NavGrid is ready
            if self._nav_grid is None:
                alerts.append(Alert(
                    level="warning",
                    step="navigation",
                    message=f"NavGrid not initialized for entity {entity_id}",
                    tick=current_tick,
                    ts=time.time()
                ))
                continue
            
            # Check cache
            cache_key = (request.start, request.goal)
            if cache_key in self._path_cache:
                result = self._path_cache[cache_key]
            else:
                # Call mr kernel for pathfinding
                result = find_path(
                    request.start,
                    request.goal,
                    self._nav_grid,
                    allow_diagonal=request.allow_diagonal
                )
                
                # Cache result
                self._path_cache[cache_key] = result
            
            # Store result
            self._state_slice["completed_paths"][entity_id] = {
                "success": result.success,
                "path": [list(p) for p in result.path],
                "cost": result.cost,
                "nodes_explored": result.nodes_explored
            }
            
            # Emit delta
            if result.success:
                # Store active path
                self._state_slice["active_paths"][entity_id] = [list(p) for p in result.path]
                
                # Emit path_ready delta
                delta = Delta(
                    id=f"nav_{self._delta_counter}",
                    type="navigation3d/path_ready",
                    payload={
                        "entity_id": entity_id,
                        "path": [list(p) for p in result.path],
                        "cost": result.cost,
                        "waypoints": len(result.path)
                    },
                    tags=["navigation", entity_id],
                    priority=request.priority
                )
                deltas.append(delta)
                self._delta_counter += 1
                
                alerts.append(Alert(
                    level="info",
                    step="navigation",
                    message=f"Path found for {entity_id}: {len(result.path)} waypoints, cost {result.cost:.2f}",
                    tick=current_tick,
                    ts=time.time(),
                    payload={"nodes_explored": result.nodes_explored}
                ))
            else:
                # Emit path_failed delta
                delta = Delta(
                    id=f"nav_{self._delta_counter}",
                    type="navigation3d/path_failed",
                    payload={
                        "entity_id": entity_id,
                        "start": list(request.start),
                        "goal": list(request.goal),
                        "reason": "no_path_found"
                    },
                    tags=["navigation", entity_id],
                    priority=request.priority
                )
                deltas.append(delta)
                self._delta_counter += 1
                
                alerts.append(Alert(
                    level="warning",
                    step="navigation",
                    message=f"No path found for {entity_id}",
                    tick=current_tick,
                    ts=time.time()
                ))
            
            # Mark request as processed
            requests_to_remove.append(entity_id)
        
        # Remove processed requests
        for entity_id in requests_to_remove:
            self._state_slice["active_requests"].pop(entity_id, None)
        
        return deltas, alerts
    
    # ========================================
    # AP CONSTRAINT VALIDATION
    # ========================================
    
    def _validate_navigation_state(self, current_tick: int) -> Tuple[bool, str]:
        """Validate AP constraints for navigation state.
        
        Constraints:
        1. All entities with path requests must exist in spatial state
        2. Grid bounds must be valid
        3. Request ticks must not be in future
        """
        # Check spatial snapshot exists
        if self._spatial_snapshot is None and len(self._state_slice["active_requests"]) > 0:
            return False, "No spatial snapshot available for navigation validation"
        
        # Validate each active request
        if self._spatial_snapshot:
            spatial_entities = self._spatial_snapshot.get("spatial3d", {}).get("entities", {})
            
            for entity_id, request_data in self._state_slice["active_requests"].items():
                # Check entity exists in spatial state
                if entity_id not in spatial_entities:
                    return False, f"Entity {entity_id} has path request but not in spatial state"
                
                # Check request tick
                if request_data["request_tick"] > current_tick:
                    return False, f"Entity {entity_id} has future request tick"
        
        # Validate grid bounds
        bounds_min = self._state_slice["grid_bounds_min"]
        bounds_max = self._state_slice["grid_bounds_max"]
        
        if not all(bounds_max[i] > bounds_min[i] for i in range(3)):
            return False, "Invalid grid bounds (max must be > min)"
        
        return True, ""


# ============================================================
# AP CONSISTENCY CONSTRAINT (Global)
# ============================================================

def navigation_consistency_constraint(
    nav_snapshot: Dict[str, Any],
    spatial_snapshot: Dict[str, Any],
    current_tick: int
) -> Tuple[bool, str]:
    """Global AP constraint for navigation consistency.
    
    Validates that navigation state is consistent with spatial state.
    Used by ZON4D kernel for rollback decisions.
    """
    # Extract entities with active paths
    active_paths = nav_snapshot.get("active_paths", {})
    
    # Extract spatial entities
    spatial_entities = spatial_snapshot.get("spatial3d", {}).get("entities", {})
    
    # Check all entities with paths exist in spatial
    for entity_id in active_paths.keys():
        if entity_id not in spatial_entities:
            return False, f"Entity {entity_id} has active path but not in spatial state"
    
    # Check all path requests reference existing entities
    active_requests = nav_snapshot.get("active_requests", {})
    for entity_id in active_requests.keys():
        if entity_id not in spatial_entities:
            return False, f"Entity {entity_id} has path request but not in spatial state"
    
    return True, ""


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    print("Testing navigation_adapter...")
    print()
    
    # Create navigation view
    nav_view = NavigationStateView()
    
    # Create mock spatial snapshot
    spatial_snapshot = {
        "spatial3d": {
            "entities": {
                "guard": {
                    "pos": [0, 0, 0],
                    "radius": 0.5,
                    "solid": True,
                },
                "player": {
                    "pos": [10, 0, 0],
                    "radius": 0.5,
                    "solid": True,
                },
                "wall": {
                    "pos": [5, 0, 0],
                    "radius": 1.5,
                    "solid": True,
                }
            }
        }
    }
    
    # Update obstacles from spatial
    print("TEST 1: Update NavGrid from spatial state")
    nav_view.update_obstacles_from_spatial(spatial_snapshot)
    print(f"  NavGrid created: {nav_view._nav_grid is not None}")
    print(f"  Walkable cells: {len(nav_view._nav_grid.walkable_cells)}")
    print()
    
    # Request path
    print("TEST 2: Request path (guard → player, around wall)")
    nav_view.request_path(
        entity_id="guard",
        start=(0.5, 0.5, 0.5),
        goal=(9.5, 0.5, 0.5),
        current_tick=1
    )
    print(f"  Request created: {nav_view.has_path_request('guard')}")
    print()
    
    # Process navigation step
    print("TEST 3: Process navigation step")
    deltas, alerts = nav_view.navigation_step(current_tick=1)
    print(f"  Deltas: {len(deltas)}")
    print(f"  Alerts: {len(alerts)}")
    
    if deltas:
        delta = deltas[0]
        print(f"  Delta type: {delta.type}")
        print(f"  Waypoints: {delta.payload.get('waypoints', 0)}")
        print(f"  Cost: {delta.payload.get('cost', 0):.2f}")
    print()
    
    # Query active path
    print("TEST 4: Query active path")
    path = nav_view.get_active_path("guard")
    if path:
        print(f"  Path found: {len(path)} waypoints")
        print(f"  First: {path[0]}")
        print(f"  Last: {path[-1]}")
    print()
    
    # Test AP constraint violation
    print("TEST 5: AP constraint validation (entity doesn't exist)")
    nav_view.request_path(
        entity_id="ghost",  # Not in spatial state
        start=(0, 0, 0),
        goal=(5, 0, 0),
        current_tick=2
    )
    
    try:
        deltas, alerts = nav_view.navigation_step(current_tick=2)
        print("  ❌ Should have raised APViolation")
    except APViolation as e:
        print(f"  ✅ AP constraint caught: {str(e)[:60]}...")
    print()
    
    # Test impossible path
    print("TEST 6: Impossible path (blocked start)")
    nav_view.cancel_path("ghost")
    nav_view.request_path(
        entity_id="wall",  # Wall position is blocked
        start=(5.0, 0.0, 0.0),
        goal=(10.0, 0.0, 0.0),
        current_tick=3
    )
    
    deltas, alerts = nav_view.navigation_step(current_tick=3)
    if deltas:
        delta = deltas[0]
        print(f"  Delta type: {delta.type}")
        print(f"  Reason: {delta.payload.get('reason', 'unknown')}")
    print()
    
    print("✅ navigation_adapter tests complete")
