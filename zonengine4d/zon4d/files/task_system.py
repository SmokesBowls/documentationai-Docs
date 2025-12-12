# task_system.py
"""
Universal Task System for EngAIn

This is the abstraction layer that unifies:
- Runtime Loop maintenance (pocket tasks)
- Performer game tasks (dialogue, audio, animation)
- Godot execution (routing tasks to nodes)

Tasks are the COMMON LANGUAGE across all scopes.

Build this FIRST, wire Godot to it SECOND.
Don't retrofit later.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol, Callable
import time


# ==========================================
# TASK ABSTRACTION
# ==========================================

class TaskDomain(Enum):
    """
    Domain classification for task routing.
    Each domain has its own handler in the engine.
    """
    ENGINE_MAINTENANCE = auto()  # Pocket tasks - memory cleanup, snapshot consolidation
    NARRATIVE = auto()           # Dialogue, scene transitions, story progression
    AUDIO = auto()               # Music, SFX, voice playback
    ANIMATION = auto()           # Body animation, facial visemes, blendshapes
    SPATIAL = auto()             # 3D positioning, physics, collision
    CAMERA = auto()              # Camera movement, FOV, shake
    VFX = auto()                 # Particles, shaders, post-processing
    AP_VALIDATION = auto()       # Rule checks, constraint validation


class TaskPriority(Enum):
    """
    Priority levels for task execution.
    Critical tasks never drop frames.
    Low tasks can be deferred if frame budget is tight.
    """
    CRITICAL = 0  # Must execute (dialogue, camera, core animation)
    HIGH = 1      # Should execute (BGM, key SFX, important VFX)
    MEDIUM = 2    # Can defer (ambient SFX, secondary animation)
    LOW = 3       # Optional (cosmetic effects, polish)


@dataclass
class Task:
    """
    Universal Task representation.
    
    Every system (Runtime, Performer, Godot) speaks Task.
    This is the atom of temporal work.
    """
    id: str
    domain: TaskDomain
    priority: TaskPriority
    tick_id: int
    scene_time: float
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"Task({self.id}, {self.domain.name}, priority={self.priority.value})"


# ==========================================
# TASK HANDLERS (Protocol)
# ==========================================

class TaskHandler(Protocol):
    """
    Protocol for domain-specific task handlers.
    Each domain (narrative, audio, etc.) implements this.
    """
    def can_handle(self, task: Task) -> bool:
        """Check if this handler can process the task"""
        ...
    
    def execute(self, task: Task) -> None:
        """Execute the task (may be async/deferred)"""
        ...
    
    def estimate_cost_ms(self, task: Task) -> float:
        """Estimate execution time in milliseconds"""
        ...


# ==========================================
# TASK ROUTER
# ==========================================

class TaskRouter:
    """
    Central task routing system.
    Routes tasks to appropriate domain handlers.
    
    This is what Runtime Loop and Performer use to emit tasks.
    This is what Godot ABI uses to execute tasks.
    """
    
    def __init__(self):
        self.handlers: Dict[TaskDomain, TaskHandler] = {}
        self.task_log: List[Dict[str, Any]] = []
        self.stats = {
            "total_tasks": 0,
            "tasks_by_domain": {},
            "tasks_by_priority": {},
        }
    
    def register_handler(self, domain: TaskDomain, handler: TaskHandler) -> None:
        """Register a handler for a specific domain"""
        self.handlers[domain] = handler
    
    def route(self, task: Task) -> bool:
        """
        Route a single task to its handler.
        Returns True if handled, False if no handler available.
        """
        handler = self.handlers.get(task.domain)
        
        if handler is None:
            self._log_unhandled(task)
            return False
        
        if not handler.can_handle(task):
            self._log_rejected(task)
            return False
        
        # Execute task
        start = time.time()
        handler.execute(task)
        duration_ms = (time.time() - start) * 1000
        
        # Log execution
        self._log_executed(task, duration_ms)
        return True
    
    def route_batch(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Route multiple tasks in priority order.
        Returns execution summary.
        """
        # Sort by priority (critical first)
        sorted_tasks = sorted(tasks, key=lambda t: t.priority.value)
        
        results = {
            "handled": 0,
            "unhandled": 0,
            "rejected": 0,
            "total_time_ms": 0.0,
        }
        
        for task in sorted_tasks:
            success = self.route(task)
            if success:
                results["handled"] += 1
            else:
                results["unhandled"] += 1
        
        return results
    
    def _log_executed(self, task: Task, duration_ms: float) -> None:
        """Log successful task execution"""
        self.task_log.append({
            "task_id": task.id,
            "domain": task.domain.name,
            "priority": task.priority.value,
            "tick": task.tick_id,
            "duration_ms": duration_ms,
            "status": "executed",
        })
        
        # Update stats
        self.stats["total_tasks"] += 1
        domain_name = task.domain.name
        self.stats["tasks_by_domain"][domain_name] = \
            self.stats["tasks_by_domain"].get(domain_name, 0) + 1
        priority = task.priority.value
        self.stats["tasks_by_priority"][priority] = \
            self.stats["tasks_by_priority"].get(priority, 0) + 1
    
    def _log_unhandled(self, task: Task) -> None:
        """Log task with no handler"""
        self.task_log.append({
            "task_id": task.id,
            "domain": task.domain.name,
            "status": "unhandled",
        })
    
    def _log_rejected(self, task: Task) -> None:
        """Log task rejected by handler"""
        self.task_log.append({
            "task_id": task.id,
            "domain": task.domain.name,
            "status": "rejected",
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get task execution statistics"""
        return dict(self.stats)


# ==========================================
# POCKET TASK GENERATOR
# ==========================================

class PocketTaskType(Enum):
    """Types of engine maintenance tasks"""
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
    """
    Create an engine maintenance (pocket) task.
    
    These run automatically to keep the engine clean and fast.
    """
    return Task(
        id=f"pocket_{task_type.value}_{tick_id}",
        domain=TaskDomain.ENGINE_MAINTENANCE,
        priority=TaskPriority.MEDIUM,  # Run when there's time
        tick_id=tick_id,
        scene_time=0.0,  # Pocket tasks are timeless
        payload={"type": task_type.value},
        metadata=metadata or {},
    )


# ==========================================
# EXAMPLE HANDLERS (For Testing)
# ==========================================

class LoggingTaskHandler:
    """
    Simple handler that just logs tasks.
    Use this for testing before Godot integration.
    """
    
    def __init__(self, domain: TaskDomain):
        self.domain = domain
        self.executed_tasks: List[Task] = []
    
    def can_handle(self, task: Task) -> bool:
        return task.domain == self.domain
    
    def execute(self, task: Task) -> None:
        print(f"[{self.domain.name}] Executing: {task.id}")
        self.executed_tasks.append(task)
    
    def estimate_cost_ms(self, task: Task) -> float:
        return 1.0  # Assume 1ms per task


class PocketTaskHandler:
    """
    Handler for engine maintenance tasks.
    
    In production, this would:
    - Flush delta queues
    - Consolidate snapshots
    - Purge old memory
    - Rebuild indexes
    
    For now, just logs what it would do.
    """
    
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
        # Maintenance tasks are cheap (1-5ms typically)
        return 2.0


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def create_task_router_with_logging() -> TaskRouter:
    """
    Create a TaskRouter with logging handlers for all domains.
    Use this for testing before Godot integration.
    """
    router = TaskRouter()
    
    # Register logging handlers for game domains
    for domain in [
        TaskDomain.NARRATIVE,
        TaskDomain.AUDIO,
        TaskDomain.ANIMATION,
        TaskDomain.SPATIAL,
        TaskDomain.CAMERA,
        TaskDomain.VFX,
    ]:
        router.register_handler(domain, LoggingTaskHandler(domain))
    
    # Register pocket task handler
    router.register_handler(
        TaskDomain.ENGINE_MAINTENANCE,
        PocketTaskHandler()
    )
    
    return router
