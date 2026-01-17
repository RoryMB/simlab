"""Isaac Sim entry point for scaling-mvp project with 5 parallel environments."""

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import numpy as np
from isaacsim.core.api import World

from slcore.common.primary_functions import create_parallel_robots, CollisionDetector
from slcore.common.parallel_config import ParallelConfig
from slcore.robots.common.config import CUSTOM_ASSETS_ROOT_PATH


def main():
    """Main entry point for parallel environment simulation."""
    # Create world
    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()

    # Parallel environment configuration
    parallel_config = ParallelConfig(
        num_envs=5,
        spacing=10.0,  # 10 meters between environments
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
