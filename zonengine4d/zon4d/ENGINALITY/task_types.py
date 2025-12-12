# task_types.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any


class PerformanceTaskType(Enum):
    RENDER = "render"
    AUDIO = "audio"
    DIALOGUE = "dialogue"
    ANIMATION = "animation"
    CAMERA = "camera"
    FX = "fx"


@dataclass
class PerformanceTask:
    """
    Core ABI task unit for Performer → platform.

    Mirrors PERFORMER_ENGINE_v1.0 §8.1:
      - id
      - tick_id
      - scene_time
      - task_type
      - payload
      - priority
    """
    id: str
    tick_id: int
    scene_time: float
    task_type: PerformanceTaskType
    payload: Dict[str, Any]
    priority: int = 1


class ClipType(Enum):
    AUDIO = "audio"
    DIALOGUE = "dialogue"
    ANIMATION = "animation"
    CAMERA = "camera"
    FX = "fx"


@dataclass
class Clip:
    """
    Generic Clip as per spec §4.3.
    """
    id: str
    type: ClipType
    start_time: float
    duration: float
    payload: Dict[str, Any] = field(default_factory=dict)
    easing: Any = None          # can be extended later
    tags: list[str] = field(default_factory=list)
