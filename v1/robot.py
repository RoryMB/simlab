import logging
import math
from pathlib import Path
from pprint import pprint
import time
from typing import Tuple

import numpy as np
import omni
import omni.kit.pipapi
import omni.physx.scripts.utils as pxutils
from omni.isaac.core.articulations.articulation import Articulation
from omni.isaac.core.utils.types import ArticulationAction
from omni.isaac.dynamic_control import _dynamic_control
from omni.isaac.motion_generation import (ArticulationKinematicsSolver,
                                          ArticulationMotionPolicy,
                                          LulaKinematicsSolver, RmpFlow)
from omni.kit.scripting import BehaviorScript
from omni.physx import get_physx_scene_query_interface
from omni.usd.commands.usd_commands import DeletePrimsCommand
from pxr import (Gf, PhysxSchema, Sdf, Tf, Usd, UsdGeom, UsdLux, UsdPhysics,
                 UsdShade, UsdUtils)

try:
    import zmq
except ModuleNotFoundError:
    omni.kit.pipapi.install("zmq")
    import zmq


PATH_BASE = Path(__file__).absolute().parent
logger = logging.getLogger(__name__)

class RobotControl(BehaviorScript):
    def on_init(self):
        self.robot = None
        self.target = None
        self.attachment = None
        self.follow_target = None
        self.had_first_update = False

        self.ee_name = 'wrist_3_link'
        self.ee_prim = self.stage.GetPrimAtPath(str(self.prim_path) + '/' + self.ee_name)
        self.ee_offset = 0.166

        self.approach_offset = 0.2

        # self.motion_gen_algo = RmpFlow(
        #     urdf_path=str(PATH_BASE / 'robot_data/ur5e.urdf'),
        #     rmpflow_config_path=str(PATH_BASE / 'robot_data/ur_rmpflow.yaml'),
        #     robot_description_path=str(PATH_BASE / 'robot_data/ur_descriptor.yaml'),
        #     end_effector_frame_name=self.ee_name,
        #     maximum_substep_size=.0034,
        # )
        self.motion_gen_algo = LulaKinematicsSolver(
            robot_description_path=str(PATH_BASE / 'robot_data/ur_descriptor.yaml'),
            urdf_path=str(PATH_BASE / 'robot_data/ur5e.urdf'),
        )

        port = str(self.prim_path).split('_')[-1]
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f'tcp://*:{port}')
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        logger.warn(f'Finished initializing')

    def on_destroy(self):
        self.context.destroy()
        if self.attachment:
            DeletePrimsCommand([self.attachment[0]]).do()

    def on_play(self):
        self.had_first_update = False

    def on_pause(self):
        pass

    def on_stop(self):
        self.had_first_update = False
        if self.attachment:
            DeletePrimsCommand([self.attachment[0]]).do()

    def on_first_update(self, current_time: float, delta_time: float):
        self.had_first_update = True

        self.robot = Articulation(str(self.prim_path))
        self.robot.initialize()

        # self.motion_gen_solver = ArticulationMotionPolicy(self.robot, self.motion_gen_algo, default_physics_dt=1/120)
        self.motion_gen_solver = ArticulationKinematicsSolver(self.robot, self.motion_gen_algo, self.ee_name)

    def on_update(self, current_time: float, delta_time: float):
        # Do any initialization that couldn't be done in on_play()
        if not self.had_first_update:
            self.on_first_update(current_time, delta_time)

        # Check if we received a message
        poll_results = dict(self.poller.poll(timeout=0))
        if self.socket in poll_results:
            command, *args = self.socket.recv_string().split(maxsplit=1)
            args = args[0] if args else ''

            if command == 'follow':
                self.follow_target = self.stage.GetPrimAtPath(args)
                self.socket.send_string('follow')

            elif command == 'moveto':
                self.follow_target = None

                target = list(map(float, args.split()))
                self.target = (
                    np.array(target[:3]),
                    np.array(target[3:]),
                )

                # target = self.stage.GetPrimAtPath(args)

                # rot = get_world_rotation(target)
                # direction = rot.TransformDir(Gf.Vec3d(0, 0, 1))
                # w = rot.GetQuat().GetReal()
                # im = rot.GetQuat().GetImaginary()
                # rot = np.array((w, im[0], im[1], im[2]))

                # pos = get_world_translation(target)
                # pos -= self.ee_offset * direction
                # pos = np.array(pos)

                # self.target = (
                #     pos,
                #     rot,
                # )

            elif command == 'grab' and not self.attachment:
                self.target = None
                self.follow_target = None

                if str(self.prim_path) == '/World/ur5e_suction_5563':
                    hit_path = '/World/Plate'
                    hit_prim = self.stage.GetPrimAtPath(hit_path)
                    joint_prim = pxutils.createJoint(self.stage, 'Fixed', self.ee_prim, hit_prim)
                    self.attachment = (joint_prim.GetPath().pathString, hit_path)
                else:
                    pos = get_world_translation(self.ee_prim)
                    rot = get_world_rotation(self.ee_prim)
                    direction = rot.TransformDir(Gf.Vec3d(0, 0, 1))
                    origin = pos + (self.ee_offset * direction)

                    hit = get_physx_scene_query_interface().raycast_closest(origin, direction, 0.3)

                    if hit['hit']:
                        hit_prim = self.stage.GetPrimAtPath(hit['rigidBody'])
                        joint_prim = pxutils.createJoint(self.stage, 'Fixed', self.ee_prim, hit_prim)
                        self.attachment = (joint_prim.GetPath().pathString, hit['rigidBody'])

                        logger.warn(f'Raycast hit {hit["rigidBody"]}')
                    else:
                        logger.warn(f'Raycast did not hit')

                self.socket.send_string(command)

            elif command == 'release':
                self.target = None
                self.follow_target = None

                if self.attachment:
                    DeletePrimsCommand([self.attachment[0]]).do()
                    dc = _dynamic_control.acquire_dynamic_control_interface()
                    dc.wake_up_rigid_body(dc.get_rigid_body(self.attachment[1]))

                    # if self.attachment[1] != '/World/Plate':
                    #     time.sleep(0.2)
                    #     plate_prim = self.stage.GetPrimAtPath('/World/Plate')
                    #     hit_prim = self.stage.GetPrimAtPath(self.attachment[1])
                    #     joint_prim = pxutils.createJoint(self.stage, 'Fixed', plate_prim, hit_prim)

                    self.attachment = None

                self.socket.send_string(command)

            elif command == 'stop':
                self.target = None
                self.follow_target = None

                self.socket.send_string(command)

            elif command == 'print':
                # logger.warn(f'{self.prim_path} - at - {self.robot.get_joint_positions()}')
                if self.follow_target:
                    pos = get_world_translation(self.follow_target)
                    rot = get_world_rotation(self.follow_target)
                else:
                    pos = None
                    rot = None

                s = f'print - {self.prim_path} - {pos} {rot}'
                logger.warn(s)
                self.socket.send_string(s)

            else:
                self.target = None
                self.follow_target = None

                self.socket.send_string(f'Bad command - {command}')

        target = self.target

        if not target and self.follow_target:
            rot = get_world_rotation(self.follow_target)
            direction = rot.TransformDir(Gf.Vec3d(0, 0, 1))
            w = rot.GetQuat().GetReal()
            im = rot.GetQuat().GetImaginary()
            rot = np.array((w, im[0], im[1], im[2]))

            pos = get_world_translation(self.follow_target)
            pos -= self.ee_offset * direction
            pos = np.array(pos)

            target = (pos, rot)

        if target:
            robot_pose = self.robot.get_world_pose()
            self.motion_gen_algo.set_robot_base_pose(robot_pose[0], robot_pose[1])

            # self.motion_gen_algo.set_end_effector_target(
            #     target_position=target[0],
            #     target_orientation=target[1],
            # )
            # action = self.motion_gen_solver.get_next_articulation_action()
            # self.robot.apply_action(action)

            action, success = self.motion_gen_solver.compute_inverse_kinematics(
                target_position=target[0],
                target_orientation=target[1],
            )
            if success:
                self.robot.apply_action(action)
            else:
                logger.warn(f'{self.prim_path} - IK failed')

        if self.target:
            pos = get_world_translation(self.ee_prim)
            pos = np.array(pos)

            rot = get_world_rotation(self.ee_prim)
            w = rot.GetQuat().GetReal()
            im = rot.GetQuat().GetImaginary()
            rot = np.array((w, im[0], im[1], im[2]))

            ee_pos = (pos, rot)

            diff  = np.sum(np.abs((ee_pos[0] - self.target[0])))
            diff += np.sum(np.abs((ee_pos[1] - self.target[1])))

            if diff < 0.015:
                self.socket.send_string('target reached')
                self.target = None

def get_world_pose(prim: Usd.Prim) -> Tuple[np.ndarray, np.ndarray]:
    pos = get_world_translation(prim)
    pos = np.array(pos)

    rot = get_world_rotation(prim)
    w = rot.GetQuat().GetReal()
    im = rot.GetQuat().GetImaginary()
    rot = np.array((w, im[0], im[1], im[2]))

    return pos, rot

def get_world_translation(prim: Usd.Prim) -> Gf.Vec3d:
    world_transform: Gf.Matrix4d = omni.usd.get_world_transform_matrix(prim)
    translation: Gf.Vec3d = world_transform.ExtractTranslation()
    return translation

def get_world_rotation(prim: Usd.Prim) -> Gf.Rotation:
    world_transform: Gf.Matrix4d = omni.usd.get_world_transform_matrix(prim)
    rotation: Gf.Rotation = world_transform.ExtractRotation()
    return rotation

def get_world_scale(prim: Usd.Prim) -> Gf.Vec3d:
    world_transform: Gf.Matrix4d = omni.usd.get_world_transform_matrix(prim)
    scale: Gf.Vec3d = Gf.Vec3d(*(v.GetLength() for v in world_transform.ExtractRotationMatrix()))
    return scale
