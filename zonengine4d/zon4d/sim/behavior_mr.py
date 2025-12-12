#!/usr/bin/env python3
"""
behavior_mr.py - Pure Functional Behavior FSM Kernel

The "mr" (mathematics/rules) kernel for Behavior3D.
Pure functional finite state machine: no state, no side effects, deterministic.

Snapshot-in → snapshot-out architecture:
- BehaviorState: Immutable FSM state per entity
- step_behavior(): State transition logic
- Integrates with Perception3D (what I see) and Navigation3D (where to go)

Portable to C++/Rust/GDExtension.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum

# Type aliases
Vec3 = Tuple[float, float, float]


# ============================================================
# BEHAVIOR STATES (FSM)
# ============================================================

class BehaviorStateType(Enum):
    """Possible behavior states for AI agents."""
    IDLE = "idle"
    PATROL = "patrol"
    CHASE = "chase"
    ATTACK = "attack"
    FLEE = "flee"
    SEARCH = "search"
    INVESTIGATE = "investigate"
    RETURN = "return"


# ============================================================
# IMMUTABLE DATA STRUCTURES
# ============================================================

@dataclass(frozen=True)
class BehaviorConfig:
    """Immutable configuration for behavior AI."""
    # Detection ranges
    sight_range: float = 20.0
    hearing_range: float = 15.0
    attack_range: float = 2.0
    flee_threshold_health: float = 0.3  # Flee when health < 30%
    
    # Chase behavior
    chase_abandon_range: float = 30.0  # Stop chase if target too far
    chase_abandon_time: float = 10.0   # Stop chase after 10s if no sight
    
    # Search behavior
    search_duration: float = 5.0       # Search for 5s before giving up
    search_radius: float = 10.0
    
    # Patrol behavior
    patrol_wait_time: float = 3.0      # Wait 3s at patrol points
    patrol_speed: float = 2.0
    
    # Movement speeds
    walk_speed: float = 2.0
    chase_speed: float = 5.0
    flee_speed: float = 6.0


@dataclass(frozen=True)
class BehaviorState:
    """Immutable behavior state for a single entity."""
    entity_id: str
    current_state: BehaviorStateType
    target_entity: Optional[str] = None
    target_position: Optional[Vec3] = None
    last_known_position: Optional[Vec3] = None
    state_enter_time: float = 0.0
    time_since_target_seen: float = 0.0
    patrol_index: int = 0
    patrol_points: Tuple[Vec3, ...] = field(default_factory=tuple)
    alert_level: float = 0.0  # 0.0 = calm, 1.0 = max alert
    
    def with_state(self, new_state: BehaviorStateType, tick: float) -> 'BehaviorState':
        """Create new state with updated FSM state."""
        return BehaviorState(
            entity_id=self.entity_id,
            current_state=new_state,
            target_entity=self.target_entity,
            target_position=self.target_position,
            last_known_position=self.last_known_position,
            state_enter_time=tick,
            time_since_target_seen=self.time_since_target_seen,
            patrol_index=self.patrol_index,
            patrol_points=self.patrol_points,
            alert_level=self.alert_level
        )
    
    def with_target(self, target_id: Optional[str], target_pos: Optional[Vec3]) -> 'BehaviorState':
        """Create new state with updated target."""
        return BehaviorState(
            entity_id=self.entity_id,
            current_state=self.current_state,
            target_entity=target_id,
            target_position=target_pos,
            last_known_position=target_pos if target_pos else self.last_known_position,
            state_enter_time=self.state_enter_time,
            time_since_target_seen=0.0 if target_id else self.time_since_target_seen,
            patrol_index=self.patrol_index,
            patrol_points=self.patrol_points,
            alert_level=self.alert_level
        )
    
    def with_alert(self, alert: float) -> 'BehaviorState':
        """Create new state with updated alert level."""
        return BehaviorState(
            entity_id=self.entity_id,
            current_state=self.current_state,
            target_entity=self.target_entity,
            target_position=self.target_position,
            last_known_position=self.last_known_position,
            state_enter_time=self.state_enter_time,
            time_since_target_seen=self.time_since_target_seen,
            patrol_index=self.patrol_index,
            patrol_points=self.patrol_points,
            alert_level=max(0.0, min(1.0, alert))  # Clamp [0, 1]
        )


@dataclass(frozen=True)
class PerceptionInput:
    """Perception data from Perception3D."""
    visible_entities: Tuple[str, ...] = field(default_factory=tuple)
    audible_entities: Tuple[str, ...] = field(default_factory=tuple)
    entity_positions: Dict[str, Vec3] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityState:
    """Spatial state for an entity."""
    position: Vec3
    health: float = 1.0
    tags: Tuple[str, ...] = field(default_factory=tuple)


@dataclass
class BehaviorAction:
    """Action output from behavior system."""
    entity_id: str
    action_type: str  # "move_to", "attack", "wait", "patrol"
    target_entity: Optional[str] = None
    target_position: Optional[Vec3] = None
    speed: float = 2.0


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def distance(a: Vec3, b: Vec3) -> float:
    """Calculate Euclidean distance between two points."""
    return ((a[0] - b[0])**2 + (a[1] - b[1])**2 + (a[2] - b[2])**2) ** 0.5


def is_enemy(entity_tags: Tuple[str, ...], my_tags: Tuple[str, ...]) -> bool:
    """Determine if entity is an enemy based on tags."""
    # Simple heuristic: "player" is enemy to "npc", "hostile" tags
    if "player" in entity_tags and ("npc" in my_tags or "hostile" in my_tags):
        return True
    if "enemy" in entity_tags:
        return True
    return False


# ============================================================
# FSM TRANSITION LOGIC
# ============================================================

def step_behavior(
    behavior_state: BehaviorState,
    entity_state: EntityState,
    perception: PerceptionInput,
    config: BehaviorConfig,
    current_tick: float,
    delta_time: float
) -> Tuple[BehaviorState, List[BehaviorAction]]:
    """
    Pure functional behavior FSM step.
    
    Takes current behavior state, entity state, and perception input.
    Returns new behavior state and list of actions to execute.
    
    FSM States:
    - IDLE: Standing still, waiting
    - PATROL: Following patrol route
    - CHASE: Pursuing target
    - ATTACK: In range, attacking
    - FLEE: Low health, running away
    - SEARCH: Lost target, searching last known position
    - INVESTIGATE: Heard sound, moving to investigate
    - RETURN: Returning to patrol route
    
    Args:
        behavior_state: Current behavior FSM state
        entity_state: Current spatial/health state
        perception: What entity can see/hear
        config: Behavior configuration
        current_tick: Current game time
        delta_time: Time since last step
        
    Returns:
        (new_behavior_state, actions)
    """
    actions = []
    
    # Update time since target seen
    time_since_seen = behavior_state.time_since_target_seen + delta_time
    behavior_state = BehaviorState(
        entity_id=behavior_state.entity_id,
        current_state=behavior_state.current_state,
        target_entity=behavior_state.target_entity,
        target_position=behavior_state.target_position,
        last_known_position=behavior_state.last_known_position,
        state_enter_time=behavior_state.state_enter_time,
        time_since_target_seen=time_since_seen,
        patrol_index=behavior_state.patrol_index,
        patrol_points=behavior_state.patrol_points,
        alert_level=behavior_state.alert_level
    )
    
    # Find enemies in perception
    enemies_seen = [
        eid for eid in perception.visible_entities
        if is_enemy(
            perception.entity_positions.get(eid, (0, 0, 0)),  # Placeholder, need tags
            entity_state.tags
        )
    ]
    
    # Priority check: Flee if low health
    if entity_state.health < config.flee_threshold_health and enemies_seen:
        if behavior_state.current_state != BehaviorStateType.FLEE:
            behavior_state = behavior_state.with_state(BehaviorStateType.FLEE, current_tick)
            # Flee away from closest enemy
            if enemies_seen and enemies_seen[0] in perception.entity_positions:
                enemy_pos = perception.entity_positions[enemies_seen[0]]
                # Calculate flee direction (opposite of enemy)
                dx = entity_state.position[0] - enemy_pos[0]
                dy = entity_state.position[1] - enemy_pos[1]
                dz = entity_state.position[2] - enemy_pos[2]
                mag = (dx**2 + dy**2 + dz**2) ** 0.5
                if mag > 0:
                    flee_pos = (
                        entity_state.position[0] + dx/mag * 10,
                        entity_state.position[1] + dy/mag * 10,
                        entity_state.position[2] + dz/mag * 10
                    )
                    behavior_state = behavior_state.with_target(None, flee_pos)
        
        # Flee action
        if behavior_state.target_position:
            actions.append(BehaviorAction(
                entity_id=behavior_state.entity_id,
                action_type="move_to",
                target_position=behavior_state.target_position,
                speed=config.flee_speed
            ))
        
        return behavior_state, actions
    
    # FSM State Machine
    current = behavior_state.current_state
    
    # ========================================
    # IDLE State
    # ========================================
    if current == BehaviorStateType.IDLE:
        # Transition: Enemy seen → CHASE
        if enemies_seen:
            enemy_id = enemies_seen[0]
            enemy_pos = perception.entity_positions.get(enemy_id)
            behavior_state = behavior_state.with_state(BehaviorStateType.CHASE, current_tick)
            behavior_state = behavior_state.with_target(enemy_id, enemy_pos)
            behavior_state = behavior_state.with_alert(1.0)
        
        # Transition: Has patrol route → PATROL
        elif behavior_state.patrol_points:
            behavior_state = behavior_state.with_state(BehaviorStateType.PATROL, current_tick)
        
        # Stay idle - wait action
        else:
            actions.append(BehaviorAction(
                entity_id=behavior_state.entity_id,
                action_type="wait"
            ))
    
    # ========================================
    # PATROL State
    # ========================================
    elif current == BehaviorStateType.PATROL:
        # Transition: Enemy seen → CHASE
        if enemies_seen:
            enemy_id = enemies_seen[0]
            enemy_pos = perception.entity_positions.get(enemy_id)
            behavior_state = behavior_state.with_state(BehaviorStateType.CHASE, current_tick)
            behavior_state = behavior_state.with_target(enemy_id, enemy_pos)
            behavior_state = behavior_state.with_alert(1.0)
        
        # Continue patrol
        elif behavior_state.patrol_points:
            patrol_target = behavior_state.patrol_points[behavior_state.patrol_index]
            
            # Check if reached patrol point
            dist_to_point = distance(entity_state.position, patrol_target)
            if dist_to_point < 1.0:
                # Wait at patrol point
                time_at_point = current_tick - behavior_state.state_enter_time
                if time_at_point < config.patrol_wait_time:
                    actions.append(BehaviorAction(
                        entity_id=behavior_state.entity_id,
                        action_type="wait"
                    ))
                else:
                    # Move to next patrol point
                    next_index = (behavior_state.patrol_index + 1) % len(behavior_state.patrol_points)
                    behavior_state = BehaviorState(
                        entity_id=behavior_state.entity_id,
                        current_state=behavior_state.current_state,
                        target_entity=behavior_state.target_entity,
                        target_position=behavior_state.target_position,
                        last_known_position=behavior_state.last_known_position,
                        state_enter_time=current_tick,
                        time_since_target_seen=behavior_state.time_since_target_seen,
                        patrol_index=next_index,
                        patrol_points=behavior_state.patrol_points,
                        alert_level=behavior_state.alert_level
                    )
            else:
                # Move to patrol point
                actions.append(BehaviorAction(
                    entity_id=behavior_state.entity_id,
                    action_type="patrol",
                    target_position=patrol_target,
                    speed=config.patrol_speed
                ))
    
    # ========================================
    # CHASE State
    # ========================================
    elif current == BehaviorStateType.CHASE:
        # Update target position if visible
        if behavior_state.target_entity in perception.visible_entities:
            target_pos = perception.entity_positions.get(behavior_state.target_entity)
            behavior_state = behavior_state.with_target(behavior_state.target_entity, target_pos)
        
        if behavior_state.target_entity and behavior_state.target_position:
            dist_to_target = distance(entity_state.position, behavior_state.target_position)
            
            # Transition: In attack range → ATTACK
            if dist_to_target < config.attack_range:
                behavior_state = behavior_state.with_state(BehaviorStateType.ATTACK, current_tick)
            
            # Transition: Lost target for too long → SEARCH
            elif behavior_state.time_since_target_seen > config.chase_abandon_time:
                behavior_state = behavior_state.with_state(BehaviorStateType.SEARCH, current_tick)
            
            # Transition: Target too far → RETURN
            elif dist_to_target > config.chase_abandon_range:
                behavior_state = behavior_state.with_state(BehaviorStateType.RETURN, current_tick)
            
            # Continue chase
            else:
                actions.append(BehaviorAction(
                    entity_id=behavior_state.entity_id,
                    action_type="move_to",
                    target_entity=behavior_state.target_entity,
                    target_position=behavior_state.target_position,
                    speed=config.chase_speed
                ))
    
    # ========================================
    # ATTACK State
    # ========================================
    elif current == BehaviorStateType.ATTACK:
        if behavior_state.target_entity:
            # Check if still in range
            target_pos = perception.entity_positions.get(behavior_state.target_entity)
            if target_pos:
                dist = distance(entity_state.position, target_pos)
                if dist > config.attack_range * 1.5:
                    # Target moved away → CHASE
                    behavior_state = behavior_state.with_state(BehaviorStateType.CHASE, current_tick)
                else:
                    # Attack!
                    actions.append(BehaviorAction(
                        entity_id=behavior_state.entity_id,
                        action_type="attack",
                        target_entity=behavior_state.target_entity
                    ))
            else:
                # Lost sight → SEARCH
                behavior_state = behavior_state.with_state(BehaviorStateType.SEARCH, current_tick)
    
    # ========================================
    # SEARCH State
    # ========================================
    elif current == BehaviorStateType.SEARCH:
        time_in_search = current_tick - behavior_state.state_enter_time
        
        # Transition: Found target again → CHASE
        if enemies_seen:
            enemy_id = enemies_seen[0]
            enemy_pos = perception.entity_positions.get(enemy_id)
            behavior_state = behavior_state.with_state(BehaviorStateType.CHASE, current_tick)
            behavior_state = behavior_state.with_target(enemy_id, enemy_pos)
        
        # Transition: Search timeout → RETURN
        elif time_in_search > config.search_duration:
            behavior_state = behavior_state.with_state(BehaviorStateType.RETURN, current_tick)
        
        # Continue searching last known position
        elif behavior_state.last_known_position:
            actions.append(BehaviorAction(
                entity_id=behavior_state.entity_id,
                action_type="move_to",
                target_position=behavior_state.last_known_position,
                speed=config.walk_speed
            ))
    
    # ========================================
    # RETURN State
    # ========================================
    elif current == BehaviorStateType.RETURN:
        # Transition: Enemy seen → CHASE
        if enemies_seen:
            enemy_id = enemies_seen[0]
            enemy_pos = perception.entity_positions.get(enemy_id)
            behavior_state = behavior_state.with_state(BehaviorStateType.CHASE, current_tick)
            behavior_state = behavior_state.with_target(enemy_id, enemy_pos)
        
        # Return to patrol or idle
        elif behavior_state.patrol_points:
            # Return to nearest patrol point
            nearest_point = min(
                behavior_state.patrol_points,
                key=lambda p: distance(entity_state.position, p)
            )
            dist_to_patrol = distance(entity_state.position, nearest_point)
            
            if dist_to_patrol < 2.0:
                # Reached patrol route → PATROL
                behavior_state = behavior_state.with_state(BehaviorStateType.PATROL, current_tick)
            else:
                # Move to patrol route
                actions.append(BehaviorAction(
                    entity_id=behavior_state.entity_id,
                    action_type="move_to",
                    target_position=nearest_point,
                    speed=config.walk_speed
                ))
        else:
            # No patrol route → IDLE
            behavior_state = behavior_state.with_state(BehaviorStateType.IDLE, current_tick)
    
    # Decay alert level
    alert_decay = 0.1 * delta_time
    behavior_state = behavior_state.with_alert(behavior_state.alert_level - alert_decay)
    
    return behavior_state, actions


# ============================================================
# TESTING (when run directly)
# ============================================================

if __name__ == "__main__":
    print("Testing behavior_mr kernel...")
    print()
    
    # Create test config
    config = BehaviorConfig()
    
    # Create guard with patrol route
    patrol_route = (
        (0.0, 0.0, 0.0),
        (10.0, 0.0, 0.0),
        (10.0, 10.0, 0.0),
        (0.0, 10.0, 0.0)
    )
    
    behavior_state = BehaviorState(
        entity_id="guard",
        current_state=BehaviorStateType.PATROL,
        patrol_points=patrol_route,
        patrol_index=0
    )
    
    entity_state = EntityState(
        position=(0.0, 0.0, 0.0),
        health=1.0,
        tags=("npc", "guard")
    )
    
    # Test 1: Normal patrol (no enemies)
    print("TEST 1: Normal patrol (no enemies)")
    perception = PerceptionInput(
        visible_entities=(),
        audible_entities=(),
        entity_positions={}
    )
    
    new_state, actions = step_behavior(
        behavior_state, entity_state, perception, config, 0.0, 0.1
    )
    
    print(f"  State: {new_state.current_state.value}")
    print(f"  Actions: {len(actions)}")
    if actions:
        print(f"  Action type: {actions[0].action_type}")
    print()
    
    # Test 2: Enemy spotted → chase
    print("TEST 2: Enemy spotted → chase")
    perception = PerceptionInput(
        visible_entities=("player",),
        audible_entities=(),
        entity_positions={"player": (15.0, 0.0, 0.0)}
    )
    
    entity_state = EntityState(
        position=(0.0, 0.0, 0.0),
        health=1.0,
        tags=("npc", "guard", "hostile")
    )
    
    new_state, actions = step_behavior(
        behavior_state, entity_state, perception, config, 1.0, 0.1
    )
    
    print(f"  State: {new_state.current_state.value}")
    print(f"  Target: {new_state.target_entity}")
    print(f"  Alert: {new_state.alert_level:.2f}")
    print(f"  Actions: {len(actions)}")
    if actions:
        print(f"  Action: {actions[0].action_type} → {actions[0].target_position}")
    print()
    
    # Test 3: Low health → flee
    print("TEST 3: Low health → flee")
    entity_state_damaged = EntityState(
        position=(5.0, 0.0, 0.0),
        health=0.2,  # 20% health
        tags=("npc", "guard")
    )
    
    new_state, actions = step_behavior(
        new_state, entity_state_damaged, perception, config, 2.0, 0.1
    )
    
    print(f"  State: {new_state.current_state.value}")
    print(f"  Health: {entity_state_damaged.health * 100:.0f}%")
    print(f"  Actions: {len(actions)}")
    if actions:
        print(f"  Action: {actions[0].action_type} speed={actions[0].speed}")
    print()
    
    print("✅ behavior_mr kernel tests complete")
