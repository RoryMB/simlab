import logging
import pickle
import time
from pathlib import Path

import carb
import numpy as np
import omni
import omni.physx.scripts.utils as pxutils
from omni.debugdraw import get_debug_draw_interface
from omni.isaac.core.articulations.articulation import Articulation
from omni.isaac.dynamic_control import _dynamic_control
from omni.isaac.motion_generation import (ArticulationKinematicsSolver,
                                          ArticulationMotionPolicy,
                                          LulaKinematicsSolver, RmpFlow)
from omni.isaac.core.utils.types import ArticulationAction
from omni.kit.scripting import BehaviorScript
from omni.physx import get_physx_scene_query_interface
from omni.timeline import get_timeline_interface
from omni.usd.commands.usd_commands import DeletePrimsCommand
from pxr import (Gf, PhysxSchema, Sdf, Tf, Usd, UsdGeom, UsdLux, UsdPhysics,
                 UsdShade, UsdUtils)

try:
    import zmq
except ModuleNotFoundError:
    omni.kit.pipapi.install('zmq')
    import zmq
try:
    import networkx
except ModuleNotFoundError:
    omni.kit.pipapi.install('networkx')
    import networkx

import sys
sys.path.append(str(Path.home() / 'simlab'))
from utils import DSH_ADDR, LAB_ADDR, Flags, Resource


logger = logging.getLogger(__name__)
PATH_BASE = Path(__file__).absolute().parent
PATH_ROBOTS = Path.home() / 'rpl_omniverse/ov/robots/'

COLOR_K = 0xff000000
COLOR_R = 0xffff0000
COLOR_G = 0xff00ff00
COLOR_B = 0xff0000ff
COLOR_C = 0xff00ffff
COLOR_M = 0xffff00ff
COLOR_Y = 0xffffff00
COLOR_W = 0xffffffff
COLOR_GRAY = 0xff555555

_gizmo = get_debug_draw_interface()
_physx = get_physx_scene_query_interface()
_dc = _dynamic_control.acquire_dynamic_control_interface()
_timeline = get_timeline_interface()
# _timeline.is_playing()

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

def get_world_pose(prim: Usd.Prim) -> 'tuple[np.ndarray, np.ndarray]':
    pos = get_world_translation(prim)
    pos = np.array(pos)

    rot = get_world_rotation(prim)
    w = rot.GetQuat().GetReal()
    im = rot.GetQuat().GetImaginary()
    rot = np.array((w, im[0], im[1], im[2]))

    return pos, rot

class Agent:
    def __init__(self, resource: Resource=None, context: zmq.Context[zmq.Socket]=None) -> None:
        self.resource = resource

        if context is None:
            context: zmq.Context[zmq.Socket] = zmq.Context.instance()

        self.sock_sub = context.socket(zmq.SUB)
        self.sock_sub.connect(DSH_ADDR)
        self.sock_sub.setsockopt(zmq.SUBSCRIBE, Flags.ENGINE_HEARTBEAT)

        self.sock_pub = context.socket(zmq.PUB)
        self.sock_pub.connect(LAB_ADDR)
        time.sleep(1) # Allow socket to connect

        self.sock_cmd = context.socket(zmq.REP)
        self.port = self.sock_cmd.bind_to_random_port('tcp://*')

        self.resource.features['addr_external'] = f'tcp://192.168.1.90:{self.port}'

        self.poller = zmq.Poller()
        self.poller.register(self.sock_sub, zmq.POLLIN)
        self.poller.register(self.sock_cmd, zmq.POLLIN)

        self.announce()

    def poll(self) -> 'list[zmq.Socket]':
        return [l[0] for l in filter(lambda x: x[1]==zmq.POLLIN, self.poller.poll(timeout=0))]

    def announce(self):
        logger.warning(f'Agent announcing self at {self.resource.features["addr_external"]}')
        self.sock_pub.send_multipart([Flags.RESOURCE_UP, pickle.dumps(self.resource)])

    def depart(self):
        logger.warning(f'Agent announcing departure at {self.resource.features["addr_external"]}')
        self.sock_pub.send_multipart([Flags.RESOURCE_DN, pickle.dumps(self.resource)])
        self.sock_sub.close()
        self.sock_pub.close()
        self.sock_cmd.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.depart()

