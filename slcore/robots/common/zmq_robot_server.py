from abc import ABC, abstractmethod

import numpy as np
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

from slcore.common import utils

class ZMQ_Robot_Server(ABC):
    """Base class for ZMQ robot handlers with enhanced end-effector robot functionality.

    Note: Socket management is handled by ZMQRouterServer. This class focuses on
    command handling and robot control logic.
    """

    def __init__(
        self,
        simulation_app,
        robot,
        robot_prim_path: str,
        robot_name: str,
        env_id: int,
        motion_type: str = "smooth",
    ):
        self.simulation_app = simulation_app
        self.robot = robot
        self.robot_name = robot_name
        self.env_id = env_id
        self.motion_type = motion_type

        # Cache paths and prims
        stage = get_current_stage()
        self.robot_prim_path = robot_prim_path
        self.robot_prim = stage.GetPrimAtPath(self.robot_prim_path)

        # Enhanced robot functionality
        self.motion_gen_algo = None
        self.motion_gen_solver = None

        # Pause state
        self.is_paused = False

        # Collision state
        self.collision_detected = False
        self.collision_actors = None

        # Control state
        self.current_action = None
        self.target_joints = None
        self.target_pose = None

    @abstractmethod
    def handle_command(self, request: dict) -> dict:
        """Handle incoming ZMQ command from MADSci - must be implemented by subclasses"""
        pass

    def create_success_response(self, message: str = "success", **kwargs) -> dict:
        """Helper to create standardized success response"""
        response = {"status": "success", "message": message}
        response.update(kwargs)
        return response

    def create_error_response(self, message: str) -> dict:
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
        robot_pos, robot_rot = utils.get_xform_world_pose(self.robot_prim)
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

        # Calculate the pose of the Gripper (Body0) relative to the Target (Body1)
        # We want the joint frames to match so the bodies don't move when locked.
        # By setting LocalPose0 to identity, the Joint Frame matches the Gripper Frame.
        # We then set LocalPose1 to be the Gripper's position in the Target's coordinate space.

        # Get Gripper pose relative to Target (Target -> Gripper)
        rel_pos, rel_rot = utils.get_relative_pose(end_effector_prim, target_prim)

        # Body 0 (Gripper) - Identity (No offset)
        joint_prim.CreateLocalPos0Attr().Set(Gf.Vec3f(0, 0, 0))
        joint_prim.CreateLocalRot0Attr().Set(Gf.Quatf(1, 0, 0, 0))

        # Body 1 (Target) - Offset to match Gripper
        # POSITION: Set to (0,0,0) to force the Target to snap to the Gripper's position.
        joint_prim.CreateLocalPos1Attr().Set(Gf.Vec3f(0, 0, 0))
        # This prevents the object from snapping its position to match the gripper.
        # joint_prim.CreateLocalPos1Attr().Set(Gf.Vec3f(float(rel_pos[0]), float(rel_pos[1]), float(rel_pos[2])))
        # This prevents the object from snapping its rotation to match the gripper.
        joint_prim.CreateLocalRot1Attr().Set(Gf.Quatf(float(rel_rot[0]), float(rel_rot[1]), float(rel_rot[2]), float(rel_rot[3])))

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

        # TODO: Add a tiny velocity? Objects don't always fall when dropped.

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

    def update(self):
        """Called every simulation frame to execute robot actions - must be implemented by subclasses"""
        pass
