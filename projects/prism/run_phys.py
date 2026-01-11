from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})


import numpy as np

from isaacsim.core.api import World
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.utils.prims import create_prim
from pxr import PhysxSchema

from slcore.common import utils
from slcore.common.primary_functions import create_robot, CollisionDetector, CUSTOM_ASSETS_ROOT_PATH


def create_scene_objects(world):
    """Create scene objects"""

    # Add default ground plane
    world.scene.add_default_ground_plane()

    # Create microplate at position (0.3, 0.3, 0.3)
    microplate_asset_path = CUSTOM_ASSETS_ROOT_PATH + "/labware/microplate/microplate.usd"
    add_reference_to_stage(
        usd_path=microplate_asset_path,
        prim_path="/World/microplate",
    )
    microplate_prim = world.stage.GetPrimAtPath("/World/microplate")
    # utils.set_xform_world_pose(microplate_prim, np.array([0.64, 0.5, 0.3]), np.array([1.0, 0.0, 0.0, 0.0]))
    utils.set_xform_world_pose(microplate_prim, np.array([0.80263, -0.37815, 0.27746]), np.array([1.0, 0.0, 0.0, 0.0]))

    # Enable collision detection for microplate
    contact_report_api = PhysxSchema.PhysxContactReportAPI.Apply(microplate_prim)
    contact_report_api.CreateThresholdAttr().Set(0.0)

    # Set contact offset for microplate
    physx_collision_api = PhysxSchema.PhysxCollisionAPI.Apply(microplate_prim)
    physx_collision_api.CreateContactOffsetAttr().Set(0.0)

    exchange_deck = create_prim(
        prim_path="/World/exchange_deck",
        prim_type="Cube",
        position=np.array([1.07, 0.75, -0.23]),
        scale=np.array([0.5, 0.5, 0.5]),
    )

    utils.add_collider_to_prim(exchange_deck)
    physx_collision_api = PhysxSchema.PhysxCollisionAPI.Apply(exchange_deck)
    physx_collision_api.CreateContactOffsetAttr().Set(0.0)

    # Create reference position markers (invisible Xforms for coordinate calculation)
    create_prim(
        prim_path="/World/target",
        prim_type="Xform",
        position=np.array([0.0, 0.0, 1.0]),
    )

    # PF400 location markers (from captured EE world poses)
    # These allow goto_prim to move the end effector to these world positions
    # Each location has a main position and a hover position (0.1m above for safe approach)
    HOVER_HEIGHT = 0.1

    pf400_locations = {
        # Home position (reset state)
        "home": {
            "position": [0.0, 0.0, 0.5],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        # OT-2 locations
        "safe_path_ot2bioalpha": {
            "position": [0.803, 0.0, 0.474],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        "ot2bioalpha_deck1_wide": {
            "position": [0.803, -0.378, 0.283],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        # Exchange deck locations
        "safe_path_exchange": {
            "position": [0.640, 0.300, 0.574],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        "exchange_deck_high_wide": {
            "position": [0.640, 0.300, 0.296],
            "orientation": [0.707, 0.0, 0.0, 0.707],
        },
        "exchange_deck_high_narrow": {
            "position": [0.640, 0.300, 0.276],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        # Sealer locations
        "safe_path_sealer": {
            "position": [0.061, -0.307, 0.548],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        "sealer_nest": {
            "position": [0.060, -0.307, 0.269],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        # Thermocycler locations (calibrated from joint angles)
        "safe_path_biometra3": {
            "position": [0.161, 0.387, 0.590],
            "orientation": [0.707, 0.0, 0.0, 0.707],
        },
        "bio_biometra3_nest": {
            "position": [0.161, 0.387, 0.333],
            "orientation": [0.707, 0.0, 0.0, 0.707],
        },
        # Peeler locations (calibrated from joint angles)
        "safe_path_peeler": {
            "position": [-0.284, -0.342, 0.568],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        "peeler_nest": {
            "position": [-0.285, -0.342, 0.269],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        # Hidex locations (calibrated from joint angles)
        "safe_path_hidex": {
            "position": [-0.279, 0.0, 0.408],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        "hidex_geraldine_high_nest": {
            "position": [-0.401, 0.229, 0.210],
            "orientation": [0.707, 0.0, 0.0, 0.707],
        },
    }

    for name, pose in pf400_locations.items():
        # Create main location marker
        create_prim(
            prim_path=f"/World/locations/{name}",
            prim_type="Xform",
            position=np.array(pose["position"]),
            orientation=np.array(pose["orientation"]),
        )
        # Create hover marker (same position but higher z)
        hover_pos = pose["position"].copy() if isinstance(pose["position"], list) else list(pose["position"])
        hover_pos[2] += HOVER_HEIGHT
        create_prim(
            prim_path=f"/World/locations/{name}_hover",
            prim_type="Xform",
            position=np.array(hover_pos),
            orientation=np.array(pose["orientation"]),
        )

def main():
    # Create world
    world = World(stage_units_in_meters=1.0)

    # Create scene objects (including microplates and platforms)
    create_scene_objects(world)

    # Robot configuration
    robots_config = [
        {
            "prim_path": "/World/ot2_0",
            "name": "ot2_0",
            "type": "ot2",
            "port": 5556,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/robots/Opentrons/OT-2/OT-2.usd",
            "position": [0.67, -0.55, 0.2],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "prim_path": "/World/pf400_0",
            "name": "pf400_0",
            "type": "pf400",
            "port": 5557,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/robots/Brooks/PF400/PF400.usd",
            "position": [0.0, 0.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },

        {
            "prim_path": "/World/sealer_0",
            "name": "sealer_0",
            "type": "sealer",
            "port": 5558,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/robots/Azenta/a4SSealer/a4SSealer.usda",
            "position": [0.06, -0.675, 0.125],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "prim_path": "/World/peeler_0",
            "name": "peeler_0",
            "type": "peeler",
            "port": 5559,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/robots/Azenta/XPeel/XPeel.usda",
            "position": [-0.4, -0.625, 0.125],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "prim_path": "/World/thermocycler_0",
            "name": "thermocycler_0",
            "type": "thermocycler",
            "port": 5560,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/robots/AnalytikJena/Biometra/Biometra.usda",
            "position": [0.16, 0.4, 0.125],
            "orientation": [0.0, 0.0, 0.0, 1.0],
        },
        {
            "prim_path": "/World/hidex_0",
            "name": "hidex_0",
            "type": "hidex",
            "port": 5561,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/robots/Hidex/SenseMicroplateReader/SenseMicroplateReader.usda",
            "position": [-0.4, 0.55, 0.125],
            "orientation": [0.0, 0.0, 0.0, 1.0],
        },
    ]

    # Create robots and their ZMQ servers
    zmq_servers = {}
    for config in robots_config:
        robot, zmq_server = create_robot(simulation_app, world, config)
        zmq_servers[config["name"]] = zmq_server

    # Reset world to initialize physics
    world.reset()

    # Set up collision detection (MUST be after world.reset())
    _collision_detector = CollisionDetector(zmq_servers)

    # Start all ZMQ servers
    for server in zmq_servers.values():
        server.start_server()

    # Run simulation loop
    try:
        while simulation_app.is_running():
            # Call robot server update methods each frame
            for server in zmq_servers.values():
                if hasattr(server, 'update'):
                    server.update()

            # Step the simulation
            world.step(render=True)
    except KeyboardInterrupt:
        pass

    simulation_app.close()

if __name__ == "__main__":
    main()
