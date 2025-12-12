# runtime_loop.py

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Protocol
import time

# NEW: import Performer + PerformanceTask
from .performer_engine import PerformerEngine
from .task_types import PerformanceTask


# ---------------------------
# Spec-Driven Data Structures
# ---------------------------

class APVerdict(Enum):
    ACCEPT = auto()
    REJECT = auto()
    ARBITRATE = auto()
    TIMEOUT = auto()  # prototype-only explicit state


@dataclass
class Delta:
    """
    Delta structure per RUNTIME_LOOP_v0.1 Implementation Requirements §1.
    """
    id: str
    source_id: str
    entity_ref: str
    temporal_index: float
    temporal_scope: Tuple[float, float]
    parent_ids: List[str]
    payload: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Snapshot:
    """
    Canonical or candidate world state at a given Tick.
    """
    id: str
    tick: int
    zon4d_state: Dict[str, Any]
    hash32: Optional[str] = None
    anchor_type: str = "soft"  # "soft" | "hard" | "immutable"


@dataclass
class TickContext:
    """
    Execution context for a single Engine Tick.
    """
    tick_id: int
    wall_clock_ts: float
    snapshot_in: Snapshot
    snapshot_out: Optional[Snapshot] = None

    # Delta queues
    deltas_in: List[Delta] = field(default_factory=list)
    deltas_ordered: List[Delta] = field(default_factory=list)
    deltas_accepted: List[Delta] = field(default_factory=list)
    deltas_rejected: List[Delta] = field(default_factory=list)
    inverse_deltas: List[Delta] = field(default_factory=list)

    # Diagnostics
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    fenced: bool = False
    breached: bool = False
    breach_step: Optional[int] = None
    timeline_hash_ok: bool = True

    # NEW: Performer-related context
    delta_time: float = 0.0                     # seconds since last Tick
    domain_views: Dict[str, Any] = field(default_factory=dict)
    performance_tasks: List[PerformanceTask] = field(default_factory=list)


# ---------------------------
# Interfaces / Protocols
# ---------------------------

class AnchorStore(Protocol):
    """
    Anchor & Timeline backing store.
    Responsible for canonical Snapshot persistence + hash chain.
    """

    def load_initial_snapshot(self) -> Snapshot: ...
    def load_last_immutable_anchor(self) -> Snapshot: ...
    def compute_hash(self, snapshot: Snapshot) -> str: ...
    def append_snapshot(self, snapshot: Snapshot) -> None: ...
    def timeline_hash_ok(self) -> bool: ...


class APEngine(Protocol):
    """
    AP Rule Engine interface for preflight / finalization.
    Prototype-only timeout is passed as ms_budget.
    """

    def preflight_delta(self, snapshot: Snapshot, delta: Delta, ms_budget: int) -> APVerdict: ...
    def arbitrate_delta(self, snapshot: Snapshot, delta: Delta, ms_budget: int) -> Optional[Delta]: ...
    def finalize_snapshot(self, snapshot: Snapshot, ms_budget: int) -> APVerdict: ...
    def arbitrate_snapshot(self, snapshot: Snapshot, ms_budget: int) -> Optional[Snapshot]: ...


class ZON4DKernel(Protocol):
    """
    ZON4D Temporal Kernel: applies and inverts Deltas on raw state.
    """

    def compute_inverse_delta(self, state: Dict[str, Any], delta: Delta) -> Optional[Delta]: ...
    def apply_delta_in_place(self, state: Dict[str, Any], delta: Delta) -> None: ...
    def validate_state(self, state: Dict[str, Any]) -> bool: ...


class PerformanceABI(Protocol):
    """
    Execution ABI hook for performance scheduling.
    Runtime calls this at Step 11 with the tasks for a given Tick.
    """

    def schedule_performance(self, tick_id: int, tasks: List[PerformanceTask]) -> None: ...


class NoopPerformanceABI:
    """
    Safe default: do nothing with performance tasks.
    Lets you run the runtime with no renderer/audio yet.
    """

    def schedule_performance(self, tick_id: int, tasks: List[PerformanceTask]) -> None:
        # Intentionally no-op
        return


# ---------------------------
# Runtime Implementation
# ---------------------------

