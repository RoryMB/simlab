"""Isaac Lab Articulation wrapper for existing USD prims.

This module provides utilities to create Isaac Lab Articulation objects from
existing USD prims in the scene. This allows accessing Isaac Lab's physics
data (like Jacobians) without replacing the existing Isaac Sim Robot objects.

NOTE: Isaac Lab modules (isaaclab.*) are only available after Isaac Sim
has started and loaded its extensions. All imports are deferred to function
call time.
"""


def create_articulation_from_prim(prim_path: str, device: str = "cuda:0"):
    """Create an Isaac Lab Articulation from an existing USD prim.

    This wraps an existing robot prim (already in the scene) with Isaac Lab's
    Articulation class to access Jacobians and other physics data needed for
    differential IK.

    The key is using spawn=None in the config, which tells Isaac Lab to wrap
    an existing prim rather than spawning a new one.

    Args:
        prim_path: USD prim path of the existing articulation root
        device: Torch device for tensor computations (default: "cuda:0")

    Returns:
        Isaac Lab Articulation instance wrapping the existing prim

    Example:
        >>> # After creating Isaac Sim Robot pointing to /World/pf400
        >>> articulation = create_articulation_from_prim("/World/pf400")
        >>> jacobians = articulation.root_physx_view.get_jacobians()
    """
    # Deferred import - only available after Isaac Sim starts
    from isaaclab.assets import Articulation, ArticulationCfg

    cfg = ArticulationCfg(
        prim_path=prim_path,
        spawn=None,  # Don't spawn - wrap existing prim
    )

    articulation = Articulation(cfg=cfg)

    return articulation
