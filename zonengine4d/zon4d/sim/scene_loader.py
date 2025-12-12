# -------------------------------------------------------------
# EngAIn Scene Loader
# -------------------------------------------------------------
# Loads a world_scene into Spatial3D + Behavior3D.
# -------------------------------------------------------------

from spatial3d_adapter import Spatial3DStateViewAdapter
from behavior_adapter import BehaviorStateView
from behavior_mr import BehaviorStateType

class SceneLoader:
    def __init__(self, spatial: Spatial3DStateViewAdapter, behavior: BehaviorStateView):
        self.spatial = spatial
        self.behavior = behavior

    def load_scene(self, scene_dict):
        print(f"[SCENE LOADER] Loading scene: {scene_dict['id']}")

        # -----------------------------------------------------
        # 1. Spawn all entities
        # -----------------------------------------------------
        for e in scene_dict["entities"]:
            eid = e["id"]
            pos = e["pos"]
            tags = e.get("tags", [])
            radius = e.get("radius", 0.5)
            
            # Use convenience API (Pattern B)
            self.spatial.spawn_entity(
                entity_id=eid,
                pos=pos,
                radius=radius,
                tags=tags
            )

            # Behavior configuration
            if "behavior" in e:
                beh = e["behavior"]
                mode_str = beh.get("mode", "idle")
                patrol = beh.get("patrol_points", [])
                
                # Convert mode string to BehaviorStateType
                try:
                    mode = BehaviorStateType(mode_str)
                except ValueError:
                    mode = BehaviorStateType.IDLE

                self.behavior.add_behavior_entity(
                    eid,
                    initial_state=mode,
                    patrol_points=patrol
                )

        print("[SCENE LOADER] Scene loaded successfully.")
