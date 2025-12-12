# dialogue_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
from .scene_track import SceneTrack
from .task_types import Clip, ClipType


@dataclass
class DialogueEngineConfig:
    """
    Tunables for Dialogue → Clip mapping.
    """
    default_track_id: str = "dialogue"
    default_duration: float = 2.0  # seconds, if not provided in narrative_view


class DialogueEngine:
    """
    Dialogue → DialogueClip generator.
    Consumes narrative_view (domain view) and writes Clips into SceneTrack.
    """

    def __init__(self, config: DialogueEngineConfig | None = None) -> None:
        self.config = config or DialogueEngineConfig()

    def update_from_narrative_view(
        self,
        scene_track: SceneTrack,
        tick_id: int,
        scene_time: float,
        narrative_view: Dict[str, Any] | None,
    ) -> None:
        """
        narrative_view schema (loose, for v0.1):

        {
          "active_conversations": [
            {
              "conversation_id": str,
              "speaker_id": str,
              "line_id": str,
              "emotion": str,
              "intensity": float,
              "duration": float | None
            },
            ...
          ]
        }
        """
        if not narrative_view:
            return

        conversations = narrative_view.get("active_conversations", [])
        for conv in conversations:
            line_id = conv["line_id"]
            speaker_id = conv["speaker_id"]
            duration = float(conv.get("duration") or self.config.default_duration)
            emotion = conv.get("emotion", "neutral")
            intensity = float(conv.get("intensity", 0.5))

            clip_id = f"dlg_{line_id}_t{tick_id}"

            payload = {
                "line_id": line_id,
                "speaker_id": speaker_id,
                "emotion": emotion,
                "intensity": intensity,
                "conversation_id": conv.get("conversation_id"),
            }

            clip = Clip(
                id=clip_id,
                type=ClipType.DIALOGUE,
                start_time=scene_time,
                duration=duration,
                payload=payload,
                tags=["dialogue"],
            )

            scene_track.add_clip(
                track_id=self.config.default_track_id,
                clip=clip,
                priority=0,  # dialogue = critical by default
                layering_mode="exclusive",
            )
