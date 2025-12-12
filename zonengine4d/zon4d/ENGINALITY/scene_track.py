# scene_track.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from .task_types import Clip, ClipType, PerformanceTask, PerformanceTaskType


@dataclass
class Track:
    """
    SceneTrack Track: ordered Clips and layering metadata.
    """
    id: str
    priority: int = 1
    layering_mode: str = "blend"  # "additive" | "exclusive" | "blend"
    clips: List[Clip] = field(default_factory=list)
    _triggered_clips: set[str] = field(default_factory=set)

    def add_clip(self, clip: Clip) -> None:
        self.clips.append(clip)
        self.clips.sort(key=lambda c: c.start_time)

    def get_new_clips_in_window(self, start_t: float, end_t: float) -> List[Clip]:
        """
        Return clips whose start_time ∈ (start_t, end_t] and not yet triggered.
        """
        new_clips: List[Clip] = []
        for clip in self.clips:
            if clip.id in self._triggered_clips:
                continue
            if start_t < clip.start_time <= end_t:
                new_clips.append(clip)
                self._triggered_clips.add(clip.id)
        return new_clips


@dataclass
class SceneTrack:
    """
    Top-level performance orchestrator (PERFORMER_ENGINE_v1.0 §4).
    """
    id: str = "main_scene"
    active: bool = True
    scene_time: float = 0.0
    tick_to_scene_time: Dict[int, float] = field(default_factory=dict)
    tracks: Dict[str, Track] = field(default_factory=dict)
    # Simplified mix/camera placeholders
    mix_bus: dict = field(default_factory=dict)
    camera_state: dict = field(default_factory=dict)

    def get_or_create_track(self, track_id: str, priority: int = 1,
                            layering_mode: str = "blend") -> Track:
        if track_id not in self.tracks:
            self.tracks[track_id] = Track(
                id=track_id,
                priority=priority,
                layering_mode=layering_mode,
            )
        return self.tracks[track_id]

    def add_clip(self, track_id: str, clip: Clip,
                 priority: int = 1,
                 layering_mode: str = "blend") -> None:
        track = self.get_or_create_track(track_id, priority, layering_mode)
        track.add_clip(clip)

    def advance_time(self, delta_time: float, tick_id: int) -> Tuple[float, float]:
        """
        Advance SceneTrack time; register mapping tick → scene_time.
        Returns (prev_time, new_time) for window-based scheduling.
        """
        prev_time = self.scene_time
        self.scene_time += max(delta_time, 0.0)
        self.tick_to_scene_time[tick_id] = self.scene_time
        return prev_time, self.scene_time

    def gather_new_tasks_for_window(
        self,
        tick_id: int,
        window_start: float,
        window_end: float,
    ) -> list[PerformanceTask]:
        """
        Convert newly-started Clips in (window_start, window_end] into PerformanceTasks.
        This is the Clip → Task concretization layer.
        """
        tasks: list[PerformanceTask] = []

        for track in self.tracks.values():
            new_clips = track.get_new_clips_in_window(window_start, window_end)
            for clip in new_clips:
                pt_type = self._map_clip_type_to_task_type(clip.type)
                task = PerformanceTask(
                    id=f"{clip.id}@{tick_id}",
                    tick_id=tick_id,
                    scene_time=clip.start_time,
                    task_type=pt_type,
                    payload={
                        "track_id": track.id,
                        "clip_id": clip.id,
                        "duration": clip.duration,
                        "payload": clip.payload,
                        "tags": clip.tags,
                    },
                    priority=track.priority,
                )
                tasks.append(task)

        return tasks

    @staticmethod
    def _map_clip_type_to_task_type(clip_type: ClipType) -> PerformanceTaskType:
        if clip_type == ClipType.DIALOGUE:
            return PerformanceTaskType.DIALOGUE
        if clip_type == ClipType.AUDIO:
            return PerformanceTaskType.AUDIO
        if clip_type == ClipType.ANIMATION:
            return PerformanceTaskType.ANIMATION
        if clip_type == ClipType.CAMERA:
            return PerformanceTaskType.CAMERA
        if clip_type == ClipType.FX:
            return PerformanceTaskType.FX
        # Default fallback
        return PerformanceTaskType.FX
