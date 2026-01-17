"""Isaac Sim entry point for scaling-mvp project with 5 parallel environments."""

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import numpy as np
from isaacsim.core.api import World
from isaacsim.core.utils.prims import create_prim

from slcore.common.primary_functions import create_parallel_robots, CollisionDetector
from slcore.common.parallel_config import ParallelConfig
from slcore.robots.common.config import CUSTOM_ASSETS_ROOT_PATH


# PF400 location markers for calibration and workflow execution
# These are world coordinates where the PF400 end effector should move to
# Each location has a main position and a hover position above for safe vertical approach
#
# Values calibrated from projects/prism/run_phys.py
HOVER_HEIGHT = 0.1  # 10cm above target for auto-generated hover positions

PF400_LOCATIONS = {
    # Home position (safe neutral position)
    "home": {
        "position": [0.0, 0.0, 0.5],
        "orientation": [1.0, 0.0, 0.0, 0.0],
    },
    # Staging area (intermediate position for plate transfers)
    "staging": {
        "position": [0.3, 0.0, 0.3],
        "orientation": [1.0, 0.0, 0.0, 0.0],
    },
    # Thermocycler nest (calibrated from prism bio_biometra3_nest)
    # Device at [0.16, 0.4, 0.125] rotated 180° Z
    "thermocycler_nest": {
        "position": [0.161, 0.387, 0.333],
        "orientation": [0.707, 0.0, 0.0, 0.707],  # 90° Z rotation
    },
    # Peeler nest (calibrated from prism peeler_nest)
    # Device at [-0.4, -0.625, 0.125], tray is at different position
    "peeler_nest": {
        "position": [-0.285, -0.342, 0.269],
        "orientation": [-0.707, 0.0, 0.0, 0.707],  # -90° Z rotation
    },
}


def create_location_markers(env_id: int, offset: np.ndarray):
    """Create PF400 location xform markers for an environment.

    Args:
        env_id: Environment ID for naming
        offset: [x, y, z] offset for this environment
    """
    for name, pose in PF400_LOCATIONS.items():
        # Calculate offset position
        pos = np.array(pose["position"]) + offset

        # Create main location marker
        create_prim(
            prim_path=f"/World/env_{env_id}/locations/{name}",
            prim_type="Xform",
            position=pos,
            orientation=np.array(pose["orientation"]),
        )

        # Create hover marker (same position but higher z)
        hover_pos = pos.copy()
        hover_pos[2] += HOVER_HEIGHT
        create_prim(
            prim_path=f"/World/env_{env_id}/locations/{name}_hover",
            prim_type="Xform",
            position=hover_pos,
            orientation=np.array(pose["orientation"]),
        )


def main():
    """Main entry point for parallel environment simulation."""
    # Create world
    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()

    # Parallel environment configuration
    parallel_config = ParallelConfig(
        num_envs=5,
        spacing=5.0,  # 5 meters between environments
        zmq_port=5555,
    )

    # Base robot configuration (will be cloned with offsets for each environment)
    base_robots_config = [
        {
            "type": "pf400",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Brooks/PF400/PF400.usd"),
            "position": [0.0, 0.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "type": "peeler",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Azenta/XPeel/XPeel.usd"),
            "position": [-0.4, -0.625, 0.125],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "type": "thermocycler",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/AnalytikJena/Biometra/Biometra.usd"),
            "position": [0.16, 0.4, 0.125],
            "orientation": [0.0, 0.0, 0.0, 1.0],
        },
    ]

    # Create all parallel environments
    router_server, handlers = create_parallel_robots(
        simulation_app,
        world,
        base_robots_config,
        parallel_config,
    )

    # Create location markers for each environment (for PF400 calibration and goto_prim)
    for env_id in range(parallel_config.num_envs):
        offset = parallel_config.get_offset(env_id)
        create_location_markers(env_id, offset)

    # Reset world after all robots are added
    world.reset()

    # Set up collision detection across all environments
    collision_detector = CollisionDetector(handlers)

    # Start multiplexed ZMQ ROUTER server
    router_server.start_server()

    print(f"\nScaling MVP: {parallel_config.num_envs} parallel environments running")
    print(f"ZMQ ROUTER server listening on port {parallel_config.zmq_port}")
    print(f"Total handlers registered: {len(handlers)}")
    print("\nPress Ctrl+C to stop\n")

    # Simulation loop
    try:
        while simulation_app.is_running():
            # Update all robot handlers
            for handler in handlers.values():
                handler.update()

            # Step simulation
            world.step(render=True)
    except KeyboardInterrupt:
        print("\nShutting down...")

    simulation_app.close()


if __name__ == "__main__":
    main()
