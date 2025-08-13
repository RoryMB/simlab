from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

from isaacsim.core.api import World

from primary_functions import create_robot, CUSTOM_ASSETS_ROOT_PATH


def create_scene_objects(world):
    """Create scene objects"""

    # Add default ground plane
    world.scene.add_default_ground_plane()


def main():
    # Create world
    world = World(stage_units_in_meters=1.0)

    # Create scene objects (including microplates and platforms)
    create_scene_objects(world)

    # Robot configuration
    robots_config = [
        {
            "name": "ot2_1",
            "type": "ot2",
            "port": 5556,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/ot2.usda",
            "position": [0.0, 0.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
    ]

    # Create robots and their ZMQ servers
    zmq_servers = []
    for config in robots_config:
        robot, zmq_server = create_robot(simulation_app, world, config)
        zmq_servers.append(zmq_server)

    # Reset world to initialize physics
    world.reset()

    # Start all ZMQ servers
    for server in zmq_servers:
        server.start_server()

    # Run simulation loop
    try:
        while simulation_app.is_running():
            # Call robot server update methods each frame
            for server in zmq_servers:
                if hasattr(server, 'update'):
                    server.update()

            # Step the simulation
            world.step(render=True)
    except KeyboardInterrupt:
        pass

    simulation_app.close()

if __name__ == "__main__":
    main()
