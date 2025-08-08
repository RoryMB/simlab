#!/usr/bin/env python3

"""
run_ppc.py - Pick and Place Control Demo
Modern Isaac Sim script with hardcoded scene setup inspired by simple_plate_transfer.usda
Integrates robot control into simulation loop for collision detection while maintaining
per-robot ZMQ server architecture
"""

from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

import sys
from pathlib import Path
import numpy as np

from isaacsim.core.api import World
from isaacsim.core.api.robots import Robot
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.storage.native import get_assets_root_path
from isaacsim.core.utils.prims import create_prim, get_prim_at_path
from isaacsim.core.utils.stage import get_current_stage

# Collision detection
from omni.physx import get_physx_simulation_interface
from omni.physx.bindings._physx import ContactEventType
from omni.physx.scripts.physicsUtils import PhysicsSchemaTools
from pxr import PhysxSchema

import utils
from zmq_pf400_server import ZMQ_PF400_Server

CUSTOM_ASSETS_ROOT_PATH = str(Path("../../assets").resolve())

NVIDIA_ASSETS_ROOT_PATH = get_assets_root_path()
if NVIDIA_ASSETS_ROOT_PATH is None:
    print("Error: Could not find Isaac Sim assets folder")
    simulation_app.close()
    sys.exit()

def create_hardcoded_scene(world):
    """Create scene objects hardcoded based on simple_plate_transfer.usda"""
    
    # Add default ground plane
    world.scene.add_default_ground_plane()
    
    # Create PF400 robot
    pf400_asset_path = CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/pf400.usda"
    add_reference_to_stage(
        usd_path=pf400_asset_path,
        prim_path="/World/pf400",
    )
    
    # Position PF400 at origin (same as simple_plate_transfer.usda)
    pf400_prim = world.stage.GetPrimAtPath("/World/pf400")
    utils.set_prim_world_pose(pf400_prim, position=np.array([0.0, 0.0, 0.0]))
    
    # Create microplate at position (0.3, 0.3, 0.3)
    microplate_asset_path = CUSTOM_ASSETS_ROOT_PATH + "/temp/objects/microplate.usda"
    add_reference_to_stage(
        usd_path=microplate_asset_path,
        prim_path="/World/microplate",
    )
    microplate_prim = world.stage.GetPrimAtPath("/World/microplate")
    utils.set_prim_world_pose(microplate_prim, position=np.array([0.3, 0.3, 0.3]))
    
    # Create platform cubes (as collision objects and targets)
    # Platform 1 at (0.73, 0.75, -0.205)
    platform1_prim = create_prim(
        prim_path="/World/platform1",
        prim_type="Cube",
        position=np.array([0.73, 0.75, -0.205]),
        scale=np.array([1.0, 1.0, 1.0]),
    )
    
    # Platform 2 at (0.73, -0.75, -0.205) 
    platform2_prim = create_prim(
        prim_path="/World/platform2",
        prim_type="Cube",
        position=np.array([0.73, -0.75, -0.205]),
        scale=np.array([1.0, 1.0, 1.0]),
    )
    
    # Collision test cube at (0, -1.8, 0.5)
    collision_cube_prim = create_prim(
        prim_path="/World/collision_cube",
        prim_type="Cube", 
        position=np.array([0.0, -1.8, 0.5]),
        scale=np.array([1.0, 1.0, 1.0]),
    )
    
    # Create reference position markers (invisible prims for navigation)
    # High position at (0.24454794450064865, 1.1102230246251565e-14, 1.04338924256884)
    high_prim = create_prim(
        prim_path="/World/high",
        prim_type="Xform",
        position=np.array([0.245, 0.0, 1.043]),
    )
    
    # Side position at (0.3, 0.3, 0.3) - same as microplate for pickup
    side_prim = create_prim(
        prim_path="/World/side", 
        prim_type="Xform",
        position=np.array([0.3, 0.3, 0.3]),
    )
    
    # Coll position at (0.3, -0.3, 0.3) - for collision testing
    coll_prim = create_prim(
        prim_path="/World/coll",
        prim_type="Xform", 
        position=np.array([0.3, -0.3, 0.3]),
    )
    
    print("Hardcoded scene created successfully")
    return {
        "pf400": pf400_prim,
        "microplate": microplate_prim,
        "platform1": platform1_prim,
        "platform2": platform2_prim,
        "collision_cube": collision_cube_prim,
        "high": high_prim,
        "side": side_prim,
        "coll": coll_prim,
    }

def create_pf400_robot(world):
    """Create PF400 robot and its ZMQ server"""
    
    # Create robot articulation
    robot = world.scene.add(Robot(
        prim_path="/World/pf400",
        name="pf400_robot",
    ))
    
    # Create ZMQ server with integrated control
    zmq_server = ZMQ_PF400_Server(simulation_app, robot, "pf400_robot", 5557, "smooth")
    
    return robot, zmq_server

class CollisionDetector:
    """Handles collision detection and notifies robot servers"""
    
    def __init__(self, robot_servers):
        self.robot_servers = robot_servers  # Dict of {robot_name: server}
        
    def on_collision(self, contact_headers, contact_data):
        """Handle collision events and notify affected robot servers"""
        
        for contact_header in contact_headers:
            if contact_header.type != ContactEventType.CONTACT_FOUND:
                continue
                
            actor0 = str(PhysicsSchemaTools.intToSdfPath(contact_header.actor0))
            actor1 = str(PhysicsSchemaTools.intToSdfPath(contact_header.actor1))
            
            print(f"Collision detected: {actor0} <-> {actor1}")
            
            # Check which robot servers are affected by this collision
            for robot_name, server in self.robot_servers.items():
                robot_prim_path = f"/World/{robot_name.replace('_robot', '')}"
                
                if actor0.startswith(robot_prim_path) or actor1.startswith(robot_prim_path):
                    print(f"Notifying {robot_name} server of collision")
                    if hasattr(server, 'on_collision'):
                        server.on_collision(actor0, actor1)

def main():
    # Create world
    world = World(stage_units_in_meters=1.0)
    
    # Create hardcoded scene
    scene_objects = create_hardcoded_scene(world)
    
    # Create PF400 robot and server
    pf400_robot, pf400_server = create_pf400_robot(world)
    
    # Enable collision detection on robot
    pf400_prim = get_prim_at_path("/World/pf400")
    PhysxSchema.PhysxContactReportAPI.Apply(pf400_prim)
    
    # Setup collision detector
    robot_servers = {"pf400_robot": pf400_server}
    collision_detector = CollisionDetector(robot_servers)
    
    # Subscribe to collision events
    collision_subscription = get_physx_simulation_interface().subscribe_contact_report_events(
        collision_detector.on_collision
    )
    print(f"Collision subscription: {collision_subscription}")
    
    # Reset world to initialize physics
    world.reset()
    
    # Start ZMQ server
    pf400_server.start_server()
    print("PF400 ZMQ server started on port 5557")
    
    # Run simulation loop
    try:
        print("Starting simulation loop...")
        while simulation_app.is_running():
            # Call robot server update methods each frame
            if hasattr(pf400_server, 'update'):
                pf400_server.update()
            
            # Step the simulation
            world.step(render=True)
            
    except KeyboardInterrupt:
        print("Simulation interrupted by user")
    
    print("Shutting down...")
    simulation_app.close()

if __name__ == "__main__":
    main()