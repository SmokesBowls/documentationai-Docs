# test_full_integration.py
"""
Full Integration Test: Runtime Loop + Performer Engine

This demonstrates the complete pipeline:
  Agent → Delta → Runtime (Steps 1-6) → Hydration (Step 7) → 
  Performer (Step 11) → PerformanceTasks

Run with:
  cd ~/Downloads/EngAIn/zonengine4d/zon4d
  python3 -m ENGINALITY.test_full_integration
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from pprint import pprint

from .runtime_loop import (
    EnginalityRuntime,
    Delta,
    Snapshot,
    APVerdict,
    AnchorStore,
    APEngine,
    ZON4DKernel,
    PerformanceABI,
)
from .performer_engine import PerformerEngine
from .task_types import PerformanceTask


# ==========================================
# STUB IMPLEMENTATIONS (same as test_runtime_loop.py)
# ==========================================

class TestAnchorStore:
    def __init__(self):
        self.initial = Snapshot(id="snap_0", tick=0, zon4d_state={})
        self.hash_ok = True

    def load_initial_snapshot(self) -> Snapshot:
        return self.initial

    def load_last_immutable_anchor(self) -> Snapshot:
        return self.initial

    def compute_hash(self, snapshot: Snapshot) -> str:
        return f"hash_{snapshot.tick}"

    def append_snapshot(self, snapshot: Snapshot) -> None:
        pass

    def timeline_hash_ok(self) -> bool:
        return self.hash_ok


class TestAPEngine:
    def preflight_delta(self, snapshot: Snapshot, delta: Delta, ms_budget: int) -> APVerdict:
        return APVerdict.ACCEPT

    def arbitrate_delta(self, snapshot: Snapshot, delta: Delta, ms_budget: int) -> Optional[Delta]:
        return delta

    def finalize_snapshot(self, snapshot: Snapshot, ms_budget: int) -> APVerdict:
        return APVerdict.ACCEPT

    def arbitrate_snapshot(self, snapshot: Snapshot, ms_budget: int) -> Optional[Snapshot]:
        return snapshot


class TestZON4DKernel:
    """
    Simple kernel that applies deltas to a dict-based state.
    Tracks narrative/audio/animation changes for domain view generation.
    """

    def compute_inverse_delta(self, state: Dict[str, Any], delta: Delta) -> Optional[Delta]:
        old_val = state.get(delta.entity_ref)
        inv = Delta(
            id=f"inv_{delta.id}",
            source_id="inverse",
            entity_ref=delta.entity_ref,
            temporal_index=delta.temporal_index,
            temporal_scope=delta.temporal_scope,
            parent_ids=[delta.id],
            payload=old_val,
        )
        return inv

    def apply_delta_in_place(self, state: Dict[str, Any], delta: Delta) -> None:
        state[delta.entity_ref] = delta.payload

    def validate_state(self, state: Dict[str, Any]) -> bool:
        # Simple validation: reject if any value is "INVALID"
        return "INVALID" not in state.values()


class TestPerformanceABI:
    """
    Logs PerformanceTasks instead of rendering them.
    """

    def __init__(self):
        self.task_log: List[Dict[str, Any]] = []

    def schedule_performance(self, tick_id: int, tasks: List[PerformanceTask]) -> None:
        for task in tasks:
            self.task_log.append({
                "tick": tick_id,
                "task_id": task.id,
                "type": task.task_type.value,
                "scene_time": task.scene_time,
                "priority": task.priority,
                "payload": task.payload,
            })


# ==========================================
# DOMAIN VIEW GENERATOR
# ==========================================

def generate_domain_views_from_state(state: Dict[str, Any], tick_id: int) -> Dict[str, Any]:
    """
    Convert ZON4D state into domain views that Performer can consume.
    
    This simulates Step 7 (Hydration) by extracting narrative/audio/animation
    events from the current state.
    """
    views: Dict[str, Any] = {}

    # NARRATIVE VIEW
    active_speaker = state.get("narrative/active_speaker")
    active_line = state.get("narrative/active_line")
    emotion = state.get("narrative/emotion")
    intensity = state.get("narrative/intensity")

    if active_speaker and active_line:
        views["narrative_view"] = {
            "active_conversations": [{
                "conversation_id": "main",
                "speaker_id": active_speaker,
                "line_id": active_line,
                "emotion": emotion or "neutral",
                "intensity": intensity or 0.5,
                "duration": 2.5,
            }]
        }

    # AUDIO VIEW
    music_asset = state.get("audio/music")
    sfx_asset = state.get("audio/sfx")

    audio_events = []
    if music_asset:
        audio_events.append({
            "asset_id": music_asset,
            "action": "play",
            "duration": 10.0,
        })
    if sfx_asset:
        audio_events.append({
            "asset_id": sfx_asset,
            "duration": 1.0,
        })

    if audio_events:
        views["audio_view"] = {
            "music_events": [e for e in audio_events if e.get("action") == "play"],
            "sfx_events": [e for e in audio_events if "action" not in e],
        }

    # ANIMATION VIEW
    rig_id = state.get("animation/rig")
    pose_id = state.get("animation/pose")

    if rig_id and pose_id:
        views["animation_view"] = {
            "body_events": [{
                "rig_id": rig_id,
                "pose_id": pose_id,
                "duration": 2.0,
                "layer": "base",
            }]
        }

    return views


# ==========================================
# INTEGRATION TESTS
# ==========================================

def test_01_dialogue_triggers_performance():
    """
    Test: Delta mutates narrative state → Performer emits DialogueTask
    """
    print("\n" + "="*60)
    print("TEST 1: DIALOGUE DELTA → PERFORMANCE TASK")
    print("="*60)

    # Setup
    anchor_store = TestAnchorStore()
    ap_engine = TestAPEngine()
    zon4d = TestZON4DKernel()
    performer = PerformerEngine()
    perf_abi = TestPerformanceABI()

    runtime = EnginalityRuntime(
        anchor_store=anchor_store,
        ap_engine=ap_engine,
        zon4d_kernel=zon4d,
        config={},
        performer=performer,
        performance_abi=perf_abi,
    )

    # Create Delta that sets narrative state
    dialogue_delta = Delta(
        id="delta_dialogue_001",
        source_id="agent_mrlore",
        entity_ref="narrative/active_speaker",
        temporal_index=1.0,
        temporal_scope=(1.0, 1.0),
        parent_ids=[],
        payload="keen",
    )

    line_delta = Delta(
        id="delta_line_001",
        source_id="agent_mrlore",
        entity_ref="narrative/active_line",
        temporal_index=1.0,
        temporal_scope=(1.0, 1.0),
        parent_ids=[],
        payload="intro_001",
    )

    emotion_delta = Delta(
        id="delta_emotion_001",
        source_id="agent_mrlore",
        entity_ref="narrative/emotion",
        temporal_index=1.0,
        temporal_scope=(1.0, 1.0),
        parent_ids=[],
        payload="curious",
    )

    # Run Tick with Deltas
    ctx = runtime.run_tick(
        pending_deltas=[dialogue_delta, line_delta, emotion_delta],
        domain_views=generate_domain_views_from_state(
            runtime.current_snapshot.zon4d_state,
            tick_id=1
        ),
        delta_time=0.5,
    )

    print(f"\nTick {ctx.tick_id} Complete")
    print(f"State after Deltas: {ctx.snapshot_out.zon4d_state}")
    print(f"Performance Tasks emitted: {len(ctx.performance_tasks)}")
    
    if ctx.performance_tasks:
        print("\nPerformanceTasks:")
        for task in ctx.performance_tasks:
            pprint({
                "id": task.id,
                "type": task.task_type.value,
                "priority": task.priority,
                "payload": task.payload,
            })

    # Verify
    assert len(ctx.performance_tasks) > 0, "Should emit at least one task"
    dialogue_tasks = [t for t in ctx.performance_tasks if t.task_type.value == "dialogue"]
    assert len(dialogue_tasks) > 0, "Should emit dialogue task"
    
    print("\n✅ TEST 1 PASSED: Dialogue Delta → PerformanceTask pipeline working")


def test_02_multi_domain_performance():
    """
    Test: Multiple Deltas → narrative + audio + animation tasks
    """
    print("\n" + "="*60)
    print("TEST 2: MULTI-DOMAIN DELTA → MULTI-DOMAIN TASKS")
    print("="*60)

    # Setup
    anchor_store = TestAnchorStore()
    ap_engine = TestAPEngine()
    zon4d = TestZON4DKernel()
    performer = PerformerEngine()
    perf_abi = TestPerformanceABI()

    runtime = EnginalityRuntime(
        anchor_store=anchor_store,
        ap_engine=ap_engine,
        zon4d_kernel=zon4d,
        config={},
        performer=performer,
        performance_abi=perf_abi,
    )

    # Tick 1: Setup dialogue
    deltas_t1 = [
        Delta("d1", "agent", "narrative/active_speaker", 1.0, (1.0, 1.0), [], "tran"),
        Delta("d2", "agent", "narrative/active_line", 1.0, (1.0, 1.0), [], "intro_002"),
        Delta("d3", "agent", "narrative/emotion", 1.0, (1.0, 1.0), [], "wary"),
        Delta("d4", "agent", "audio/music", 1.0, (1.0, 1.0), [], "bgm_tense"),
        Delta("d5", "agent", "animation/rig", 1.0, (1.0, 1.0), [], "tran_rig"),
        Delta("d6", "agent", "animation/pose", 1.0, (1.0, 1.0), [], "defensive_stance"),
    ]

    ctx1 = runtime.run_tick(
        pending_deltas=deltas_t1,
        domain_views=generate_domain_views_from_state(
            runtime.current_snapshot.zon4d_state,
            tick_id=1
        ),
        delta_time=0.5,
    )

    print(f"\nTick {ctx1.tick_id} - Tasks: {len(ctx1.performance_tasks)}")
    
    # Count task types
    task_types = {}
    for task in ctx1.performance_tasks:
        t = task.task_type.value
        task_types[t] = task_types.get(t, 0) + 1

    print(f"Task breakdown: {task_types}")
    
    for task in ctx1.performance_tasks:
        print(f"  - {task.task_type.value}: {task.id}")

    # Verify multi-domain
    assert "dialogue" in task_types, "Should have dialogue task"
    assert "audio" in task_types, "Should have audio task"
    assert "animation" in task_types, "Should have animation task"

    print("\n✅ TEST 2 PASSED: Multi-domain coordination working")


def test_03_temporal_continuity():
    """
    Test: Multiple ticks maintain SceneTrack temporal continuity
    """
    print("\n" + "="*60)
    print("TEST 3: TEMPORAL CONTINUITY ACROSS TICKS")
    print("="*60)

    # Setup
    anchor_store = TestAnchorStore()
    ap_engine = TestAPEngine()
    zon4d = TestZON4DKernel()
    performer = PerformerEngine()
    perf_abi = TestPerformanceABI()

    runtime = EnginalityRuntime(
        anchor_store=anchor_store,
        ap_engine=ap_engine,
        zon4d_kernel=zon4d,
        config={},
        performer=performer,
        performance_abi=perf_abi,
    )

    scene_times = []

    # Run 5 ticks
    for tick in range(5):
        # Vary the deltas per tick
        deltas = []
        if tick == 1:
            deltas.append(Delta(f"d{tick}", "agent", "audio/sfx", float(tick), (float(tick), float(tick)), [], f"sfx_{tick}"))
        elif tick == 3:
            deltas.append(Delta(f"d{tick}", "agent", "narrative/active_speaker", float(tick), (float(tick), float(tick)), [], "keen"))
            deltas.append(Delta(f"d{tick}b", "agent", "narrative/active_line", float(tick), (float(tick), float(tick)), [], f"line_{tick}"))

        ctx = runtime.run_tick(
            pending_deltas=deltas,
            domain_views=generate_domain_views_from_state(
                runtime.current_snapshot.zon4d_state,
                tick_id=tick
            ),
            delta_time=0.5,
        )

        # Capture scene_time from first task (if any)
        if ctx.performance_tasks:
            scene_times.append(ctx.performance_tasks[0].scene_time)
        
        print(f"Tick {tick}: {len(ctx.performance_tasks)} tasks, scene_time: {scene_times[-1] if scene_times else 'N/A'}")

    # Verify monotonic scene_time
    for i in range(1, len(scene_times)):
        assert scene_times[i] >= scene_times[i-1], f"Scene time must be monotonic: {scene_times}"

    print(f"\nScene times: {scene_times}")
    print("✅ TEST 3 PASSED: Temporal continuity maintained across ticks")


def run_all_tests():
    print("\n" + "="*60)
    print("FULL INTEGRATION TEST SUITE")
    print("Runtime Loop + Performer Engine")
    print("="*60)

    test_01_dialogue_triggers_performance()
    test_02_multi_domain_performance()
    test_03_temporal_continuity()

    print("\n" + "="*60)
    print("🔥 ALL INTEGRATION TESTS PASSED 🔥")
    print("="*60)
    print("\nThe complete pipeline is working:")
    print("  Agent → Delta → Runtime → State → Domain Views → Performer → Tasks")
    print("\nReady for Godot integration!")


if __name__ == "__main__":
    run_all_tests()
