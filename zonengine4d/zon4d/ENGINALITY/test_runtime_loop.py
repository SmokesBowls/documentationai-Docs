# test_runtime_loop.py

from ENGINALITY.runtime_loop import (
    EnginalityRuntime,
    AnchorStore,
    APEngine,
    ZON4DKernel,
    Delta,
    Snapshot,
    APVerdict,
)
import pprint


# -------------------------------
# In-memory Anchor Store
# -------------------------------
class TestAnchorStore(AnchorStore):
    def __init__(self):
        self.immutable_anchor = Snapshot(
            id="snap_0",
            tick=0,
            zon4d_state={"value": 0},  # initial world state
            hash32="hash0",
            anchor_type="immutable",
        )
        self.current_hash_ok = True
        self.timeline = [self.immutable_anchor]

    def load_initial_snapshot(self):
        return self.immutable_anchor

    def load_last_immutable_anchor(self):
        return self.immutable_anchor

    def compute_hash(self, snapshot):
        # Prototype hash: stable string based on sorted state
        return "h" + str(hash(frozenset(snapshot.zon4d_state.items())))

    def append_snapshot(self, snapshot):
        # Not used in prototype loop, but required for interface
        self.timeline.append(snapshot)

    def timeline_hash_ok(self):
        return self.current_hash_ok


# -------------------------------
# Stub AP Engine
# -------------------------------
class TestAPEngine(APEngine):
    def preflight_delta(self, snapshot, delta, ms_budget):
        return APVerdict.ACCEPT

    def arbitrate_delta(self, snapshot, delta, ms_budget):
        return delta

    def finalize_snapshot(self, snapshot, ms_budget):
        return APVerdict.ACCEPT

    def arbitrate_snapshot(self, snapshot, ms_budget):
        return snapshot


# -------------------------------
# Minimal ZON4D Kernel
# World state is just: { "value": int }
# -------------------------------
class TestZON4DKernel(ZON4DKernel):
    def compute_inverse_delta(self, state, delta):
        # Delta payload: {"op": "add", "amount": int}
        amt = delta.payload.get("amount")
        if amt is None:
            return None
        return Delta(
            id=f"inv_{delta.id}",
            source_id=delta.source_id,
            entity_ref=delta.entity_ref,
            temporal_index=delta.temporal_index,
            temporal_scope=delta.temporal_scope,
            parent_ids=[],
            payload={"op": "add", "amount": -amt},
        )

    def apply_delta_in_place(self, state, delta):
        amt = delta.payload.get("amount", 0)
        state["value"] = state.get("value", 0) + amt

    def validate_state(self, state):
        return isinstance(state.get("value"), int)


# -------------------------------
# Utility: pretty print results
# -------------------------------
def show(ctx, label):
    print("\n===============================")
    print(label)
    print("===============================")
    print("Tick:", ctx.tick_id)
    print("Snapshot In:", ctx.snapshot_in.zon4d_state)
    if ctx.snapshot_out:
        print("Snapshot Out:", ctx.snapshot_out.zon4d_state)
    print("Accepted Deltas:", [d.id for d in ctx.deltas_accepted])
    print("Rejected Deltas:", [d.id for d in ctx.deltas_rejected])
    print("Alerts:")
    pprint.pp(ctx.alerts)


# -------------------------------
# TEST CASES
# -------------------------------

def test_ordering():
    print("\n\n=== TEST 1: TEMPORAL ORDERING ===")

    runtime = EnginalityRuntime(
        anchor_store=TestAnchorStore(),
        ap_engine=TestAPEngine(),
        zon4d_kernel=TestZON4DKernel(),
        config={},
    )

    deltas = [
        Delta("d1", "user", "world/value", 10.0, (10, 10), [], {"op": "add", "amount": 5}),
        Delta("d2", "user", "world/value", 5.0,  (5, 5),  [], {"op": "add", "amount": 1}),
        Delta("d3", "user", "world/value", 7.0,  (7, 7),  [], {"op": "add", "amount": 2}),
    ]

    ctx = runtime.run_tick(deltas)
    show(ctx, "TEMPORAL ORDERING RESULT")

    assert [d.id for d in ctx.deltas_accepted] == ["d2", "d3", "d1"]


def test_mutation_and_inverse():
    print("\n\n=== TEST 2: DELTA APPLICATION + INVERSE ===")

    runtime = EnginalityRuntime(
        anchor_store=TestAnchorStore(),
        ap_engine=TestAPEngine(),
        zon4d_kernel=TestZON4DKernel(),
        config={},
    )

    deltas = [
        Delta("add10", "user", "world/value", 1, (1, 1), [], {"op": "add", "amount": 10}),
        Delta("add5",  "user", "world/value", 2, (2, 2), [], {"op": "add", "amount": 5}),
    ]

    ctx = runtime.run_tick(deltas)
    show(ctx, "MUTATION RESULT")

    assert ctx.snapshot_out.zon4d_state["value"] == 15


def test_too_many_deltas():
    print("\n\n=== TEST 3: TEMPORAL FENCE ===")

    runtime = EnginalityRuntime(
        anchor_store=TestAnchorStore(),
        ap_engine=TestAPEngine(),
        zon4d_kernel=TestZON4DKernel(),
        config={"max_deltas_per_tick": 3},
    )

    deltas = [
        Delta(f"d{i}", "user", "world/value", i, (i, i), [], {"op": "add", "amount": 1})
        for i in range(10)
    ]

    ctx = runtime.run_tick(deltas)
    show(ctx, "TEMPORAL FENCE RESULT")

    assert ctx.fenced is True
    assert len(ctx.deltas_accepted) == 3


def test_forced_breach_and_rollback():
    print("\n\n=== TEST 4: BREACH + ROLLBACK ===")

    class BreachKernel(TestZON4DKernel):
        def validate_state(self, state):
            # Force a validation failure to trigger breach
            return False

    runtime = EnginalityRuntime(
        anchor_store=TestAnchorStore(),
        ap_engine=TestAPEngine(),
        zon4d_kernel=BreachKernel(),
        config={},
    )

    deltas = [
        Delta("bad", "user", "world/value", 1, (1, 1), [], {"op": "add", "amount": 99})
    ]

    ctx = runtime.run_tick(deltas)
    show(ctx, "BREACH ROLLBACK RESULT")

    # Should have rolled back to immutable anchor state {value: 0}
    assert runtime.current_snapshot.zon4d_state["value"] == 0
    assert ctx.breached is True


# -------------------------------
# MAIN RUNNER
# -------------------------------
if __name__ == "__main__":
    test_ordering()
    test_mutation_and_inverse()
    test_too_many_deltas()
    test_forced_breach_and_rollback()

    print("\n\n=== ALL TESTS COMPLETED ===")
