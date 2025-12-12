# performance_harness.py
from __future__ import annotations
from typing import Dict, Any
from pprint import pprint
from .performer_engine import PerformerEngine


def fake_domain_views_for_tick(tick_id: int) -> Dict[str, Any]:
    """
    Minimal synthetic domain views to exercise PerformerEngine.
    """
    views: Dict[str, Any] = {}

    # Simple narrative script:
    if tick_id == 1:
        views["narrative_view"] = {
            "active_conversations": [
                {
                    "conversation_id": "intro",
                    "speaker_id": "keen",
                    "line_id": "intro_001",
                    "emotion": "curious",
                    "intensity": 0.7,
                    "duration": 2.5,
                }
            ]
        }
    elif tick_id == 3:
        views["narrative_view"] = {
            "active_conversations": [
                {
                    "conversation_id": "intro",
                    "speaker_id": "tran",
                    "line_id": "intro_002",
                    "emotion": "wary",
                    "intensity": 0.8,
                    "duration": 3.0,
                }
            ]
        }

    # Simple audio script:
    if tick_id == 0:
        views["audio_view"] = {
            "music_events": [
                {"asset_id": "bgm_theme_01", "action": "play", "duration": 30.0}
            ]
        }
    elif tick_id == 2:
        views.setdefault("audio_view", {})
        views["audio_view"].setdefault("sfx_events", []).append(
            {"asset_id": "ui_ping_01", "duration": 1.0}
        )

    # Simple animation script:
    if tick_id == 1:
        views["animation_view"] = {
            "body_events": [
                {
                    "rig_id": "keen_rig",
                    "pose_id": "idle_listen",
                    "duration": 1.5,
                    "layer": "base",
                }
            ]
        }
    elif tick_id == 3:
        views["animation_view"] = {
            "body_events": [
                {
                    "rig_id": "tran_rig",
                    "pose_id": "speak_emphatic",
                    "duration": 2.0,
                    "layer": "upper_body",
                }
            ],
            "facial_events": [
                {
                    "rig_id": "tran_rig",
                    "viseme_curve_id": "intro_002_visemes",
                    "duration": 2.0,
                    "audio_clip_id": "voice_intro_002",
                }
            ],
        }

    return views


def run_performance_sim():
    performer = PerformerEngine()
    tick_delta_time = 0.5  # half a second per Tick for demo

    for tick_id in range(0, 6):
        domain_views = fake_domain_views_for_tick(tick_id)
        tasks = performer.step(tick_id=tick_id, delta_time=tick_delta_time,
                               domain_views=domain_views)

        print("\n===============================")
        print(f"Tick {tick_id} – generated {len(tasks)} PerformanceTasks")
        print("===============================")
        for t in tasks:
            pprint(
                {
                    "id": t.id,
                    "tick_id": t.tick_id,
                    "scene_time": t.scene_time,
                    "type": t.task_type.value,
                    "priority": t.priority,
                    "payload": t.payload,
                }
            )


if __name__ == "__main__":
    run_performance_sim()