class InspectorVariable(property):
    # https://docs.omniverse.nvidia.com/dev-guide/latest/dev_usd/quick-start/usd-types.html
    def __init__(self, name: str, value_type: Sdf.ValueTypeName, default=None) -> None:
        def get_attr(owner):
            assert isinstance(owner, BehaviorScript),\
                'InspectorVariable should only be attached to an instance of BehaviorScript'

            attr = owner.prim.GetAttribute(name)
            if not attr:
                attr = owner.prim.CreateAttribute(name, value_type)
                if default is not None:
                    attr.Set(default)

            return attr

        def fget(owner):
            return get_attr(owner).Get()

        def fset(owner, value):
            get_attr(owner).Set(value)

        property.__init__(self, fget, fset)

class RobotControl(BehaviorScript):
    robot_name = InspectorVariable('rmb:robot_name', Sdf.ValueTypeNames.String, '')
    motion_algo_name = InspectorVariable('rmb:motion_algo_name', Sdf.ValueTypeNames.String, 'IK')
    target_name = InspectorVariable('rmb:target_name', Sdf.ValueTypeNames.String, '')
    resource_positions = InspectorVariable('rmb:resource_positions', Sdf.ValueTypeNames.String, '')

    _grab_joint = InspectorVariable('rmb:_grab_joint', Sdf.ValueTypeNames.String, None)

    def __init__(self, prim_path: Sdf.Path):
        super().__init__(prim_path)

        # Make InspectorVariables populate in the Raw USD Properties for editing
        for k, v in self.__class__.__dict__.items():
            if isinstance(v, InspectorVariable):
                v.__get__(self)

    def on_init(self):
        self._agent = None
        self.clear()
        logger.warning(f'{self.prim_path} - on_init complete')

    def on_destroy(self):
        self.clear()

    def on_stop(self):
        # if self.initialized and self.motion_algo_name == 'RMPFlow':
        #     self.motion_gen_algo.stop_visualizing_end_effector()

        self.clear()

    def clear(self):
        if self._agent: self._agent.depart()
        self.detach(warn=False)

        self.initialized = False
        self._state = None
        self._agent = None
        self.motion_gen_algo = None
        self.motion_gen_solver = None
        self.robot = None
        self.ray_prim = None

    def setup(self):
        logger.warning(f'{self.prim_path} - Setting up')

        for prim in Usd.PrimRange(self.prim):
            if prim.GetName() == 'grab_ray_src':
                self.ray_prim = prim
                break
        else:
            self.ray_prim = self.stage.GetPrimAtPath(str(self.prim_path) + '/pointer')

        if not self.robot_name:
            logger.error(f'{self.prim_path} - robot_name not valid: {self.robot_name}')
            return

        self.robot = Articulation(str(self.prim_path))
        try:
            self.robot.initialize()
        except AttributeError:
            logger.error(f'{self.prim_path} - Articulation failed initialization')
            return

        if self.motion_algo_name == 'RMPFlow':
            self.motion_gen_algo = RmpFlow(
                robot_description_path=str(PATH_ROBOTS / self.robot_name / f'{self.robot_name}_descriptor.yaml'),
                rmpflow_config_path=str(PATH_ROBOTS / self.robot_name / f'{self.robot_name}_rmpflow.yaml'),
                urdf_path=str(PATH_ROBOTS / self.robot_name / f'{self.robot_name}.urdf'),
                end_effector_frame_name='pointer',
                maximum_substep_size=.0034,
            )
            self.motion_gen_solver = ArticulationMotionPolicy(self.robot, self.motion_gen_algo, default_physics_dt=1/120)
            # self.motion_gen_algo.visualize_end_effector_position()
        elif self.motion_algo_name == 'IK':
            self.motion_gen_algo = LulaKinematicsSolver(
                robot_description_path=str(PATH_ROBOTS / self.robot_name / f'{self.robot_name}_descriptor.yaml'),
                urdf_path=str(PATH_ROBOTS / self.robot_name / f'{self.robot_name}.urdf'),
            )
            self.motion_gen_solver = ArticulationKinematicsSolver(self.robot, self.motion_gen_algo, 'pointer')
        elif self.motion_algo_name == 'None':
            self.motion_gen_algo = None
            self.motion_gen_solver = None
        else:
            logger.error(f'{self.prim_path} - bad motion algorithm {self.motion_algo_name}')
            return

        resource = Resource(
            features={
                'name': self.robot_name,
                'variant': 'agent',
                'model': self.robot_name,
                'group': '0',
            },
        )
        if self.resource_positions:
            for name in self.resource_positions.split(' '):
                pos_prim = self.stage.GetPrimAtPath(str(self.prim_path) + '/' + name)
                pos_pose = get_world_pose(pos_prim)
                resource.features[name] = ' '.join((*map(str, pos_pose[0]), *map(str, pos_pose[1])))
        self._agent = Agent(resource)
        self._state = 'idle'

        logger.warning(f'{self.prim_path} - Finished setup')
        self.initialized = True

    def on_update(self, current_time: float, delta_time: float):
        if not self.initialized:
            self.setup()
        if not self.initialized:
            logger.info(f'{self.prim_path} - Failed to setup')
            self.clear()
            return



        socks = self._agent.poll()

        if self._agent.sock_sub in socks:
            msg = self._agent.sock_sub.recv_multipart()
            if len(msg) == 1 and msg[0] == Flags.ENGINE_HEARTBEAT:
                self._agent.announce()
            else:
                logger.warning(f'{self.prim_path} - Agent received bad heartbeat from server?: {msg}')

        if self._agent.sock_cmd in socks:
            msg = self._agent.sock_cmd.recv_multipart()
            try:
                if len(msg) == 2 and msg[0] == Flags.AGENT_CMD:
                    command_msg = pickle.loads(msg[1])
                else:
                    assert False
            except Exception:
                self._agent.sock_cmd.send_multipart([Flags.FAILURE])
                logger.warning(f'{self.prim_path} - Agent received bad message from server: {msg}')
            else:
                logger.warning(f'{self.prim_path} - Agent received command: {command_msg}')

                if self._state != 'idle':
                    logger.warning(f'{self.prim_path} - Oops... tried to command while already busy')
                    self._agent.sock_cmd.send_multipart([Flags.FAILURE])
                    return

                action, *args = command_msg
                if action == 'home':
                    self._state = 'move_to'
                    self._target_pose = get_world_pose(self.stage.GetPrimAtPath(str(self.prim_path) + '/home'))
                elif action == 'move_to':
                    self._state = 'move_to'
                    pose = list(map(float, args[0].split(' ')))
                    self._target_pose = np.array(pose[:3]), np.array(pose[3:])
                elif action == 'move_close':
                    self._state = 'move_close'
                    pose = list(map(float, args[0].split(' ')))
                    self._target_pose = np.array(pose[:3]), np.array(pose[3:])
                elif action == 'grab':
                    if not self.grab():
                        logger.warning(f'{self.prim_path} - Problem attaching')
                        self._agent.sock_cmd.send_multipart([Flags.FAILURE])
                        return
                    self._agent.sock_cmd.send_multipart([Flags.SUCCESS, pickle.dumps(None)])
                elif action == 'release':
                    if not self.release():
                        logger.warning(f'{self.prim_path} - Problem detaching')
                        self._agent.sock_cmd.send_multipart([Flags.FAILURE])
                        return
                    self._agent.sock_cmd.send_multipart([Flags.SUCCESS, pickle.dumps(None)])
                else:
                    logger.warning(f'{self.prim_path} - Bad action in message')
                    self._agent.sock_cmd.send_multipart([Flags.FAILURE])
                    return



        if self._state in ('move_to', 'move_close'):
            action, success = self.calculate_move(self._target_pose)
            if success:
                if self._state == 'move_close':
                    if self.robot_name == 'pf400':
                        action.joint_positions[1] += 0.05
                    if self.robot_name == 'platecrane_sciclops':
                        action.joint_positions[1] = 0.0
                    # if self.robot_name == 'ot2':
                    #     action.joint_positions[1] += 0.05

                self.robot.apply_action(action)

            if self.close_to_target(action):
                self._state = 'idle'
                self._agent.sock_cmd.send_multipart([Flags.SUCCESS, pickle.dumps(None)])



        # target = self.stage.GetPrimAtPath(self.target_name)
        # if target:
        #     target_pose = get_world_pose(target)
        #     action, success = self.calculate_move(target_pose)
        #     if not self.close_to_target(action):
        #         # action.joint_positions[1] = 0
        #         self.robot.apply_action(action)
        #         logger.warn(f'{self.prim_path} - ACTION {action.joint_positions}')
        # else:
        #     logger.error(f'{self.prim_path} - No target')

        # src = get_world_translation(self.ray_prim)
        # rot = get_world_rotation(self.ray_prim)
        # drc = rot.TransformDir(Gf.Vec3d(0, 0, -1))
        # hit_prim = self.raycast(src, drc, dist=0.03, show=True, show_extra=True)

        # if hit_prim:
        #     logger.warning(f'{self.prim_path} - Raycast hit {hit_prim.GetPath()}')

        # if hit_prim and not self._grab_joint:
        #     self.attach(hit_prim)

        src = get_world_translation(self.ray_prim)
        rot = get_world_rotation(self.ray_prim)
        drc = rot.TransformDir(Gf.Vec3d(0, 0, -1))
        self.raycast(src, drc, dist=0.03, show=True, show_extra=True)

    def calculate_move(self, target_pose):
        robot_pose = get_world_pose(self.prim)
        self.motion_gen_algo.set_robot_base_pose(*robot_pose)

        if self.motion_algo_name == 'RMPFlow':
            self.motion_gen_algo.set_end_effector_target(*target_pose)
            action, success = self.motion_gen_solver.get_next_articulation_action(), True
        elif self.motion_algo_name == 'IK':
            tolerances = (0.001, 0.01)
            action, success = self.motion_gen_solver.compute_inverse_kinematics(*target_pose, *tolerances)
        else:
            action, success = None, False

        if not success:
            logger.info(f'{self.prim_path} - Motion solve failed')

        return action, success

    def close_to_target(self, action: ArticulationAction):
        diff = action.joint_positions - self.robot.get_joint_positions()
        diff = np.sum(np.abs(diff))

        vel = self.robot.get_joint_velocities()
        vel = np.sum(np.abs(vel))

        logger.warning(f'{self.prim_path} - {diff}, {vel}, {diff < 0.003 and vel < 0.0065}')

        if diff < 0.003 and vel < 0.008:
            return True
        else:
            return False

    def grab(self):
        if self._grab_joint:
            return False

        src = get_world_translation(self.ray_prim)
        rot = get_world_rotation(self.ray_prim)
        drc = rot.TransformDir(Gf.Vec3d(0, 0, -1))
        hit_prim = self.raycast(src, drc, dist=0.03)

        if hit_prim:
            logger.warning(f'{self.prim_path} - Raycast hit {hit_prim.GetPath()}')
            self.attach(hit_prim)
            return True

        return False

    def release(self):
        if not self._grab_joint:
            return False

        self.detach()
        return True

    def raycast(self, src: Gf.Vec3d, drc: Gf.Vec3d, dist: float, show=False, show_extra=False):
        dst = src + drc*dist

        hits = []
        def ray_func(_hit):
            if _hit.rigid_body.startswith(self.prim_path.pathString):
                return True

            prim = self.stage.GetPrimAtPath(_hit.rigid_body)
            if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
                return True

            hits.append({
                'hit': True,
                'prim': prim,
                'rigidBody': _hit.rigid_body,
                'position': Gf.Vec3d(*_hit.position),
                'normal': Gf.Vec3d(*_hit.normal),
            })

            return True

        _physx.raycast_all(src, drc, dist, ray_func)
        hits = sorted(hits, key=lambda x: (src-x['position'])*(src-x['position']))
        if hits:
            hit = hits[0]
        else:
            hit = {'hit': False}
        # hit = _physx.raycast_closest(src, drc, dist)

        if hit and hit['hit']:
            # hit_path = hit['rigidBody']
            # self.stage.GetPrimAtPath(hit_path)
            hit_prim = hit['prim']
            if show:
                hpos = Gf.Vec3d(*hit['position'])
                _gizmo.draw_line(src, COLOR_G, hpos, COLOR_G)
                _gizmo.draw_line(hpos, COLOR_M, dst, COLOR_M)
                if show_extra:
                    hnrm = Gf.Vec3d(*hit['normal'])
                    hoff = hpos + hnrm*0.1
                    _gizmo.draw_line(hpos, COLOR_Y, hoff, COLOR_Y)
                    _gizmo.draw_sphere(hpos, sphere_radius=0.01, color=COLOR_B)
                    # _gizmo.draw_box(hpos, (0,0,0,1), (0.02,0.02,0.02), color=COLOR_M)
            return hit_prim
        else:
            if show:
                _gizmo.draw_line(src, COLOR_R, dst, COLOR_R)
            return None

    def attach(self, prim):
        if not prim:
            logger.warning(f'{self.prim_path} - Tried to attach nothing')
            return
        logger.warning(f'{self.prim_path} - Attaching {prim.GetPath()}')

        control_prim = self.stage.GetPrimAtPath(str(self.prim_path) + '/pointer')
        joint_prim = pxutils.createJoint(self.stage, 'Fixed', control_prim, prim)
        self._grab_joint = joint_prim.GetPath().pathString

    def detach(self, warn=True):
        path_str = self._grab_joint
        if not path_str:
            if warn: logger.warning(f'{self.prim_path} - Tried to detach nothing')
            return
        logger.warning(f'{self.prim_path} - Detaching {path_str}')

        joint = Sdf.Path(path_str)
        DeletePrimsCommand([joint]).do()

        parent_rb = joint.GetParentPath().pathString
        _dc.wake_up_rigid_body(_dc.get_rigid_body(parent_rb))

        self._grab_joint = ''
