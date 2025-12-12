# task_system_merged.py
"""
Universal Task System for EngAIn (MERGED VERSION)

Combines:
- GPT's clean separation (TaskTree = planning, Task = execution)
- Rich semantic facades (Quest, Behavior, Sequence, Conversation, Maintenance, Routine)
- Domain-specific helpers and metadata
- Simple integration (flatten_to_tasks → route_batch)

This is the COMPREHENSIVE system - best of both approaches.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol, Callable, Set, Tuple
import time


# ==========================================
# TASK ABSTRACTION
# ==========================================

class TaskState(Enum):
    """Execution state (stored in Task, NOT TaskTree)"""
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class TaskDomain(Enum):
    """Domain classification for task routing"""
    ENGINE_MAINTENANCE = auto()
    NARRATIVE = auto()
    AUDIO = auto()
    ANIMATION = auto()
    SPATIAL = auto()
    CAMERA = auto()
    VFX = auto()
    AP_VALIDATION = auto()


class TaskPriority(Enum):
    """Priority levels for task execution"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class Task:
    """
    Flat execution unit.
    This is what actually runs through TaskRouter.
    """
    id: str
    domain: TaskDomain
    priority: TaskPriority
    tick_id: int
    scene_time: float
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Execution state (lives HERE, not in TaskTree)
    state: TaskState = TaskState.PENDING
    
    def __repr__(self) -> str:
        return f"Task({self.id}, {self.domain.name}, priority={self.priority.value})"


# ==========================================
# TASK TREE (Planning Only - GPT's Approach)
# ==========================================

