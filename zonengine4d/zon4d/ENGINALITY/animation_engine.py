# animation_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from .scene_track import SceneTrack
from .task_types import Clip, ClipType


@dataclass
class AnimationEngineConfig:
    animation_track_id: str = "animation"
    facial_track_id: str = "facial"


class AnimationEngine:
    """
    Animation & facial/viseme handler.
    Consumes animation_view and produces ANIMATION Clips.
    """

    def __init__(self, config: AnimationEngineConfig | None = None) -> None:
        self.config = config or AnimationEngineConfig()

    def update_from_animation_view(
        self,
        scene_track: SceneTrack,
        tick_id: int,
        scene_time: float,
        animation_view: Dict[str, Any] | None,
    ) -> None:
        """
        animation_view schema (v0.1, loose):

        {
          "body_events": [
            { "rig_id": str, "pose_id": str, "duration": float, "layer": "base"|"upper_body"|"additive" },
          ],
          "facial_events": [
            { "rig_id": str, "viseme_curve_id": str, "duration": float, "audio_clip_id": str },
          ]
        }
        """
        if not animation_view:
            return

        for ev in animation_view.get("body_events", []):
            self._create_body_clip(scene_track, tick_id, scene_time, ev)

        for ev in animation_view.get("facial_events", []):
            self._create_facial_clip(scene_track, tick_id, scene_time, ev)

    def _create_body_clip(
        self,
        scene_track: SceneTrack,
        tick_id: int,
        scene_time: float,
        ev: Dict[str, Any],
    ) -> None:
        rig_id = ev["rig_id"]
        pose_id = ev["pose_id"]
        duration = float(ev.get("duration") or 0.5)
        layer = ev.get("layer", "base")

        payload = {
            "rig_id": rig_id,
            "pose_asset_id": pose_id,
            "blend_in": float(ev.get("blend_in", 0.1)),
            "blend_out": float(ev.get("blend_out", 0.1)),
            "layer": layer,
            "weight": float(ev.get("weight", 1.0)),
        }

        clip_id = f"anim_{rig_id}_{pose_id}_t{tick_id}"

        clip = Clip(
            id=clip_id,
            type=ClipType.ANIMATION,
            start_time=scene_time,
            duration=duration,
            payload=payload,
            tags=["body"],
        )

        scene_track.add_clip(
            track_id=self.config.animation_track_id,
            clip=clip,
            priority=1,
            layering_mode="blend",
        )

    def _create_facial_clip(
        self,
        scene_track: SceneTrack,
        tick_id: int,
        scene_time: float,
        ev: Dict[str, Any],
    ) -> None:
        rig_id = ev["rig_id"]
        viseme_curve_id = ev["viseme_curve_id"]
        duration = float(ev.get("duration") or 0.5)

        payload = {
            "rig_id": rig_id,
            "viseme_curve_id": viseme_curve_id,
            "linked_audio_clip_id": ev.get("audio_clip_id"),
            "offset": float(ev.get("offset", 0.0)),
        }

        clip_id = f"vis_{rig_id}_{viseme_curve_id}_t{tick_id}"

        clip = Clip(
            id=clip_id,
            type=ClipType.ANIMATION,  # still ANIMATION; facial vs body via tags
            start_time=scene_time,
            duration=duration,
            payload=payload,
            tags=["facial", "viseme"],
        )

        scene_track.add_clip(
            track_id=self.config.facial_track_id,
            clip=clip,
            priority=0,  # facial is critical when tied to dialogue
            layering_mode="additive",
        )
