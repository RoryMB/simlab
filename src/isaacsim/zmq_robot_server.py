import json
import threading
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import zmq
from isaacsim.core.utils.stage import get_current_stage
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot_motion.motion_generation import (
    ArticulationKinematicsSolver,
    LulaKinematicsSolver,
)
from omni.isaac.dynamic_control import _dynamic_control
from omni.physx import get_physx_scene_query_interface
from omni.usd.commands.usd_commands import DeletePrimsCommand
from pxr import Gf, Sdf, UsdPhysics

import utils


CUSTOM_ASSETS_ROOT_PATH = str((Path(__file__).parent / "../../assets").resolve())

class ZMQ_Robot_Server(ABC):
    """Base class for ZMQ robot servers with enhanced end-effector robot functionality"""

    def __init__(self, simulation_app, robot, robot_prim_path: str, robot_name: str, port: int, motion_type: str = "smooth"):
        self.simulation_app = simulation_app
        self.robot = robot
        self.robot_name = robot_name
        self.port = port
        self.motion_type = motion_type
        self.context = None
        self.socket = None

        # Cache paths and prims
        stage = get_current_stage()
        self.robot_prim_path = robot_prim_path
        self.robot_prim = stage.GetPrimAtPath(self.robot_prim_path)

        # Enhanced robot functionality
        self.motion_gen_algo = None
        self.motion_gen_solver = None

        # Pause state
        self.is_paused = False

        # Control state
        self.current_action = None
        self.target_joints = None
        self.target_pose = None

    def start_server(self):
        """Start ZMQ server in background thread"""
        zmq_thread = threading.Thread(target=self.zmq_server_thread, daemon=True)
        zmq_thread.start()
        return zmq_thread

    def zmq_server_thread(self):
        """ZMQ server running in background thread"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")

        print(f"{self.robot_name} ZMQ server listening on port {self.port}")

        while self.simulation_app.is_running():
            try:
                if self.socket.poll(100):
                    message = self.socket.recv_string(zmq.NOBLOCK)
                    request = json.loads(message)

                    print(f"{self.robot_name} received command: {request}")
                    response = self.handle_command(request)
                    print(f"{self.robot_name} sending response: {response}")

                    self.socket.send_string(json.dumps(response))

            except zmq.Again:
                continue
            except Exception as e:
                print(f"ZMQ server error for {self.robot_name}: {e}")
                error_response = {"status": "error", "message": str(e)}
                try:
                    self.socket.send_string(json.dumps(error_response))
                except:
                    pass

        self.cleanup()

    def cleanup(self):
        """Clean up ZMQ resources"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()

    @abstractmethod
    def handle_command(self, request):
        """Handle incoming ZMQ command from MADSci - must be implemented by subclasses"""
        pass

    def create_success_response(self, message: str = "success", **kwargs):
        """Helper to create standardized success response"""
        response = {"status": "success", "message": message}
        response.update(kwargs)
        return response

    def create_error_response(self, message: str):
        """Helper to create standardized error response"""
        return {"status": "error", "message": message}

    def initialize_motion_generation(self, robot_description_path: str, urdf_path: str, end_effector_frame: str = 'end_effector'):
        """Initialize motion generation algorithms for the robot"""
        self.motion_gen_algo = LulaKinematicsSolver(
            robot_description_path=robot_description_path,
            urdf_path=urdf_path,
        )
        self.motion_gen_solver = ArticulationKinematicsSolver(
            self.robot,
            self.motion_gen_algo,
            end_effector_frame,
        )
        print(f"Motion generation initialized for {self.robot_name}")

    def set_robot_base_pose(self):
        """Update robot base pose for motion planning"""
        robot_pos, robot_rot = utils.get_prim_world_pose(self.robot_prim)
        self.motion_gen_algo.set_robot_base_pose(robot_pos, robot_rot)

    def raycast(self, src: Gf.Vec3d, direction: Gf.Vec3d, distance: float, filter_prim_path: str):
        """Perform raycast to detect objects for gripping"""
        physx_query = get_physx_scene_query_interface()

        hits = []
        def ray_func(_hit):
            if _hit.rigid_body.startswith(filter_prim_path):
                return True

            stage = get_current_stage()
            prim = stage.GetPrimAtPath(_hit.rigid_body)
            if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
                return True

            hits.append({
                'hit': True,
                'prim': prim,
                'rigid_body': _hit.rigid_body,
                'position': Gf.Vec3d(*_hit.position),
                'normal': Gf.Vec3d(*_hit.normal),
            })
            return True

        physx_query.raycast_all(src, direction, distance, ray_func)

        if hits:
            hits = sorted(hits, key=lambda x: (src - x['position']).GetLength())
            return hits[0]['prim']
        return None

    def attach_object(self, target_prim_path: str, end_effector_name: str) -> str:
        """Attach a specific object using physics joints"""
        stage = get_current_stage()
        end_effector_prim_path = f"{self.robot_prim_path}/{end_effector_name}"
        end_effector_prim = stage.GetPrimAtPath(end_effector_prim_path)
        target_prim = stage.GetPrimAtPath(target_prim_path)

        if not target_prim:
            raise RuntimeError(f"Robot {self.robot_name}: Target prim not found: {target_prim_path}")

        # Create physics joint
        joint_path = end_effector_prim.GetPath().AppendChild("grip_joint")
        joint_prim = UsdPhysics.FixedJoint.Define(stage, joint_path)

        # Set the bodies to connect
        joint_prim.CreateBody0Rel().SetTargets([end_effector_prim.GetPath()])
        joint_prim.CreateBody1Rel().SetTargets([target_prim.GetPath()])

        print(f"Robot {self.robot_name} attached object: {target_prim_path}")
        return joint_path.pathString

    def detach_object(self, joint_path_string: str) -> bool:
        """Detach object by removing the specified physics joint"""
        if not joint_path_string:
            return False

        joint_path = Sdf.Path(joint_path_string)
        DeletePrimsCommand([joint_path]).do()

        # Wake up the released object
        dc = _dynamic_control.acquire_dynamic_control_interface()
        parent_rb = joint_path.GetParentPath().pathString
        dc.wake_up_rigid_body(dc.get_rigid_body(parent_rb))

        print(f"Robot {self.robot_name} detached object")
        return True

    def execute_move_joints(self):
        """Execute joint movement in simulation"""
        if self.target_joints is None:
            return

        if self.motion_type == "teleport":
            self.robot.set_joint_positions(self.target_joints)
            self.current_action = None
        else:
            action = ArticulationAction(joint_positions=self.target_joints)
            self.robot.apply_action(action)

            current_joints = self.robot.get_joint_positions()
            diff = np.abs(current_joints - self.target_joints)
            max_diff = np.max(diff)

            velocities = self.robot.get_joint_velocities()
            max_vel = np.max(np.abs(velocities))

            if max_diff < 0.01 and max_vel < 0.008:
                self.current_action = None
                print(f"Robot {self.robot_name} completed motion")

    def execute_goto_pose(self):
        """Execute pose-based movement using motion planning"""
        if self.target_pose is None:
            self.current_action = None
            raise RuntimeError(f"Robot {self.robot_name}: Cannot execute goto_pose - missing target pose")

        if self.motion_gen_solver is None:
            self.current_action = None
            raise RuntimeError(f"Robot {self.robot_name}: Cannot execute goto_pose - motion generation solver not initialized")

        target_position, target_orientation = self.target_pose
        self.set_robot_base_pose()

        tolerances = (0.001, 0.01)
        action, success = self.motion_gen_solver.compute_inverse_kinematics(
            target_position, target_orientation, *tolerances
        )

        if not success:
            self.current_action = None
            raise RuntimeError(f"Robot {self.robot_name}: IK solve failed for target pose {target_position}, {target_orientation}")

        self.robot.apply_action(action)

        if self.close_to_target(action):
            self.current_action = None
            print(f"Robot {self.robot_name} reached target pose with joint angles: {action.joint_positions.tolist() if action.joint_positions is not None else 'None'}")

    def close_to_target(self, action: ArticulationAction) -> bool:
        """Check if robot is close to target position"""
        if action.joint_positions is None:
            return True

        action_joints = action.joint_positions
        robo_joints = np.array(self.robot.get_joint_positions())[action.joint_indices]

        diff = np.sum(np.abs(action_joints - robo_joints))
        vel = np.sum(np.abs(self.robot.get_joint_velocities()))

        return diff < 0.003 and vel < 0.008


    def halt_motion(self):
        """Immediately halt robot motion"""
        current_joints = self.robot.get_joint_positions()
        action = ArticulationAction(joint_positions=current_joints)
        self.robot.apply_action(action)

        self.current_action = None
        print(f"Robot {self.robot_name} motion halted")

    def on_collision(self, actor0, actor1):
        """Called when collision is detected involving this robot"""
        self.collision_detected = True
        self.collision_actors = f"{actor0} <-> {actor1}"
        print(f"Robot {self.robot_name} collision detected: {self.collision_actors}   Use 'clear_collision' to resume operation.")

        self.halt_motion()
        self.current_action = None
        self.is_moving = False

    def update(self):
        """Called every simulation frame to execute robot actions - must be implemented by subclasses"""
        pass
