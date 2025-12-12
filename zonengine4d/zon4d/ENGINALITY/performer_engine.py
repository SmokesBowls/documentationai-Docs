# performer_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
from .scene_track import SceneTrack
from .dialogue_engine import DialogueEngine, DialogueEngineConfig
from .audio_engine import AudioEngine, AudioEngineConfig
from .animation_engine import AnimationEngine, AnimationEngineConfig
from .task_types import PerformanceTask


@dataclass
class PerformerEngineConfig:
    """
    High-level performer configuration.
    """
    dialogue: DialogueEngineConfig = DialogueEngineConfig()
    audio: AudioEngineConfig = AudioEngineConfig()
    animation: AnimationEngineConfig = AnimationEngineConfig()


class PerformerEngine:
    """
    PerfCore v0.1:
      - Maintains SceneTrack
      - Feeds domain views into sub-engines
      - Emits PerformanceTasks each Tick
    """

    def __init__(self, config: PerformerEngineConfig | None = None) -> None:
        self.config = config or PerformerEngineConfig()
        self.scene_track = SceneTrack(id="main_scene")
        self.dialogue_engine = DialogueEngine(self.config.dialogue)
        self.audio_engine = AudioEngine(self.config.audio)
        self.animation_engine = AnimationEngine(self.config.animation)

    def step(
        self,
        tick_id: int,
        delta_time: float,
        domain_views: Dict[str, Any],
    ) -> List[PerformanceTask]:
        """
        Perform one Performer tick (aligned to Runtime Tick).

        domain_views example:
        {
          "narrative_view": {...},
          "audio_view": {...},
          "animation_view": {...},
          "spatial_view": {...},     # ignored for now
          "ap_rules_view": {...},    # ignored for now
        }
        """
        if not self.scene_track.active:
            return []

        window_start, window_end = self.scene_track.advance_time(delta_time, tick_id)

        narrative_view = domain_views.get("narrative_view")
        audio_view = domain_views.get("audio_view")
        animation_view = domain_views.get("animation_view")

        # 1) Feed domain views into engines – they produce Clips
        self.dialogue_engine.update_from_narrative_view(
            self.scene_track, tick_id, window_end, narrative_view
        )
        self.audio_engine.update_from_audio_view(
            self.scene_track, tick_id, window_end, audio_view
        )
        self.animation_engine.update_from_animation_view(
            self.scene_track, tick_id, window_end, animation_view
        )

        # 2) Gather newly-started Clips in this time window → PerformanceTasks
        tasks = self.scene_track.gather_new_tasks_for_window(
            tick_id=tick_id,
            window_start=window_start,
            window_end=window_end,
        )

        # (In a full engine, here we might also apply priority-based filtering,
        # overload/degradation logic, etc.)

        return tasks
