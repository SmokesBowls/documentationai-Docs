#!/usr/bin/env bash
set -euo pipefail

# Make sure folders exist
mkdir -p ZW-S ZW-H ZON4D TEMPORAL META

echo "=== Moving ZW-S ==="
mv -vn "03_ZW-S_SPEC_v1.0.txt" ZW-S/ 2>/dev/null || true
mv -vn "ZW-S Specification (Soft ZW Language) (1).txt" ZW-S/ 2>/dev/null || true

echo "=== Moving ZW-H ==="
mv -vn "05_ZW-H_SPEC_v0.1_SECTION_1_TYPES.txt" ZW-H/ 2>/dev/null || true
mv -vn "Appendix C1 — Override Handling Performance Spec.txt" ZW-H/ 2>/dev/null || true
mv -vn "Generate ZW-H Spec v0.1 (Hard ZW Schema Language).txt" ZW-H/ 2>/dev/null || true
mv -vn "ZW_H_OVERRIDE_MODEL.txt" ZW-H/ 2>/dev/null || true
mv -vn "ZW-H_SECTION_5_PRE-SPEC_PROMPT.txt" ZW-H/ 2>/dev/null || true
mv -vn "ZW-H SPEC v0.1 — SECTION 1 TYPES (FINAL)_1.txt" ZW-H/ 2>/dev/null || true
mv -vn "ZW_H_SPEC_v0.1_SECTION_1_TYPES.txt" ZW-H/ 2>/dev/null || true
mv -vn "ZW-H_SPEC_v0.1_SECTION_5_MAPPING_PROMPT.txt" ZW-H/ 2>/dev/null || true
mv -vn "ZW-H SPEC v0.1 STATUS.txt" ZW-H/ 2>/dev/null || true
mv -vn "ZW_H_Transition_Dialogue.txt" ZW-H/ 2>/dev/null || true
mv -vn "ZW_H_v0.1_Quick_Refresher.txt" ZW-H/ 2>/dev/null || true

echo "=== Moving ZON4D core + sections ==="
mv -vn "ZON4D_SPEC_v0.1.txt" ZON4D/ 2>/dev/null || true
mv -vn "ZON4D_Temporal_Law_v1.0.zwdoc.txt" ZON4D/ 2>/dev/null || true
mv -vn "Appendix A — Temporal Data Model.txt" ZON4D/ 2>/dev/null || true
mv -vn "Appendix B — ZON4D v0.1 Specification.txt" ZON4D/ 2>/dev/null || true
mv -vn "APPENDIX C — Examples & Edge Cases.txt" ZON4D/ 2>/dev/null || true

mv -vn "SECTION 13 — Dialogue Intensity Tracks.txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 18 — Facial Animation & Visemes.txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 19- Audio Envelopes.txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 20 — AP Hooks on ZON4D.txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 22 - Scene_Track Engine.txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 23-Temporal Query Protocol Micro-Spec, including.txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 24 - Temporal Consistency & Kernel Arbitration law.txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 31 — Temporal Syncpoints & Hash Anchors.txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 32 — Canonical Hashing Rules (HASH32 Spec) .txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 33 — Snapshot Diff & Drift Metrics .txt" ZON4D/ 2>/dev/null || true

mv -vn "SECTION_34_SNAPSHOT_MERGE_PROTOCOL.txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION 34 Temporal Snapshot Consolidation Layer (TSCL).txt" ZON4D/ 2>/dev/null || true
mv -vn "SECTION_34_TEMPORAL_SNAPSHOT_CONSOLIDATION_LAYER.txt.txt" ZON4D/ 2>/dev/null || true
mv -vn "34 – Temporal Snapshot Consolidation Layer.txt" ZON4D/ 2>/dev/null || true

mv -vn "35.txt" ZON4D/ 2>/dev/null || true
mv -vn "36.txt" ZON4D/ 2>/dev/null || true
mv -vn "37.txt" ZON4D/ 2>/dev/null || true
mv -vn "38.txt" ZON4D/ 2>/dev/null || true
mv -vn "39 – Temporal Deltas & Patch Propagation.txt" ZON4D/ 2>/dev/null || true
mv -vn "39.txt" ZON4D/ 2>/dev/null || true
mv -vn "40.txt" ZON4D/ 2>/dev/null || true
mv -vn "41.2 (1).txt" ZON4D/ 2>/dev/null || true
mv -vn "43.txt" ZON4D/ 2>/dev/null || true
mv -vn "49-TEMPORAL LOCKSTEP ABI (.txt" ZON4D/ 2>/dev/null || true
mv -vn "4D STATE COMPRESSION & DELTA PACKING (ZONB v2).txt" ZON4D/ 2>/dev/null || true
mv -vn "24 — Oracle Law - ZON4D-AP-Kernal enforcement.txt" ZON4D/ 2>/dev/null || true
mv -vn "Ap-ZON4D Integration Supplement tc state binding layer.txt" ZON4D/ 2>/dev/null || true
mv -vn "Cross-Domain Conflict Resolution (AP-ZON4D).txt" ZON4D/ 2>/dev/null || true
mv -vn "Predictive Sandbox & Temporal Query Isolation..txt" ZON4D/ 2>/dev/null || true

echo "=== Moving TEMPORAL-law satellites ==="
mv -vn "TEMPORAL ANCHORS (Soft, Hard, Immutable).txt" TEMPORAL/ 2>/dev/null || true
mv -vn "TEMPORAL ENTROPY & DRIFT STABILIZATION  (ZON4D Temporal Law, Part VI).txt" TEMPORAL/ 2>/dev/null || true
mv -vn "Temporal Error Surfaces & Discontinuity Zones.txt" TEMPORAL/ 2>/dev/null || true
mv -vn "TEMPORAL INVALIDATION & CACHE PURGE RULES.txt" TEMPORAL/ 2>/dev/null || true
mv -vn "Temporal Merge & Retcon Rules.txt" TEMPORAL/ 2>/dev/null || true
mv -vn "Temporal Topology & Multi-Track Synchronization.txt" TEMPORAL/ 2>/dev/null || true

echo "=== Moving META / notes / options ==="
mv -vn "25 again.txt" META/ 2>/dev/null || true
mv -vn "25 clarification options.txt" META/ 2>/dev/null || true
mv -vn "25 continued.txt" META/ 2>/dev/null || true
mv -vn "30 (1).txt" META/ 2>/dev/null || true
mv -vn "7.6 — Forbidden in Output (THIS file) 7.7 — Performance Contract (.txt" META/ 2>/dev/null || true
mv -vn "APPENDIX D — Author Notes_Development map.txt" META/ 2>/dev/null || true
mv -vn "CURRENT STATUS SAFE SPEC PHASE.txt" META/ 2>/dev/null || true
mv -vn "CURRENT STATUS SAFE SPEC PHASE (1).txt" META/ 2>/dev/null || true
mv -vn "META_ZWH_BLUEPRINT_PHASE_LOCK.txt" META/ 2>/dev/null || true
mv -vn "section 24.txt" META/ 2>/dev/null || true

echo "=== Done. Remaining files (if any) need manual eyeballing. ==="
ls
