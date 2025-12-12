#!/usr/bin/env python3
"""
navigation_mr.py - Pure Functional Navigation Kernel

The "mr" (mathematics/rules) kernel for Navigation3D.
Pure functional pathfinding: no state, no side effects, deterministic.

Snapshot-in → path-out architecture:
- NavGrid: Immutable grid data (resolution, bounds, walkable cells)
- find_path(): A* pathfinding over grid
- raycast(): Grid-based line-of-sight check

Portable to C++/Rust/GDExtension.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Set, Optional, Dict
import heapq
import math

# Type aliases
Vec3 = Tuple[float, float, float]
GridCell = Tuple[int, int, int]

# ============================================================
# IMMUTABLE DATA STRUCTURES
# ============================================================

@dataclass(frozen=True)
class NavGrid:
    """Immutable navigation grid.
    
    Represents a 3D grid where each cell can be walkable or blocked.
    Used for pathfinding and collision avoidance.
    """
    resolution: float  # Size of each grid cell in world units
    bounds_min: Vec3   # World-space minimum bounds
    bounds_max: Vec3   # World-space maximum bounds
    walkable_cells: frozenset  # frozenset of GridCell tuples
    
    def __post_init__(self):
        # Convert set to frozenset if needed (for immutability)
        if not isinstance(self.walkable_cells, frozenset):
            object.__setattr__(self, 'walkable_cells', frozenset(self.walkable_cells))


@dataclass
class PathResult:
    """Result of a pathfinding query."""
    success: bool
    path: List[Vec3]  # World-space waypoints
    cost: float
    nodes_explored: int


# ============================================================
# GRID COORDINATE CONVERSION
# ============================================================

def world_to_grid(pos: Vec3, resolution: float, bounds_min: Vec3) -> GridCell:
    """Convert world-space position to grid cell coordinates."""
    x = int((pos[0] - bounds_min[0]) / resolution)
    y = int((pos[1] - bounds_min[1]) / resolution)
    z = int((pos[2] - bounds_min[2]) / resolution)
    return (x, y, z)


def grid_to_world(cell: GridCell, resolution: float, bounds_min: Vec3) -> Vec3:
    """Convert grid cell to world-space position (cell center)."""
    x = bounds_min[0] + (cell[0] + 0.5) * resolution
    y = bounds_min[1] + (cell[1] + 0.5) * resolution
    z = bounds_min[2] + (cell[2] + 0.5) * resolution
    return (x, y, z)


def is_in_bounds(cell: GridCell, grid: NavGrid) -> bool:
    """Check if grid cell is within grid bounds."""
    gx, gy, gz = cell
    
    # Calculate grid dimensions
    dims_x = int((grid.bounds_max[0] - grid.bounds_min[0]) / grid.resolution)
    dims_y = int((grid.bounds_max[1] - grid.bounds_min[1]) / grid.resolution)
    dims_z = int((grid.bounds_max[2] - grid.bounds_min[2]) / grid.resolution)
    
    return (0 <= gx < dims_x and 
            0 <= gy < dims_y and 
            0 <= gz < dims_z)


# ============================================================
# DISTANCE HEURISTICS
# ============================================================

def manhattan_distance(a: GridCell, b: GridCell) -> float:
    """Manhattan distance between two grid cells."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def euclidean_distance(a: GridCell, b: GridCell) -> float:
    """Euclidean distance between two grid cells."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)


# ============================================================
# NEIGHBOR GENERATION
# ============================================================

def get_neighbors_6way(cell: GridCell) -> List[GridCell]:
    """Get 6 orthogonal neighbors (N/S/E/W/Up/Down)."""
    x, y, z = cell
    return [
        (x+1, y, z), (x-1, y, z),  # X axis
        (x, y+1, z), (x, y-1, z),  # Y axis
        (x, y, z+1), (x, y, z-1),  # Z axis
    ]


def get_neighbors_26way(cell: GridCell) -> List[GridCell]:
    """Get all 26 neighbors (including diagonals)."""
    x, y, z = cell
    neighbors = []
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                if dx == 0 and dy == 0 and dz == 0:
                    continue  # Skip self
                neighbors.append((x+dx, y+dy, z+dz))
    return neighbors


# ============================================================
# A* PATHFINDING
# ============================================================

def find_path(
    start: Vec3,
    goal: Vec3,
    grid: NavGrid,
    allow_diagonal: bool = True
) -> PathResult:
    """A* pathfinding from start to goal on grid.
    
    Pure functional pathfinding:
    - Takes immutable NavGrid
    - Returns PathResult with waypoints
    - No side effects, deterministic
    
    Args:
        start: World-space start position
        goal: World-space goal position
        grid: Immutable navigation grid
        allow_diagonal: If True, allow 26-way movement, else 6-way
        
    Returns:
        PathResult with success flag, path waypoints, cost, and stats
    """
    # Convert to grid coordinates
    start_cell = world_to_grid(start, grid.resolution, grid.bounds_min)
    goal_cell = world_to_grid(goal, grid.resolution, grid.bounds_min)
    
    # Check if start/goal are valid
    if not is_in_bounds(start_cell, grid) or not is_in_bounds(goal_cell, grid):
        return PathResult(success=False, path=[], cost=0.0, nodes_explored=0)
    
    if start_cell not in grid.walkable_cells or goal_cell not in grid.walkable_cells:
        return PathResult(success=False, path=[], cost=0.0, nodes_explored=0)
    
    # Early exit if start == goal
    if start_cell == goal_cell:
        return PathResult(success=True, path=[start], cost=0.0, nodes_explored=1)
    
    # A* data structures
    open_set = []  # Priority queue: (f_score, counter, cell)
    counter = 0  # Tie-breaker for heap
    came_from = {}  # cell → parent cell
    g_score = {start_cell: 0.0}  # cell → cost from start
    f_score = {start_cell: euclidean_distance(start_cell, goal_cell)}  # cell → estimated total cost
    
    heapq.heappush(open_set, (f_score[start_cell], counter, start_cell))
    counter += 1
    
    closed_set = set()
    nodes_explored = 0
    
    # A* main loop
    while open_set:
        _, _, current = heapq.heappop(open_set)
        
        if current in closed_set:
            continue
        
        closed_set.add(current)
        nodes_explored += 1
        
        # Goal check
        if current == goal_cell:
            # Reconstruct path
            path_cells = []
            cell = current
            while cell in came_from:
                path_cells.append(cell)
                cell = came_from[cell]
            path_cells.append(start_cell)
            path_cells.reverse()
            
            # Convert to world coordinates
            path_world = [grid_to_world(c, grid.resolution, grid.bounds_min) for c in path_cells]
            
            return PathResult(
                success=True,
                path=path_world,
                cost=g_score[current],
                nodes_explored=nodes_explored
            )
        
        # Explore neighbors
        neighbors = get_neighbors_26way(current) if allow_diagonal else get_neighbors_6way(current)
        
        for neighbor in neighbors:
            # Check bounds and walkability
            if not is_in_bounds(neighbor, grid):
                continue
            if neighbor not in grid.walkable_cells:
                continue
            if neighbor in closed_set:
                continue
            
            # Calculate movement cost
            move_cost = euclidean_distance(current, neighbor)
            tentative_g = g_score[current] + move_cost
            
            # Check if this path is better
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + euclidean_distance(neighbor, goal_cell)
                heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
                counter += 1
    
    # No path found
    return PathResult(success=False, path=[], cost=0.0, nodes_explored=nodes_explored)


# ============================================================
# GRID RAYCAST (LINE-OF-SIGHT)
# ============================================================

def raycast(start: Vec3, end: Vec3, grid: NavGrid) -> bool:
    """Grid-based raycast for line-of-sight check.
    
    Uses DDA (Digital Differential Analyzer) to traverse grid.
    Returns True if line from start to end is clear (no blocked cells).
    
    Args:
        start: World-space start position
        end: World-space end position
        grid: Navigation grid
        
    Returns:
        True if line is clear, False if blocked
    """
    start_cell = world_to_grid(start, grid.resolution, grid.bounds_min)
    end_cell = world_to_grid(end, grid.resolution, grid.bounds_min)
    
    # Check bounds
    if not is_in_bounds(start_cell, grid) or not is_in_bounds(end_cell, grid):
        return False
    
    # DDA traversal
    x0, y0, z0 = start_cell
    x1, y1, z1 = end_cell
    
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    dz = abs(z1 - z0)
    
    n = 1 + dx + dy + dz
    x, y, z = x0, y0, z0
    
    x_inc = 1 if x1 > x0 else -1
    y_inc = 1 if y1 > y0 else -1
    z_inc = 1 if z1 > z0 else -1
    
    error_xy = dx - dy
    error_xz = dx - dz
    error_yz = dy - dz
    
    dx *= 2
    dy *= 2
    dz *= 2
    
    for _ in range(n):
        current_cell = (x, y, z)
        
        # Check if current cell is walkable
        if current_cell not in grid.walkable_cells:
            return False  # Blocked
        
        if (x, y, z) == end_cell:
            return True  # Reached end
        
        # DDA step
        if error_xy > 0 and error_xz > 0:
            x += x_inc
            error_xy -= dy
            error_xz -= dz
        elif error_xy > 0 and error_yz > 0:
            y += y_inc
            error_xy += dx
            error_yz -= dz
        elif error_xz > 0 and error_yz < 0:
            z += z_inc
            error_xz += dx
            error_yz += dy
        else:
            # Tie-break - move along axis with largest delta
            if dx >= dy and dx >= dz:
                x += x_inc
                error_xy -= dy
                error_xz -= dz
            elif dy >= dx and dy >= dz:
                y += y_inc
                error_xy += dx
                error_yz -= dz
            else:
                z += z_inc
                error_xz += dx
                error_yz += dy
    
    return True


# ============================================================
# GRID CONSTRUCTION HELPERS
# ============================================================

def create_empty_grid(
    resolution: float,
    bounds_min: Vec3,
    bounds_max: Vec3
) -> NavGrid:
    """Create an empty navigation grid (all cells walkable)."""
    # Calculate dimensions
    dims_x = int((bounds_max[0] - bounds_min[0]) / resolution)
    dims_y = int((bounds_max[1] - bounds_min[1]) / resolution)
    dims_z = int((bounds_max[2] - bounds_min[2]) / resolution)
    
    # Create all cells
    walkable = set()
    for x in range(dims_x):
        for y in range(dims_y):
            for z in range(dims_z):
                walkable.add((x, y, z))
    
    return NavGrid(
        resolution=resolution,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        walkable_cells=frozenset(walkable)
    )


def add_obstacle_sphere(
    grid: NavGrid,
    center: Vec3,
    radius: float
) -> NavGrid:
    """Create new grid with sphere obstacle removed.
    
    Returns new NavGrid with cells inside sphere marked as blocked.
    """
    center_cell = world_to_grid(center, grid.resolution, grid.bounds_min)
    radius_cells = int(radius / grid.resolution) + 1
    
    new_walkable = set(grid.walkable_cells)
    
    # Remove cells within sphere
    for dx in range(-radius_cells, radius_cells + 1):
        for dy in range(-radius_cells, radius_cells + 1):
            for dz in range(-radius_cells, radius_cells + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy, center_cell[2] + dz)
                
                # Check if cell center is within sphere
                cell_world = grid_to_world(cell, grid.resolution, grid.bounds_min)
                dist_sq = sum((cell_world[i] - center[i])**2 for i in range(3))
                
                if dist_sq <= radius * radius:
                    new_walkable.discard(cell)
    
    return NavGrid(
        resolution=grid.resolution,
        bounds_min=grid.bounds_min,
        bounds_max=grid.bounds_max,
        walkable_cells=frozenset(new_walkable)
    )


# ============================================================
# TESTING (when run directly)
# ============================================================

if __name__ == "__main__":
    print("Testing navigation_mr kernel...")
    print()
    
    # Create test grid (10x10x10 meters, 1m resolution)
    grid = create_empty_grid(
        resolution=1.0,
        bounds_min=(0.0, 0.0, 0.0),
        bounds_max=(10.0, 10.0, 10.0)
    )
    
    print(f"Grid: {len(grid.walkable_cells)} walkable cells")
    print()
    
    # Test 1: Simple path
    print("TEST 1: Simple straight path")
    result = find_path((0.5, 0.5, 0.5), (5.5, 0.5, 0.5), grid)
    print(f"  Success: {result.success}")
    print(f"  Path length: {len(result.path)}")
    print(f"  Cost: {result.cost:.2f}")
    print(f"  Nodes explored: {result.nodes_explored}")
    print()
    
    # Test 2: Path with obstacle
    print("TEST 2: Path around obstacle")
    grid_with_wall = add_obstacle_sphere(grid, (5.0, 0.0, 0.0), 1.5)
    print(f"  Grid after obstacle: {len(grid_with_wall.walkable_cells)} walkable cells")
    
    result = find_path((0.5, 0.5, 0.5), (9.5, 0.5, 0.5), grid_with_wall)
    print(f"  Success: {result.success}")
    print(f"  Path length: {len(result.path)}")
    print(f"  Cost: {result.cost:.2f}")
    print(f"  Nodes explored: {result.nodes_explored}")
    print()
    
    # Test 3: Raycast
    print("TEST 3: Grid raycast")
    clear = raycast((0.5, 0.5, 0.5), (3.5, 0.5, 0.5), grid)
    print(f"  Clear path (no obstacle): {clear}")
    
    blocked = raycast((0.5, 0.5, 0.5), (9.5, 0.5, 0.5), grid_with_wall)
    print(f"  Clear path (with obstacle): {blocked}")
    print()
    
    # Test 4: No path possible
    print("TEST 4: Impossible path (blocked start)")
    grid_blocked_start = add_obstacle_sphere(grid, (0.5, 0.5, 0.5), 2.0)
    result = find_path((0.5, 0.5, 0.5), (9.5, 0.5, 0.5), grid_blocked_start)
    print(f"  Success: {result.success}")
    print(f"  Path: {result.path}")
    print()
    
    print("✅ navigation_mr kernel tests complete")
