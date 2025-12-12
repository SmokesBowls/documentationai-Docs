# audio_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from .scene_track import SceneTrack
from .task_types import Clip, ClipType


@dataclass
class AudioEngineConfig:
    music_track_id: str = "music"
    sfx_track_id: str = "sfx"
    voice_track_id: str = "voice"


class AudioEngine:
    """
    Audio domain handler.
    Consumes audio_view and produces Clips for music / sfx / voice.
    """

    def __init__(self, config: AudioEngineConfig | None = None) -> None:
        self.config = config or AudioEngineConfig()

    def update_from_audio_view(
        self,
        scene_track: SceneTrack,
        tick_id: int,
        scene_time: float,
        audio_view: Dict[str, Any] | None,
    ) -> None:
        """
        audio_view schema (v0.1, loose):

        {
          "music_events": [
            { "asset_id": str, "action": "play"|"stop", "duration": float | None },
          ],
          "sfx_events": [
            { "asset_id": str, "duration": float | None, "spatial": {...}? },
          ]
        }
        """
        if not audio_view:
            return

        for ev in audio_view.get("music_events", []):
            self._create_audio_clip(
                scene_track=scene_track,
                track_id=self.config.music_track_id,
                base_id="music",
                tick_id=tick_id,
                scene_time=scene_time,
                event=ev,
                default_duration=5.0,
            )

        for ev in audio_view.get("sfx_events", []):
            self._create_audio_clip(
                scene_track=scene_track,
                track_id=self.config.sfx_track_id,
                base_id="sfx",
                tick_id=tick_id,
                scene_time=scene_time,
                event=ev,
                default_duration=1.0,
            )

    def _create_audio_clip(
        self,
        scene_track: SceneTrack,
        track_id: str,
        base_id: str,
        tick_id: int,
        scene_time: float,
        event: Dict[str, Any],
        default_duration: float,
    ) -> None:
        asset_id = event["asset_id"]
        duration = float(event.get("duration") or default_duration)

        payload = {
            "asset_id": asset_id,
            "channel": base_id,
            "volume_db": float(event.get("volume_db", 0.0)),
            "pan": float(event.get("pan", 0.0)),
            "pitch_semitones": float(event.get("pitch_semitones", 0.0)),
            "envelope": event.get("envelope"),
            "spatial": event.get("spatial"),
            "action": event.get("action", "play"),
        }

        clip_id = f"{base_id}_{asset_id}_t{tick_id}"

        clip = Clip(
            id=clip_id,
            type=ClipType.AUDIO,
            start_time=scene_time,
            duration=duration,
            payload=payload,
            tags=[base_id],
        )

        scene_track.add_clip(
            track_id=track_id,
            clip=clip,
            priority=1,  # high but below dialogue
            layering_mode="additive",
        )
