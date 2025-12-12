# domain_views.py
"""
Domain View Generation (Step 10)

Converts ZON4D canonical state into domain-specific views that
Performer Engine can consume (narrative/audio/animation/etc).

This implements Step 7 (Hydration) from RUNTIME_LOOP_v0.1 spec.
"""

from typing import Dict, Any


def generate_domain_views_from_state(state: Dict[str, Any], tick_id: int) -> Dict[str, Any]:
    """
    Convert ZON4D state into domain views that Performer can consume.
    
    This simulates Step 7 (Hydration) by extracting narrative/audio/animation
    events from the current state.
    
    Args:
        state: ZON4D canonical state (dict of entity_ref → payload)
        tick_id: Current tick ID (for context/logging)
    
    Returns:
        Dict of domain views (narrative_view, audio_view, animation_view, etc.)
    """
    views: Dict[str, Any] = {}

    # ===== NARRATIVE VIEW =====
    active_speaker = state.get("narrative/active_speaker")
    active_line = state.get("narrative/active_line")
    emotion = state.get("narrative/emotion")
    intensity = state.get("narrative/intensity")

    if active_speaker and active_line:
        views["narrative_view"] = {
            "active_conversations": [{
                "conversation_id": state.get("narrative/conversation_id", "main"),
                "speaker_id": active_speaker,
                "line_id": active_line,
                "emotion": emotion or "neutral",
                "intensity": float(intensity) if intensity else 0.5,
                "duration": float(state.get("narrative/duration", 2.5)),
            }]
        }

    # ===== AUDIO VIEW =====
    music_asset = state.get("audio/music")
    music_action = state.get("audio/music_action", "play")
    sfx_asset = state.get("audio/sfx")

    music_events = []
    sfx_events = []

    if music_asset:
        music_events.append({
            "asset_id": music_asset,
            "action": music_action,
            "duration": float(state.get("audio/music_duration", 10.0)),
            "volume_db": float(state.get("audio/music_volume", 0.0)),
        })

    if sfx_asset:
        sfx_events.append({
            "asset_id": sfx_asset,
            "duration": float(state.get("audio/sfx_duration", 1.0)),
            "volume_db": float(state.get("audio/sfx_volume", 0.0)),
        })

    if music_events or sfx_events:
        views["audio_view"] = {
            "music_events": music_events,
            "sfx_events": sfx_events,
        }

    # ===== ANIMATION VIEW =====
    rig_id = state.get("animation/rig")
    pose_id = state.get("animation/pose")
    pose_layer = state.get("animation/layer", "base")

    # Facial/viseme data
    viseme_curve = state.get("animation/viseme_curve")
    linked_audio = state.get("animation/linked_audio")

    body_events = []
    facial_events = []

    if rig_id and pose_id:
        body_events.append({
            "rig_id": rig_id,
            "pose_id": pose_id,
            "duration": float(state.get("animation/duration", 2.0)),
            "layer": pose_layer,
            "blend_in": float(state.get("animation/blend_in", 0.1)),
            "blend_out": float(state.get("animation/blend_out", 0.1)),
        })

    if rig_id and viseme_curve:
        facial_events.append({
            "rig_id": rig_id,
            "viseme_curve_id": viseme_curve,
            "duration": float(state.get("animation/viseme_duration", 2.0)),
            "audio_clip_id": linked_audio,
            "offset": float(state.get("animation/viseme_offset", 0.0)),
        })

    if body_events or facial_events:
        views["animation_view"] = {
            "body_events": body_events,
            "facial_events": facial_events,
        }

    # ===== SPATIAL VIEW (stub for future) =====
    # This would extract 3D positions, camera targets, etc.
    # For now, just pass through any spatial/* keys
    spatial_data = {k: v for k, v in state.items() if k.startswith("spatial/")}
    if spatial_data:
        views["spatial_view"] = spatial_data

    # ===== AP RULES VIEW (stub for future) =====
    # This would extract active AP constraints
    ap_data = {k: v for k, v in state.items() if k.startswith("ap/")}
    if ap_data:
        views["ap_rules_view"] = ap_data

    return views