class EnginalityRuntime:
    """
    Enginality Runtime Loop v0.1 (with Performer integration).

    Implements:
      - STEP 1: Tick Initialization
      - STEP 2: Delta Queue Ingestion
      - STEP 3: Temporal Ordering
      - STEP 6: Delta Application
      - STEP 10: Domain View Generation (NEW: from NEW state)
      - STEP 11: Performance Pass Scheduling (PerformerEngine)
    And the breach / rollback framing from the Runtime Loop spec.
    """

    def __init__(
        self,
        anchor_store: AnchorStore,
        ap_engine: APEngine,
        zon4d_kernel: ZON4DKernel,
        config: Dict[str, Any],
        performer: Optional[PerformerEngine] = None,
        performance_abi: Optional[PerformanceABI] = None,
    ) -> None:
        self.anchor_store = anchor_store
        self.ap_engine = ap_engine
        self.zon4d = zon4d_kernel
        self.config = config

        self.tick_counter: int = 0
        self.current_snapshot: Snapshot = self.anchor_store.load_initial_snapshot()

        # Performance / behavior knobs from spec
        self.max_deltas_per_tick: int = config.get("max_deltas_per_tick", 1024)
        self.ap_preflight_budget_ms: int = config.get("ap_preflight_budget_ms", 5)
        self.ap_final_budget_ms: int = config.get("ap_final_budget_ms", 10)

        # NEW: Performer integration
        self.performer = performer
        self.performance_abi: PerformanceABI = performance_abi or NoopPerformanceABI()
        self._last_wall_clock_ts: Optional[float] = None

    # ========= PUBLIC ENTRYPOINT =========

    def run_tick(
        self,
        pending_deltas: List[Delta],
        domain_views: Optional[Dict[str, Any]] = None,
        delta_time: Optional[float] = None,
    ) -> TickContext:
        """
        Execute one Engine Tick (Steps 1–11).

        NEW:
        - domain_views: hydrated views from Step 10 (narrative/audio/animation/etc.)
        - delta_time: optional external time step (seconds). If None, computed from wall-clock.
        """
        ctx = self._step1_init(pending_deltas, domain_views, delta_time)

        try:
            self._step2_ingest(ctx)
            self._step3_temporal_order(ctx)

            # STEP 4/5/8 are Phase 2: we skip AP & conflicts here,
            # and treat deltas_ordered as deltas_accepted for now.
            ctx.deltas_accepted = list(ctx.deltas_ordered)

            self._step6_apply_deltas(ctx)

            # === NEW STEP 10: Generate domain views from the NEW state ===
            # This ensures Performer sees the state AFTER deltas are applied
            self._step10_generate_domain_views(ctx)

            self._step11_schedule_performance(ctx)

            # Mark new snapshot as current IF no breach
            if not ctx.breached and ctx.snapshot_out is not None:
                self.current_snapshot = ctx.snapshot_out

        except RuntimeError as exc:
            # Hard breach: record and rollback
            self._mark_breach(ctx, reason=str(exc))
            self._rollback(ctx)

        else:
            if ctx.breached:
                # Soft breach flagged inside steps
                self._rollback(ctx)

        return ctx

    # ========= STEP 1: TICK INITIALIZATION =========

    def _step1_init(
        self,
        pending_deltas: List[Delta],
        domain_views: Optional[Dict[str, Any]],
        explicit_delta_time: Optional[float],
    ) -> TickContext:
        self.tick_counter += 1

        wall_clock_ts = time.time()
        snapshot_in = self.current_snapshot

        # Compute delta_time (seconds)
        if explicit_delta_time is not None:
            dt = max(float(explicit_delta_time), 0.0)
        else:
            if self._last_wall_clock_ts is None:
                dt = 0.0
            else:
                dt = max(wall_clock_ts - self._last_wall_clock_ts, 0.0)

        self._last_wall_clock_ts = wall_clock_ts

        ctx = TickContext(
            tick_id=self.tick_counter,
            wall_clock_ts=wall_clock_ts,
            snapshot_in=snapshot_in,
            delta_time=dt,
            domain_views=dict(domain_views or {}),
        )

        # Queue all incoming deltas (they'll be filtered in Step 2)
        ctx.deltas_in = list(pending_deltas)

        # Check timeline hash continuity
        ctx.timeline_hash_ok = self.anchor_store.timeline_hash_ok()
        if not ctx.timeline_hash_ok:
            self._breach(ctx, step=1, message="Timeline hash mismatch at Tick init")

        return ctx

    # ========= STEP 2: DELTA QUEUE INGESTION =========

    def _step2_ingest(self, ctx: TickContext) -> None:
        if ctx.breached:
            return

        if len(ctx.deltas_in) > self.max_deltas_per_tick:
            # Temporal fence: truncate and fence the rest
            overflow = len(ctx.deltas_in) - self.max_deltas_per_tick
            ctx.deltas_in = ctx.deltas_in[: self.max_deltas_per_tick]
            self._alert(
                ctx,
                level="WARNING",
                step=2,
                message=f"Temporal fence: {overflow} Deltas pushed to next Tick",
            )
            ctx.fenced = True

        valid: List[Delta] = []
        for d in ctx.deltas_in:
            if self._validate_delta_structure(d):
                valid.append(self._normalized_delta(d))
            else:
                ctx.deltas_rejected.append(d)
                self._alert(
                    ctx,
                    level="WARNING",
                    step=2,
                    message=f"Rejected malformed Delta {d.id}",
                )

        ctx.deltas_in = valid

    def _validate_delta_structure(self, d: Delta) -> bool:
        # Minimal structural checks; extend later with ZON4D typing.
        if not d.id or not d.source_id or not d.entity_ref:
            return False
        if d.temporal_scope[0] > d.temporal_scope[1]:
            return False
        if len(d.parent_ids) > 64:
            return False
        return True

    def _normalized_delta(self, d: Delta) -> Delta:
        """
        Normalize Delta for deterministic behavior:
        - Clamp / round temporal_index to fixed precision
        """
        ti = round(float(d.temporal_index), 6)
        return Delta(
            id=d.id,
            source_id=d.source_id,
            entity_ref=d.entity_ref,
            temporal_index=ti,
            temporal_scope=d.temporal_scope,
            parent_ids=list(d.parent_ids),
            payload=d.payload,
            metadata=dict(d.metadata),
        )

    # ========= STEP 3: TEMPORAL ORDERING =========

    def _step3_temporal_order(self, ctx: TickContext) -> None:
        if ctx.breached:
            return

        def sort_key(d: Delta):
            depth = len(d.parent_ids)
            return (d.temporal_index, depth, d.source_id, d.id)

        ctx.deltas_ordered = sorted(ctx.deltas_in, key=sort_key)

    # ========= STEP 6: DELTA APPLICATION =========

    def _step6_apply_deltas(self, ctx: TickContext) -> None:
        if ctx.breached:
            return

        if ctx.snapshot_in is None:
            self._breach(ctx, step=6, message="No input Snapshot to mutate")
            raise RuntimeError("Missing snapshot_in")

        # Copy-on-write clone of state
        new_state = dict(ctx.snapshot_in.zon4d_state)
        inverse_deltas: List[Delta] = []

        for d in ctx.deltas_accepted:
            inv = self.zon4d.compute_inverse_delta(new_state, d)
            if inv is None:
                self._breach(
                    ctx,
                    step=6,
                    message=f"Cannot compute inverse for Delta {d.id}",
                )
                # Fast-path rollback is impossible → spec says fall back
                raise RuntimeError("Inverse Delta computation failed")

            # Apply mutation
            self.zon4d.apply_delta_in_place(new_state, d)
            inverse_deltas.append(inv)

        # Validate resulting state
        if not self.zon4d.validate_state(new_state):
            self._breach(ctx, step=6, message="ZON4D state validation failed")
            raise RuntimeError("ZON4D validation failed after mutations")

        snapshot_out = Snapshot(
            id=self._alloc_snapshot_id(ctx.tick_id),
            tick=ctx.tick_id,
            zon4d_state=new_state,
        )

        ctx.snapshot_out = snapshot_out
        ctx.inverse_deltas = inverse_deltas

    # ========= NEW STEP 10: DOMAIN VIEW GENERATION =========

    def _step10_generate_domain_views(self, ctx: TickContext) -> None:
        """
        Generate domain views from the NEW state (after deltas are applied).
        This ensures Performer sees the current authoritative state.
        """
        if ctx.breached or ctx.snapshot_out is None:
            return

        try:
            # Import here to avoid circular imports
            from .domain_views import generate_domain_views_from_state
            
            # Generate views from the NEW state (after deltas)
            post_delta_views = generate_domain_views_from_state(
                ctx.snapshot_out.zon4d_state,  # This has the dialogue data
                tick_id=ctx.tick_id
            )
            
            # Update the context with views from the NEW state
            # We merge with any provided views, but post-delta views take precedence
            if post_delta_views:
                ctx.domain_views.update(post_delta_views)
                
        except ImportError:
            self._alert(
                ctx,
                level="WARNING",
                step=10,
                message="domain_views module not available; skipping view generation",
            )
        except Exception as e:
            self._alert(
                ctx,
                level="ERROR",
                step=10,
                message=f"Domain view generation failed: {str(e)}",
            )

    # ========= STEP 11: PERFORMANCE PASS SCHEDULING =========

    def _step11_schedule_performance(self, ctx: TickContext) -> None:
        if ctx.breached:
            return

        # If no PerformerEngine is attached, just log and exit.
        if self.performer is None:
            self._alert(
                ctx,
                level="INFO",
                step=11,
                message="Tick complete (PerformerEngine not attached; performance no-op)",
            )
            return

        # Invoke PerformerEngine with domain views + delta_time
        # ctx.domain_views now contains views from the NEW state (after deltas)
        tasks = self.performer.step(
            tick_id=ctx.tick_id,
            delta_time=ctx.delta_time,
            domain_views=ctx.domain_views,
        )

        ctx.performance_tasks = list(tasks)

        # Forward to Performance ABI (Godot, audio engine, etc.)
        self.performance_abi.schedule_performance(ctx.tick_id, ctx.performance_tasks)

        self._alert(
            ctx,
            level="INFO",
            step=11,
            message=f"Tick complete (Performer scheduled {len(ctx.performance_tasks)} tasks)",
        )

    # ========= BREACH / ROLLBACK / ALERT HELPERS =========

    def _breach(self, ctx: TickContext, step: int, message: str) -> None:
        ctx.breached = True
        ctx.breach_step = step
        self._alert(ctx, level="CRITICAL", step=step, message=message)

    def _mark_breach(self, ctx: TickContext, reason: str) -> None:
        ctx.breached = True
        self._alert(
            ctx,
            level="CRITICAL",
            step=ctx.breach_step or -1,
            message=f"Runtime breach: {reason}",
        )

    def _rollback(self, ctx: TickContext) -> None:
        """
        Implements the fast/slow rollback decision rule from the spec,
        but delegates actual mechanics to AnchorStore and inverse_deltas.
        """
        step = ctx.breach_step or -1
        ctx.timeline_hash_ok = self.anchor_store.timeline_hash_ok()

        use_fast = (
            ctx.timeline_hash_ok
            and 2 <= step <= 7
            and len(ctx.inverse_deltas) > 0
        )

        if use_fast:
            # Fast path: apply inverse Deltas in reverse order
            state = dict(self.current_snapshot.zon4d_state)
            for inv in reversed(ctx.inverse_deltas):
                self.zon4d.apply_delta_in_place(state, inv)

            if not self.zon4d.validate_state(state):
                # Fallback to slow path if validation fails
                self._alert(
                    ctx,
                    level="CRITICAL",
                    step=step,
                    message="Fast-path rollback validation failed; falling back to anchor restore",
                )
                use_fast = False
            else:
                self.current_snapshot = Snapshot(
                    id=self.current_snapshot.id,
                    tick=self.current_snapshot.tick,
                    zon4d_state=state,
                    hash32=self.current_snapshot.hash32,
                    anchor_type=self.current_snapshot.anchor_type,
                )
                self._alert(
                    ctx,
                    level="INFO",
                    step=step,
                    message="Fast-path rollback applied via inverse Deltas",
                )

        if not use_fast:
            # Slow path: restore last immutable anchor
            anchor = self.anchor_store.load_last_immutable_anchor()
            self.current_snapshot = anchor
            self._alert(
                ctx,
                level="INFO",
                step=step,
                message="Slow-path rollback: restored last immutable anchor",
            )

    def _alert(self, ctx: TickContext, level: str, step: int, message: str) -> None:
        ctx.alerts.append(
            {
                "level": level,
                "step": step,
                "message": message,
                "tick": ctx.tick_id,
                "ts": ctx.wall_clock_ts,
            }
        )
        # In real engine: forward to ZWAlerts autoload or logging system.

    def _alloc_snapshot_id(self, tick_id: int) -> str:
        return f"snap_{tick_id}"