@dataclass
class TaskTree:
    """
    Planning/authoring structure (NOT execution).
    
    TaskTree is purely for:
    - Authoring quest objectives
    - Defining NPC behaviors
    - Scripting cutscenes
    - Building dialogue trees
    
    Execution happens by converting to Task objects.
    """
    id: str
    label: str
    domain: TaskDomain
    priority: TaskPriority = TaskPriority.MEDIUM
    steps: List['TaskTree'] = field(default_factory=list)
    loop: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Simple progress counter (NOT execution state)
    current_step: int = 0
    
    # ---------- Authoring / Mutation ----------
    
    def add_step(self, step: 'TaskTree') -> 'TaskTree':
        """Add child step, return self for chaining"""
        self.steps.append(step)
        return self
    
    def insert_step(self, index: int, step: 'TaskTree') -> 'TaskTree':
        """Insert step at index"""
        self.steps.insert(index, step)
        return self
    
    def remove_step_by_id(self, step_id: str) -> bool:
        """Remove step by id, return True if found"""
        for i, s in enumerate(self.steps):
            if s.id == step_id:
                del self.steps[i]
                return True
        return False
    
    def find_step(self, step_id: str) -> Optional['TaskTree']:
        """Depth-first search for step by id"""
        if self.id == step_id:
            return self
        for s in self.steps:
            found = s.find_step(step_id)
            if found:
                return found
        return None
    
    # ---------- Traversal (For Authoring Tools) ----------
    
    def reset(self) -> None:
        """Reset traversal counter"""
        self.current_step = 0
        for s in self.steps:
            s.reset()
    
    def advance(self) -> None:
        """Move to next step"""
        self.current_step += 1
        if self.loop and self.steps:
            self.current_step %= len(self.steps)
    
    def current(self) -> Optional['TaskTree']:
        """Get current step (for authoring tools)"""
        if not self.steps or self.current_step >= len(self.steps):
            return None
        return self.steps[self.current_step]
    
    # ---------- Conversion to Executable Tasks ----------
    
    def to_task(
        self,
        tick_id: int,
        scene_time: float,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Convert THIS node to executable Task.
        This is the bridge: TaskTree (planning) → Task (execution).
        """
        payload = {
            "tree_id": self.id,
            "label": self.label,
            "loop": self.loop,
        }
        payload.update(self.metadata)
        if extra_payload:
            payload.update(extra_payload)
        
        return Task(
            id=f"{self.id}@{tick_id}",
            domain=self.domain,
            priority=self.priority,
            tick_id=tick_id,
            scene_time=scene_time,
            payload=payload,
            metadata={},
        )
    
    def flatten_to_tasks(
        self,
        start_tick: int,
        start_scene_time: float,
        dt_per_step: float = 0.5,
    ) -> List[Task]:
        """
        Convert entire tree to flat task list.
        Useful for:
        - Offline pre-compilation
        - Testing
        - Batch submission to TaskRouter
        """
        tasks: List[Task] = []
        queue: List[Tuple[TaskTree, int, float]] = [(self, start_tick, start_scene_time)]
        
        while queue:
            node, t_id, t_time = queue.pop(0)
            tasks.append(node.to_task(t_id, t_time))
            
            # Enqueue children
            child_tick = t_id + 1
            child_time = t_time + dt_per_step
            for child in node.steps:
                queue.append((child, child_tick, child_time))
        
        return tasks


# ==========================================
# SEMANTIC FACADES (Rich Domain Wrappers)
# ==========================================

@dataclass
class Quest(TaskTree):
    """
    Player missions with objectives and rewards.
    
    Example:
        quest = Quest(
            id="find_artifact",
            quest_name="The Lost Artifact",
            reward_gold=100
        )
        quest.add_objective(TaskTree(...))
    """
    domain: TaskDomain = TaskDomain.NARRATIVE
    
    # Quest-specific metadata
    quest_name: str = ""
    description: str = ""
    reward_gold: int = 0
    reward_items: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        # Store in metadata for serialization
        self.metadata.update({
            "quest_name": self.quest_name,
            "description": self.description,
            "reward_gold": self.reward_gold,
            "reward_items": self.reward_items,
        })
    
    @property
    def objectives(self) -> List[TaskTree]:
        """Semantic alias for steps"""
        return self.steps
    
    def add_objective(self, objective: TaskTree) -> 'Quest':
        """Domain-specific helper"""
        self.add_step(objective)
        return self


@dataclass
class Behavior(TaskTree):
    """
    NPC AI behaviors and patrol routes.
    
    Example:
        patrol = Behavior(
            id="guard_patrol",
            npc_id="guard_01",
            loop=True
        )
        patrol.add_action(TaskTree(...))
    """
    domain: TaskDomain = TaskDomain.SPATIAL
    
    # Behavior-specific metadata
    npc_id: str = ""
    interrupt_priority: int = 0
    
    def __post_init__(self):
        self.metadata.update({
            "npc_id": self.npc_id,
            "interrupt_priority": self.interrupt_priority,
        })
    
    @property
    def actions(self) -> List[TaskTree]:
        """Semantic alias for steps"""
        return self.steps
    
    def add_action(self, action: TaskTree) -> 'Behavior':
        """Domain-specific helper"""
        self.add_step(action)
        return self
    
    def should_loop(self) -> bool:
        """Check if behavior should restart"""
        return self.loop and self.current_step >= len(self.steps)


@dataclass
class Sequence(TaskTree):
    """
    Cutscenes and scripted events.
    
    Example:
        opening = Sequence(
            id="intro_cutscene",
            skippable=True
        )
        opening.add_scene(TaskTree(...))
    """
    domain: TaskDomain = TaskDomain.CAMERA
    
    # Sequence-specific metadata
    skippable: bool = True
    auto_advance: bool = True
    
    def __post_init__(self):
        self.metadata.update({
            "skippable": self.skippable,
            "auto_advance": self.auto_advance,
        })
    
    @property
    def scenes(self) -> List[TaskTree]:
        """Semantic alias for steps"""
        return self.steps
    
    def add_scene(self, scene: TaskTree) -> 'Sequence':
        """Domain-specific helper"""
        self.add_step(scene)
        return self
    
    def skip(self) -> None:
        """Skip to end (if skippable)"""
        if self.skippable:
            self.current_step = len(self.steps)


@dataclass
class Conversation(TaskTree):
    """
    Dialogue trees with branching.
    
    Example:
        convo = Conversation(
            id="keen_intro",
            speaker="keen",
            emotion="curious"
        )
        convo.add_line(TaskTree(...))
    """
    domain: TaskDomain = TaskDomain.NARRATIVE
    priority: TaskPriority = TaskPriority.CRITICAL
    
    # Conversation-specific metadata
    speaker: str = ""
    listener: str = ""
    emotion: str = "neutral"
    
    def __post_init__(self):
        self.metadata.update({
            "speaker": self.speaker,
            "listener": self.listener,
            "emotion": self.emotion,
        })
    
    @property
    def lines(self) -> List[TaskTree]:
        """Semantic alias for steps"""
        return self.steps
    
    def add_line(self, line: TaskTree) -> 'Conversation':
        """Domain-specific helper"""
        self.add_step(line)
        return self
    
    def branch(self, choice_index: int) -> Optional[TaskTree]:
        """Branch to specific choice"""
        if 0 <= choice_index < len(self.steps):
            self.current_step = choice_index
            return self.steps[choice_index]
        return None


@dataclass
class Maintenance(TaskTree):
    """
    Engine self-maintenance (pocket tasks).
    
    Example:
        cleanup = Maintenance(
            id="memory_cleanup",
            memory_threshold=0.8
        )
        cleanup.add_step(TaskTree(...))
    """
    domain: TaskDomain = TaskDomain.ENGINE_MAINTENANCE
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Maintenance-specific metadata
    memory_threshold: float = 0.8
    auto_schedule: bool = True
    
    def __post_init__(self):
        self.metadata.update({
            "memory_threshold": self.memory_threshold,
            "auto_schedule": self.auto_schedule,
        })
    
    @property
    def tasks(self) -> List[TaskTree]:
        """Semantic alias for steps"""
        return self.steps
    
    def should_run(self, current_memory_usage: float) -> bool:
        """Check if maintenance should run"""
        return current_memory_usage >= self.memory_threshold


@dataclass
class Routine(TaskTree):
    """
    Recurring timed tasks.
    
    Example:
        restock = Routine(
            id="shop_restock",
            interval_seconds=86400  # 24 hours
        )
        restock.add_step(TaskTree(...))
    """
    domain: TaskDomain = TaskDomain.SPATIAL
    
    # Routine-specific metadata
    interval_seconds: float = 0.0
    last_run_time: float = 0.0
    
    def __post_init__(self):
        self.metadata.update({
            "interval_seconds": self.interval_seconds,
            "last_run_time": self.last_run_time,
        })
    
    @property
    def tasks(self) -> List[TaskTree]:
        """Semantic alias for steps"""
        return self.steps
    
    def should_run(self, current_time: float) -> bool:
        """Check if enough time passed"""
        return (current_time - self.last_run_time) >= self.interval_seconds
    
    def mark_run(self, current_time: float) -> None:
        """Mark routine executed"""
        self.last_run_time = current_time
        self.metadata["last_run_time"] = current_time
        
        # ==========================================
# 3D SPATIAL / INTERACTION / CAMERA / PHYSICS FACADES
# ==========================================

@dataclass
class Navigation(TaskTree):
    """
    High-level 3D navigation:
      - move_to(position)
      - follow_path([pos...])
      - flee_from(target, radius)
      - orbit(target, radius)
    """
    domain: TaskDomain = TaskDomain.SPATIAL

    def move_to(self, position: List[float]) -> "Navigation":
        self.metadata["move_to"] = position
        return self

    def follow_path(self, path: List[List[float]]) -> "Navigation":
        self.metadata["follow_path"] = path
        return self

    def flee_from(self, target: str, radius: float = 10.0) -> "Navigation":
        self.metadata["flee_from"] = target
        self.metadata["radius"] = radius
        return self

    def orbit(self, target: str, radius: float = 3.0) -> "Navigation":
        self.metadata["orbit_target"] = target
        self.metadata["orbit_radius"] = radius
        return self


@dataclass
class Interaction(TaskTree):
    """
    World-object interactions:
      - use(object)
      - talk_to(npc)
      - pickup(item)
      - attack(target)
    """
    domain: TaskDomain = TaskDomain.NARRATIVE

    def use(self, object_id: str) -> "Interaction":
        self.metadata["use_object"] = object_id
        return self

    def talk_to(self, npc_id: str) -> "Interaction":
        self.metadata["talk_to"] = npc_id
        return self

    def pickup(self, object_id: str) -> "Interaction":
        self.metadata["pickup"] = object_id
        return self

    def attack(self, target_id: str, style: str = "default") -> "Interaction":
        self.metadata["attack_target"] = target_id
        self.metadata["attack_style"] = style
        return self


@dataclass
class CameraDirective(TaskTree):
    """
    Cutscene & dynamic camera control:
      - dolly_to(position)
      - orbit(target, radius)
      - cut_to(camera_id)
      - shake(intensity, duration)
    """
    domain: TaskDomain = TaskDomain.CAMERA

    def dolly_to(self, position: List[float]) -> "CameraDirective":
        self.metadata["camera_dolly_to"] = position
        return self

    def orbit(self, target: str, radius: float = 4.0) -> "CameraDirective":
        self.metadata["camera_orbit_target"] = target
        self.metadata["camera_orbit_radius"] = radius
        return self

    def cut_to(self, camera_id: str) -> "CameraDirective":
        self.metadata["camera_cut_to"] = camera_id
        return self

    def shake(self, intensity: float, duration: float) -> "CameraDirective":
        self.metadata["camera_shake_intensity"] = intensity
        self.metadata["camera_shake_duration"] = duration
        return self


@dataclass
class PhysicsDirective(TaskTree):
    """
    Physical actions:
      - apply_force([x,y,z])
      - impulse_jump(height)
      - ragdoll(True/False)
    """
    domain: TaskDomain = TaskDomain.ANIMATION

    def apply_force(self, force: List[float]) -> "PhysicsDirective":
        self.metadata["apply_force"] = force
        return self

    def impulse_jump(self, height: float) -> "PhysicsDirective":
        self.metadata["jump_height"] = height
        return self

    def ragdoll(self, enabled: bool = True) -> "PhysicsDirective":
        self.metadata["ragdoll"] = enabled
        return self

# ==========================================
# TASK HANDLERS (Protocol)
# ==========================================

class TaskHandler(Protocol):
    """Protocol for domain-specific handlers"""
    
    def can_handle(self, task: Task) -> bool: ...
    def execute(self, task: Task) -> None: ...
    def estimate_cost_ms(self, task: Task) -> float: ...


# ==========================================
# TASK ROUTER
# ==========================================

class TaskRouter:
    """Central task routing system"""
    
    def __init__(self):
        self.handlers: Dict[TaskDomain, TaskHandler] = {}
        self.task_log: List[Dict[str, Any]] = []
        self.stats = {
            "total_tasks": 0,
            "tasks_by_domain": {},
            "tasks_by_priority": {},
        }
    
    def register_handler(self, domain: TaskDomain, handler: TaskHandler) -> None:
        """Register handler for domain"""
        self.handlers[domain] = handler
    
    def route(self, task: Task) -> bool:
        """Route single task, return success"""
        handler = self.handlers.get(task.domain)
        
        if handler is None:
            self._log_unhandled(task)
            return False
        
        if not handler.can_handle(task):
            self._log_rejected(task)
            return False
        
        # Execute
        task.state = TaskState.RUNNING
        start = time.time()
        handler.execute(task)
        duration_ms = (time.time() - start) * 1000
        task.state = TaskState.COMPLETED
        
        self._log_executed(task, duration_ms)
        return True
    
    def route_batch(self, tasks: List[Task]) -> Dict[str, Any]:
        """Route multiple tasks in priority order"""
        sorted_tasks = sorted(tasks, key=lambda t: t.priority.value)
        
        results = {
            "handled": 0,
            "unhandled": 0,
            "total_time_ms": 0.0,
        }
        
        for task in sorted_tasks:
            if self.route(task):
                results["handled"] += 1
        
        return results
    
    def _log_executed(self, task: Task, duration_ms: float) -> None:
        self.task_log.append({
            "task_id": task.id,
            "domain": task.domain.name,
            "priority": task.priority.value,
            "tick": task.tick_id,
            "duration_ms": duration_ms,
            "status": "executed",
        })
        
        self.stats["total_tasks"] += 1
        domain_name = task.domain.name
        self.stats["tasks_by_domain"][domain_name] = \
            self.stats["tasks_by_domain"].get(domain_name, 0) + 1
        priority = task.priority.value
        self.stats["tasks_by_priority"][priority] = \
            self.stats["tasks_by_priority"].get(priority, 0) + 1
    
    def _log_unhandled(self, task: Task) -> None:
        self.task_log.append({
            "task_id": task.id,
            "domain": task.domain.name,
            "status": "unhandled",
        })
    
    def _log_rejected(self, task: Task) -> None:
        self.task_log.append({
            "task_id": task.id,
            "domain": task.domain.name,
            "status": "rejected",
        })
    
    def get_stats(self) -> Dict[str, Any]:
        return dict(self.stats)


# ==========================================
# POCKET TASK GENERATOR
# ==========================================

class PocketTaskType(Enum):
    """Engine maintenance task types"""
    FLUSH_DELTAS = "flush_deltas"
    CONSOLIDATE_SNAPSHOTS = "consolidate_snapshots"
    PURGE_TEMP_MEMORY = "purge_temp_memory"
    REBUILD_INDEX = "rebuild_index"
    VALIDATE_ANCHORS = "validate_anchors"
    GARBAGE_COLLECT = "garbage_collect"


def create_pocket_task(
    task_type: PocketTaskType,
    tick_id: int,
    metadata: Optional[Dict[str, Any]] = None
) -> Task:
    """Create engine maintenance task"""
    return Task(
        id=f"pocket_{task_type.value}_{tick_id}",
        domain=TaskDomain.ENGINE_MAINTENANCE,
        priority=TaskPriority.MEDIUM,
        tick_id=tick_id,
        scene_time=0.0,
        payload={"type": task_type.value},
        metadata=metadata or {},
    )


# ==========================================
# EXAMPLE HANDLERS
# ==========================================

class LoggingTaskHandler:
    """Simple logging handler for testing"""
    
    def __init__(self, domain: TaskDomain):
        self.domain = domain
        self.executed_tasks: List[Task] = []
    
    def can_handle(self, task: Task) -> bool:
        return task.domain == self.domain
    
    def execute(self, task: Task) -> None:
        print(f"[{self.domain.name}] Executing: {task.id}")
        self.executed_tasks.append(task)
    
    def estimate_cost_ms(self, task: Task) -> float:
        return 1.0


class PocketTaskHandler:
    """Handler for engine maintenance"""
    
    def __init__(self):
        self.maintenance_log: List[str] = []
    
    def can_handle(self, task: Task) -> bool:
        return task.domain == TaskDomain.ENGINE_MAINTENANCE
    
    def execute(self, task: Task) -> None:
        task_type = task.payload.get("type", "unknown")
        action = f"[ENGINE] Maintenance: {task_type} at tick {task.tick_id}"
        print(action)
        self.maintenance_log.append(action)
    
    def estimate_cost_ms(self, task: Task) -> float:
        return 2.0


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def create_task_router_with_logging() -> TaskRouter:
    """Create router with logging handlers for all domains"""
    router = TaskRouter()
    
    for domain in [
        TaskDomain.NARRATIVE,
        TaskDomain.AUDIO,
        TaskDomain.ANIMATION,
        TaskDomain.SPATIAL,
        TaskDomain.CAMERA,
        TaskDomain.VFX,
    ]:
        router.register_handler(domain, LoggingTaskHandler(domain))
    
    router.register_handler(
        TaskDomain.ENGINE_MAINTENANCE,
        PocketTaskHandler()
    )
    
    return router
