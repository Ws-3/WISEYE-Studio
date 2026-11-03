"""Run Project AirSim as WISEYE's flight-dynamics and flight-control authority."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import socket
import sys
import time
from contextlib import suppress
from pathlib import Path

from projectairsim import Drone, ProjectAirSimClient, World


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from core.routes import validate_route

from core.runtime_paths import RESOURCE_ROOT
CONFIG = RESOURCE_ROOT / "integrations" / "ProjectAirSim" / "config"
CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 50052
MAX_MESSAGE = 65536


def wiseeye_request(command: str, payload: dict | None = None) -> dict | None:
    request = {
        "version": 1,
        "request_id": f"airsim-{time.time_ns()}",
        "command": command,
        "payload": payload or {},
    }
    try:
        with socket.create_connection(("127.0.0.1", 50051), timeout=1.0) as connection:
            connection.sendall(json.dumps(request).encode("utf-8") + b"\n")
            data = b""
            while b"\n" not in data:
                chunk = connection.recv(65536)
                if not chunk:
                    return None
                data += chunk
            return json.loads(data.split(b"\n", 1)[0])
    except (OSError, ValueError):
        return None


def ue_listener_open() -> bool:
    try:
        with socket.create_connection(('127.0.0.1',50051),timeout=.2):
            return True
    except TimeoutError:
        # A loaded editor can fill its accept backlog while streaming a city.
        # A timeout is inconclusive; only a refused/closed listener ends PIE.
        return True
    except OSError:
        return False


async def connect_with_retry(client: ProjectAirSimClient, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            client.connect()
            return
        except Exception:
            if time.monotonic() >= deadline:
                raise TimeoutError("Project AirSim server did not start. Open WISEYE and click Play.")
            await asyncio.sleep(1.0)


def resolved_ue_state_ready(reply):
    """Never create physics robots using placeholder poses after a slow UE reply."""
    if not isinstance(reply,dict) or reply.get('status')!='ok':return False
    state=reply.get('payload',{})
    if not isinstance(state,dict):return False
    if not state.get('run_id') or state.get('scene_id') not in ('original','test_range','city','city_large'):return False
    if state['scene_id']=='city_large' and (state.get('world_streaming_ready') is not True or state.get('world_streaming_enabled') is not True):return False
    def pose(value):
        return isinstance(value,list) and len(value)==3 and all(type(n) in (int,float) and math.isfinite(n) for n in value)
    if not pose(state.get('initial_drone_position_cm')):return False
    devices=state.get('devices',[])
    if not isinstance(devices,list):return False
    drones=[d for d in devices if isinstance(d,dict) and d.get('kind')=='drone']
    return bool(drones) and all(d.get('id') and d.get('dynamics_name') and pose(d.get('initial_position_cm')) for d in drones)


async def wait_for_ue_snapshot(timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        reply=await asyncio.to_thread(wiseeye_request,'sim.get_state')
        if resolved_ue_state_ready(reply):return reply
        await asyncio.sleep(.2)
    raise TimeoutError('UE has not confirmed the scene, run and initial device poses; physics was not created')


async def restore_observer(mode, timeout):
    """Wait for an acknowledged view target after slow scene creation."""
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        reply=await asyncio.to_thread(wiseeye_request,'observer.set_mode',{'mode':mode})
        if reply and reply.get('status')=='ok':return True
        await asyncio.sleep(.5)
    print('Observer restoration is pending; select a view in the desktop once UE finishes loading',flush=True)
    return False


class ConfiguredWorld(World):
    """Apply UE's resolved initial pose before AirSim creates its physics robot."""
    def __init__(self, *args, initial_position_cm=None, initial_devices=None, **kwargs):
        self.initial_devices=initial_devices
        self.initial_position_cm = initial_position_cm
        super().__init__(*args, **kwargs)

    def load_scene(self, config, delay_after_load_sec=0):
        origin = self.initial_position_cm
        if origin is not None:
            if len(origin) != 3 or not all(type(n) in (int,float) and math.isfinite(n) for n in origin):
                raise ValueError('UE initial position is invalid')
            x,y,z = origin
            config['actors'][0]['origin']['xyz'] = f'{x/100:.9f} {y/100:.9f} {-z/100:.9f}'
        if self.initial_devices:
            template=config['actors'][0]
            robots=[]
            for device in self.initial_devices:
                if device['kind']!='drone':continue
                actor=json.loads(json.dumps(template));actor['name']=device['dynamics_name']
                x,y,z=device['initial_position_cm'];actor['origin']['xyz']=f'{x/100} {y/100} {-z/100}'
                actor['origin']['rpy-deg']=f"0 0 {device.get('initial_yaw_deg',0)}"
                robots.append(actor)
            config['actors']=robots
        return super().load_scene(config, delay_after_load_sec=delay_after_load_sec)


class SessionChanged(RuntimeError):
    pass


class FlightController:
    """Serializes desktop and automatic commands for one AirSim drone."""

    def __init__(self, world: World, drone: Drone, loops: int, velocity: float, *, ready_on_ground: bool = False, device_id: str = "uav-01"):
        self.device_id=device_id
        self.fleet_controllers={}
        self.world = world
        self.drone = drone
        self.max_loops = loops
        self.velocity = velocity
        self.ready_on_ground = ready_on_ground
        self.mode = "manual" if ready_on_ground else "auto"
        self.paused = ready_on_ground
        self.completed_loops = 0
        self.command_generation = 0
        self.active_task: asyncio.Task | None = None
        self.route_wakeup = asyncio.Event()
        self.finished = asyncio.Event()
        self.route_task: asyncio.Task | None = None
        self.last_error = ""
        self.initial_position: tuple[float, float, float] | None = None
        self.path: list[list[float]] = []
        self.play_session_id = None
        self.manual_command_count = 0
        self.last_manual_input = [0.0, 0.0, 0.0, 0.0]
        self.control_writers = set()
        self.closed = False
        self.scene_id = "city"
        self.uploaded_route = None
        self.active_route = None
        self.route_status = "idle"
        self.route_next_index = 0
        self.rotor_sample = (0.0, None, (0.0,)*4)
        self.placing = False
        self.pose_sample = None

    def on_pose(self, topic, message):
        """Cache authoritative physics telemetry; the topic thread never calls RPC."""
        try:
            stamp=message['time_stamp']
            xyz=tuple(message['position'][k] for k in 'xyz')
            q=tuple(message['orientation'][k] for k in ('w','x','y','z'))
            if type(stamp) is not int or stamp<0 or any(type(v) not in (int,float) or not math.isfinite(v) for v in (*xyz,*q)):return
            if max(map(abs,xyz))>100000:return
            previous=self.pose_sample
            if previous and previous[1] is not None and stamp<=previous[1]:return
            norm=math.sqrt(sum(v*v for v in q))
            if not .5<norm<1.5:return
            w,x,y,z=(v/norm for v in q)
            yaw=math.degrees(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z)))
            self.pose_sample=(time.monotonic(),stamp,tuple(map(float,xyz)),yaw)
        except (KeyError,TypeError,ValueError):return

    def on_rotors(self, topic, message):
        """Topic thread only replaces one immutable sample; never invokes RPC."""
        try:
            values={r['rotor_id']:abs(float(r['speed']))*60/(2*math.pi) for r in message['rotor_info_vec']}
            rpms=tuple(values[k] for k in ('Prop_FL_actuator','Prop_FR_actuator','Prop_RL_actuator','Prop_RR_actuator'))
            stamp=message['time_stamp']
            if any(not math.isfinite(v) or v>30000 for v in rpms) or stamp==self.rotor_sample[1]:return
            self.rotor_sample=(time.monotonic(),stamp,rpms)
        except (KeyError,TypeError,ValueError):
            return

    def ue_request(self,command,payload=None):
        return wiseeye_request(command,dict(payload or {},device_id=self.device_id))

    def initialize_route(self) -> None:
        kinematics=self.drone.get_ground_truth_kinematics()["pose"]
        state = kinematics["position"]
        x, y, z = (float(state[key]) for key in "xyz")
        q=kinematics.get('orientation',dict(w=1,x=0,y=0,z=0))
        yaw=math.degrees(math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)))
        self.pose_sample=(time.monotonic(),None,(x,y,z),yaw)
        self.initial_position = (x, y, z)
        self.path = [
            [x + 6.0, y, z - 1.0],
            [x, y + 4.0, z],
            [x - 6.0, y, z + 1.0],
            [x, y - 4.0, z],
            [x + 6.0, y, z - 1.0],
            [x, y, z],
        ]

    def start(self) -> None:
        self.route_task = asyncio.create_task(self._route_loop())
        self.route_wakeup.set()

    def _cancel_active(self) -> int:
        self.command_generation += 1
        with suppress(Exception):
            self.drone.cancel_last_task()
        return self.command_generation

    async def _issue(self, command, *, wake_route: bool = False, replace: bool = False) -> None:
        if replace:
            # AirSim velocity APIs already use SingleTaskCall to replace the
            # previous goal. Avoid a synchronous CancelLastTask RPC per tick.
            self.command_generation+=1;generation=self.command_generation
        else:generation = self._cancel_active()
        task = await command
        self.active_task = task

        async def watch() -> None:
            try:
                result = await task
                if result is False and generation == self.command_generation:
                    self.last_error = "AirSim rejected the flight command"
            except Exception as exc:
                if generation == self.command_generation:
                    self.last_error = str(exc)
            finally:
                if generation == self.command_generation:
                    self.active_task = None
                    if wake_route:
                        self.route_wakeup.set()

        asyncio.create_task(watch())

    async def _brake_and_hold(self) -> asyncio.Task:
        # Hover uses MoveToZ upstream and may finish within position tolerance
        # while a previous velocity goal is still active. Explicitly brake first.
        generation = self.command_generation
        brake = await self.drone.move_by_velocity_body_frame_async(0,0,0,duration=.6,yaw_is_rate=True,yaw=0)
        async def finish():
            await brake
            if generation != self.command_generation:
                return False
            hold = await self.drone.hover_async()
            return await hold
        return asyncio.create_task(finish())

    async def _route_loop(self) -> None:
        while not self.finished.is_set():
            await self.route_wakeup.wait()
            self.route_wakeup.clear()
            if self.paused or self.mode != "auto":
                continue
            if self.max_loops > 0 and self.completed_loops >= self.max_loops:
                await self._issue(self.drone.hover_async())
                self.finished.set()
                continue

            generation = self._cancel_active()
            try:
                if self.active_route:
                    result=True
                    # Keep the next unfinished waypoint across pause/cancel.
                    # Point-to-point motion deliberately slows at each corner.
                    for index in range(self.route_next_index,len(self.path)):
                        task=await self.drone.move_to_position_async(*self.path[index],velocity=self.velocity)
                        self.active_task=task
                        result=await task
                        if generation!=self.command_generation or result is False:break
                        self.route_next_index=index+1
                else:
                    task = await self.drone.move_on_path_async(
                        path=self.path, velocity=self.velocity, timeout_sec=120.0
                    )
                    self.active_task = task
                    result = await task
                if generation != self.command_generation:
                    continue
                self.active_task = None
                if result is not False:
                    self.completed_loops += 1
                    self.route_next_index=0
                    if self.active_route and not self.active_route['repeat']:
                        self.mode, self.paused, self.route_status = 'manual', True, 'completed'
                        await self._issue(self._brake_and_hold())
                        await asyncio.to_thread(self.ue_request,'flight.sync_state',dict(mode=self.mode,paused=self.paused))
                        continue
                    status = self.ue_request("sim.get_state")
                    if status:
                        payload = status.get("payload", {})
                        print(
                            f"loop={self.completed_loops} linked={payload.get('dynamics_connected')} "
                            f"lidar={payload.get('lidar_hits')}/{payload.get('lidar_rays')}",
                            flush=True,
                        )
                else:
                    self.last_error = "Automatic route did not complete"
                    if self.active_route:self.mode,self.paused,self.route_status='manual',True,'failed'
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if generation == self.command_generation:
                    self.last_error = str(exc)
                    if self.active_route:self.mode,self.paused,self.route_status='manual',True,'failed'
                    await asyncio.sleep(0.5)
            finally:
                if generation == self.command_generation and not self.paused and self.mode == "auto":
                    self.route_wakeup.set()

    def state(self) -> dict:
        # A synchronous NNG GetKinematics here used to block the entire control
        # event loop for 60s after map travel, starving the session-change watcher.
        # Read one immutable topic sample instead, preserving the last position
        # with an explicit stale flag while the old scene is being replaced.
        sample=self.pose_sample
        age=time.monotonic()-sample[0] if sample else None
        fresh=age is not None and age<2
        position=list(sample[2]) if sample else [0.,0.,0.]
        yaw_deg=sample[3] if sample else 0.
        return {
            "application": "WISEYE AirSim Control",
            "run_id": self.play_session_id,
            "connected": fresh,
            "telemetry_valid": fresh,
            "telemetry_age_s": age,
            "telemetry_source": "actual_pose_topic" if sample and sample[1] is not None else "initial_kinematics_rpc",
            "drone_id": self.device_id,
            "flight_status": "ready" if self.ready_on_ground else "active",
            "paused": self.paused,
            "flight_mode": self.mode,
            "position_ned_m": position,
            "route_loops": self.completed_loops,
            "route_status": self.route_status,
            "route_next_waypoint": self.route_next_index+1 if self.active_route else None,
            "route": self.uploaded_route,
            "active_route_name": self.active_route['name'] if self.active_route else '',
            "velocity_mps": self.velocity,
            "command_active": self.active_task is not None,
            "last_error": self.last_error,
            "yaw_deg": yaw_deg,
            "motor_rpm": list(self.rotor_sample[2]),
            "rotor_sample_age_s": time.monotonic()-self.rotor_sample[0] if self.rotor_sample[0] else None,
            "manual_command_count": self.manual_command_count,
            "last_manual_input": self.last_manual_input,
        }

    async def execute(self, command: str, payload: dict) -> dict:
        if command in ("sim.ping", "sim.get_state"):
            return self.state()
        if self.placing:
            raise ValueError('正在应用设备位置，请稍候')
        if command == 'placement.apply':
            return await self.apply_placement(payload)
        if command == 'route.upload':
            self.uploaded_route = json.loads(json.dumps(validate_route(payload, self.scene_id)))
            return self.state()
        if command == 'route.start':
            if self.ready_on_ground:
                raise ValueError('请先起飞，再执行航线')
            if not self.uploaded_route:
                raise ValueError('请先上传有效航线')
            if self.mode=='manual' and self.active_task is not None:
                raise ValueError('请等待起飞或悬停动作完成，再执行航线')
            self.active_route = json.loads(json.dumps(self.uploaded_route))
            self.path = [[x,y,-z] for x,y,z in self.active_route['waypoints']]
            self.velocity = self.active_route['speed_mps']
            self.completed_loops = 0
            self.route_next_index = 0
            self.max_loops = 0
            self.mode, self.paused, self.route_status = 'auto', False, 'running'
            self._cancel_active()
            self.finished.clear()
            if self.route_task is None or self.route_task.done():
                self.start()
            else:
                self.route_wakeup.set()
            await asyncio.to_thread(self.ue_request,'flight.sync_state',dict(mode=self.mode,paused=self.paused))
            return self.state()
        if command == 'route.stop':
            self.mode, self.paused, self.route_status = 'manual', True, 'stopped'
            if not self.ready_on_ground:
                await self._issue(self._brake_and_hold())
            await asyncio.to_thread(self.ue_request,'flight.sync_state',dict(mode=self.mode,paused=self.paused))
            return self.state()
        if self.ready_on_ground:
            if command in ('sim.resume', 'sim.reset') or (command == 'flight.set_mode' and payload.get('mode') == 'auto'):
                raise ValueError('Drone is ready on the ground; take off before starting a route')
            if command in ('sim.pause', 'flight.hover', 'flight.land'):
                return self.state()
            if command == 'flight.set_mode' and payload.get('mode') == 'manual':
                return self.state()
            if command == 'flight.set_input':
                values = [payload.get(key, 0) for key in ('forward','right','up','yaw')]
                if all(type(v) in (int,float) and math.isfinite(v) and v == 0 for v in values):
                    return self.state()
                raise ValueError('Drone is ready on the ground; take off before manual movement')
        if command == "sim.pause":
            self.paused = True
            if self.active_route: self.route_status="paused"
            await self._issue(self._brake_and_hold())
        elif command == "sim.resume":
            self.paused = False
            if self.mode == "auto":
                if self.active_route: self.route_status="running"
                self.route_wakeup.set()
        elif command == "sim.reset":
            if self.initial_position is None:
                raise ValueError("Flight origin is unavailable")
            self.paused = False
            self.mode = "auto"
            self.completed_loops = 0
            self.route_next_index=0
            if self.active_route:self.route_status='running'
            x, y, z = self.initial_position
            await self._issue(
                self.drone.move_to_position_async(x, y, z, velocity=max(1.0, self.velocity)),
                wake_route=True,
            )
        elif command == "flight.takeoff":
            self.active_route=None
            self.route_next_index=0
            self.route_status='idle'
            self.paused = True
            self.mode = "manual"
            self.drone.arm()
            await self._issue(self.drone.takeoff_async())
            self.ready_on_ground = False
            generation = self.command_generation
            task = self.active_task
            async def prepare_route():
                with suppress(Exception, asyncio.CancelledError):
                    if await task is not False and generation == self.command_generation:
                        self.initialize_route()
            asyncio.create_task(prepare_route())
        elif command == "flight.hover":
            if self.active_route:self.route_status='stopped'
            self.paused = True
            self.mode = "manual"
            await self._issue(self._brake_and_hold())
        elif command == "flight.land":
            if self.active_route:self.route_status='stopped'
            self.paused = True
            self.mode = "manual"
            await self._issue(self.drone.land_async())
            generation = self.command_generation
            task = self.active_task
            async def finish_landing():
                with suppress(Exception, asyncio.CancelledError):
                    if await task is not False and generation == self.command_generation:
                        # Land completion alone leaves SimpleFlight armed at idle RPM.
                        # Disarm the physical controller; never fake a stopped visual.
                        if self.drone.disarm() is False:
                            self.last_error='Landed, but AirSim refused to disarm motors'
                            return
                        self.ready_on_ground = True
            asyncio.create_task(finish_landing())
        elif command == "flight.set_mode":
            mode = payload.get("mode")
            if mode not in ("auto", "manual"):
                raise ValueError("mode must be auto or manual")
            self.mode = mode
            self.paused = False
            if mode == "manual":
                if self.active_route:self.route_status='stopped'
                await self._issue(self._brake_and_hold())
            elif not self.paused:
                if self.active_route:self.route_status='running'
                self.route_wakeup.set()
        elif command == "flight.set_input":
            if self.mode != "manual":
                raise ValueError("Manual input requires manual flight mode")
            names = ("forward", "right", "up", "yaw")
            values = []
            for name in names:
                value = payload.get(name, 0.0)
                if type(value) not in (int, float) or not math.isfinite(value) or not -1 <= value <= 1:
                    raise ValueError(f"{name} must be a finite number in [-1,1]")
                values.append(float(value))
            forward, right, up, yaw = values
            if self.paused and any(values):
                raise ValueError('Flight is paused; resume or select manual flight first')
            self.last_manual_input = values
            self.manual_command_count += 1
            if not any(values):
                await self._issue(self._brake_and_hold(),replace=True)
            else:
                await self._issue(
                    self.drone.move_by_velocity_body_frame_async(
                        forward * self.velocity,
                        right * self.velocity,
                        -up * self.velocity,
                        duration=0.35,
                        yaw_is_rate=True,
                        yaw=yaw * math.radians(70.0),
                    ),replace=True
                )
        else:
            raise KeyError("Command is not supported")
        self.last_error = ''
        if command == 'sim.reset':
            await asyncio.to_thread(self.ue_request, 'sim.reset')
        if command!='flight.set_input':
            await asyncio.to_thread(self.ue_request, 'flight.sync_state', {'mode': self.mode, 'paused': self.paused})
        return self.state()

    async def apply_placement(self, payload):
        """Move the disarmed physics body, then confirm the matching UE anchor."""
        xyz=payload.get('position_cm');yaw=payload.get('yaw_deg')
        if (payload.get('scene_id')!=self.scene_id or payload.get('run_id')!=self.play_session_id or
            not isinstance(payload.get('request_token'),str) or not 1<=len(payload['request_token'])<=64 or
            not isinstance(xyz,list) or len(xyz)!=3 or
            any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in xyz) or
            type(yaw) not in (int,float) or not math.isfinite(yaw) or abs(yaw)>180):
            raise ValueError('当前场景/会话和有效位置、偏航角不能为空')
        if not self.ready_on_ground or self.active_task is not None or any(rpm>1 for rpm in self.rotor_sample[2]):
            raise ValueError('请先降落并等待电机停止，再调整无人机位置')
        self.placing=True;old_pose=None;moved=False
        old_origin,old_path,old_sample=self.initial_position,self.path,self.pose_sample
        try:
            check=await asyncio.to_thread(self.ue_request,'placement.validate',payload)
            if not check or check.get('status')!='ok':raise ValueError('UE 未确认当前放置会话，位置未修改')
            old_pose=await asyncio.to_thread(self.drone.get_ground_truth_pose)
            radians=math.radians(yaw)
            pose=dict(frame_id=old_pose.get('frame_id','DEFAULT_FRAME'),translation=dict(zip('xyz',(xyz[0]/100,xyz[1]/100,-xyz[2]/100))),
                      rotation=dict(w=math.cos(radians/2),x=0,y=0,z=math.sin(radians/2)))
            moved=True  # An RPC timeout can occur after the server applied it.
            if await asyncio.to_thread(self.drone.set_pose,pose,True) is not True:
                raise ValueError('飞控拒绝更新无人机位置')
            self.initialize_route()
            reply=None
            for _ in range(15):
                reply=await asyncio.to_thread(self.ue_request,'placement.apply',payload)
                if reply and reply.get('status')=='ok':break
                if not reply or 'flight controller first' not in reply.get('error',{}).get('message',''):break
                await asyncio.sleep(.05)
            if not reply or reply.get('status')!='ok':
                raise ValueError('UE 未能同步新位置：'+str((reply or {}).get('error',{}).get('message','连接中断')))
            self.active_route=None;self.route_status='idle';self.route_next_index=0
            self.last_manual_input=[0.,0.,0.,0.];self.last_error=''
            state=self.state();state['placement_applied']=dict(request_token=payload['request_token'],device_id=self.device_id)
            return state
        except Exception as error:
            self.initial_position,self.path=old_origin,old_path
            self.pose_sample=old_sample
            if moved and old_pose is not None:
                try:
                    if await asyncio.to_thread(self.drone.set_pose,old_pose,True) is not True:raise RuntimeError('rollback rejected')
                except Exception as rollback:
                    raise ValueError(f'{error}；恢复原位置失败：{rollback}') from error
            raise
        finally:self.placing=False

    async def publish_rotors(self) -> None:
        """Run independently of local-key polling and interactive / --loops mode."""
        while not self.closed:
            for ctl in self.fleet_controllers.values():
                sampled,_,rpms=ctl.rotor_sample
                fresh=sampled>0 and time.monotonic()-sampled<1
                await asyncio.to_thread(ctl.ue_request,'rotors.sync_state',dict(rpm=list(rpms) if fresh else [0]*4,fresh=fresh))
            await asyncio.sleep(.1)

    async def watch_ue_controls(self) -> None:
        """One flight authority, including UE keyboard intents and PIE restarts."""
        misses = 0
        while True:
            reply = await asyncio.to_thread(self.ue_request, 'flight.get_local_control')
            if not reply or reply.get('status') != 'ok':
                # Shader compilation/readback can stall a live editor. Rebuild
                # the AirSim world only when its UE control listener is gone.
                if await asyncio.to_thread(ue_listener_open):
                    await asyncio.sleep(.5)
                    continue
                misses += 1
                if misses >= 3:
                    raise SessionChanged('UE Play session ended; reconnecting AirSim')
                await asyncio.sleep(.5)
                continue
            data = reply['payload']
            session = data['play_session_id']
            if self.play_session_id is not None and session != self.play_session_id:
                raise SessionChanged('UE Play session changed; reloading AirSim scene')
            self.play_session_id = session
            misses = 0
            selected=self.fleet_controllers.get(data.get('controlled_drone_id','uav-01'),self)
            for command in data['commands']:
                try:
                    if command == 'flight.toggle_mode':
                        await selected.execute('flight.set_mode', {'mode': 'manual' if selected.mode == 'auto' else 'auto'})
                    elif command == 'sim.toggle_pause':
                        await selected.execute('sim.resume' if selected.paused else 'sim.pause', {})
                    elif command == 'sim.reset':
                        await selected.execute(command, {})
                except (ValueError, KeyError) as error:
                    print(f'Local command rejected: {error}', flush=True)
            if data['input_dirty'] and selected.mode == 'manual' and not selected.paused:
                await selected.execute('flight.set_input', {key:data[key] for key in ('forward','right','up','yaw')})
            if self.last_error:
                raise RuntimeError(self.last_error)
            await asyncio.sleep(.1)

    async def close(self, *, skip_remote=False) -> None:
        self.closed = True
        for writer in list(self.control_writers):
            writer.close()
        self.finished.set()
        if skip_remote:
            self.command_generation += 1
        else:
            self._cancel_active()
        if self.route_task:
            self.route_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.route_task


class FleetController:
    def __init__(self,controllers):
        self.controllers={c.device_id:c for c in controllers}
        self.control_writers=set();self.closed=False
        for c in controllers:c.fleet_controllers=self.controllers
    def state(self,device_id='uav-01'):
        if device_id not in self.controllers:raise ValueError('Unknown drone device_id')
        state=self.controllers[device_id].state()
        state['fleet']=[c.state() for c in self.controllers.values()]
        return state
    async def execute(self,command,payload):
        ident=payload.get('device_id','uav-01')
        if ident not in self.controllers:raise ValueError('Unknown drone device_id')
        result=await self.controllers[ident].execute(command,payload)
        state=dict(result)
        state['fleet']=[result if c.device_id==ident else c.state() for c in self.controllers.values()]
        if command=='placement.apply':state['placement_applied']=result['placement_applied']
        return state
    async def close(self,*,skip_remote=False):
        self.closed=True
        for writer in list(self.control_writers):writer.close()
        for c in self.controllers.values():await c.close(skip_remote=skip_remote)


def response(request_id: str, payload: dict, error: tuple[str, str] | None = None) -> dict:
    result = {"version": 1, "request_id": request_id, "status": "error" if error else "ok", "payload": payload}
    if error:
        result["error"] = {"code": error[0], "message": error[1]}
    return result


async def handle_control(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, controller: FlightController
) -> None:
    controller.control_writers.add(writer)
    try:
        while not controller.closed:
            line = await reader.readline()
            if not line:
                break
            if len(line) > MAX_MESSAGE:
                break
            request_id = ""
            try:
                request = json.loads(line.decode("utf-8"))
                if not isinstance(request, dict):
                    raise ValueError("Expected a JSON object")
                request_id = request.get("request_id", "")
                command = request.get("command")
                payload = request.get("payload", {})
                if (
                    request.get("version") != 1
                    or not isinstance(request_id, str)
                    or not request_id
                    or not isinstance(command, str)
                    or not isinstance(payload, dict)
                ):
                    raise ValueError("version=1, request_id and command are required")
                result = response(request_id, await controller.execute(command, payload))
            except KeyError as exc:
                result = response(request_id, {}, ("unknown_command", str(exc)))
            except (ValueError, TypeError, json.JSONDecodeError, UnicodeError) as exc:
                result = response(request_id, {}, ("invalid_argument", str(exc)))
            except Exception as exc:
                result = response(request_id, {}, ("airsim_error", str(exc)))
            writer.write(json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
            await writer.drain()
    except (ConnectionError,OSError):
        pass  # A desktop timeout/reset must not produce an unhandled server callback.
    finally:
        controller.control_writers.discard(writer)
        writer.close()
        with suppress(ConnectionError, OSError):
            await writer.wait_closed()


async def close_control_server(server, controller, *, skip_remote):
    """Stop accepting, close clients, then await server shutdown (Python 3.12+)."""
    if server:
        server.close()
    if controller:
        await controller.close(skip_remote=skip_remote)
    if server:
        # wait_closed also waits for active clients. Waiting before closing the
        # persistent desktop sockets deadlocked map travel on Python 3.14.
        if hasattr(server,'close_clients'):
            server.close_clients()
        await server.wait_closed()


async def fly(scene: str, loops: int, velocity: float, connection_timeout: float) -> None:
    client = ProjectAirSimClient()
    drone: Drone | None = None
    controller: FlightController | None = None
    server: asyncio.Server | None = None
    stale_session = False
    rotor_publisher=None
    fleet=None
    controllers=[]
    drones=[]
    try:
        print("Waiting for WISEYE Play mode and Project AirSim server...", flush=True)
        await connect_with_retry(client, connection_timeout)
        ue_state = await wait_for_ue_snapshot(connection_timeout)
        print('UE confirmed initial poses: '+json.dumps({d['id']:d['initial_position_cm'] for d in ue_state['payload']['devices'] if d['kind']=='drone'}),flush=True)
        active_scene = (ue_state or {}).get('payload', {}).get('scene_id')
        if active_scene in ('original', 'test_range', 'city', 'city_large'):
            scene = active_scene
        # UE can accept the service socket a moment before a full scene reload is
        # ready. Allow the real reload/actor creation operation to complete.
        client.socket_services.recv_timeout = 60000
        config_name = f"scene_wiseye_{scene}.jsonc"
        origin = (ue_state or {}).get('payload', {}).get('initial_drone_position_cm')
        world = ConfiguredWorld(client, config_name, delay_after_load_sec=2, sim_config_path=str(CONFIG), initial_position_cm=origin,initial_devices=(ue_state or {}).get("payload",{}).get("devices"))
        devices=[d for d in (ue_state or {}).get('payload',{}).get('devices',[]) if d['kind']=='drone']
        if not devices:devices=[dict(id='uav-01',dynamics_name='Drone1')]
        for device in devices:
            robot=Drone(client,world,device['dynamics_name']);robot.enable_api_control();drones.append(robot)
            ctl=FlightController(world,robot,loops,velocity,ready_on_ground=loops==0,device_id=device['id'])
            ctl.scene_id=scene;ctl.play_session_id=(ue_state or {}).get('payload',{}).get('run_id');ctl.initialize_route();controllers.append(ctl)
            client.subscribe(robot.robot_info["rotor_info"],ctl.on_rotors)
            client.subscribe(robot.robot_info["actual_pose"],ctl.on_pose)
        controller=controllers[0];drone=drones[0];fleet=FleetController(controllers)
        rotor_publisher=asyncio.create_task(controller.publish_rotors())
        if loops>0:
            drone.arm();takeoff=await drone.takeoff_async();await takeoff
        server = await asyncio.start_server(
            lambda reader, writer: handle_control(reader, writer, fleet),
            CONTROL_HOST,
            CONTROL_PORT,
            limit=MAX_MESSAGE,
        )
        # Sim scene creation can replace the player view target with its robot camera.
        await restore_observer(ue_state['payload'].get('observer_mode','overview'),connection_timeout)
        for ctl in controllers:
            ctl.start()
            await asyncio.to_thread(ctl.ue_request,'flight.sync_state',dict(mode=ctl.mode,paused=ctl.paused))
        print(
            f"Project AirSim owns the drone pose. Desktop flight control: {CONTROL_HOST}:{CONTROL_PORT}",
            flush=True,
        )
        if loops > 0:
            await controller.finished.wait()
            capture = wiseeye_request("sensor.lidar.capture")
            if capture and capture.get("status") == "ok":
                print("Lidar point cloud:", capture["payload"].get("point_cloud_path"), flush=True)
        else:
            # Cleanup must close persistent clients before waiting for the
            # server. An async-with exit waits too early on Python 3.14.
            await controller.watch_ue_controls()
    except SessionChanged:
        stale_session = True
        raise
    finally:
        if rotor_publisher:
            rotor_publisher.cancel()
            with suppress(asyncio.CancelledError):await rotor_publisher
        await close_control_server(server,fleet or controller,skip_remote=stale_session)
        if not stale_session:
            for robot in drones:
                with suppress(Exception):robot.disable_api_control()
        if stale_session:
            # The old robot and service methods were destroyed by map travel.
            # Do not call cancellation/unsubscribe APIs against the new world.
            client.state = False
            thread = getattr(client, 'recv_topic_thread', None)
            if thread and thread.is_alive():
                thread.join(timeout=1)  # topic receives already have a 100 ms timeout
            for channel in (client.socket_topics, client.socket_services):
                with suppress(Exception):
                    if channel is not None:
                        channel.close()
        else:
            with suppress(Exception):
                client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", choices=("city", "city_large"), default="city")
    parser.add_argument("--loops", type=int, default=0, help="0 repeats until Ctrl+C")
    parser.add_argument("--velocity", type=float, default=3.0)
    parser.add_argument("--connection-timeout", type=float, default=180.0)
    args = parser.parse_args()
    async def supervise():
        while True:
            try:
                await fly(args.scene, args.loops, args.velocity, args.connection_timeout)
                return
            except Exception as error:
                if args.loops > 0:
                    raise
                print(f'Flight session restarting: {error}', flush=True)
                await asyncio.sleep(2)
    # Data publication follows the simulator lifecycle, independently of the
    # training UI. A busy data port must not prevent normal flight operation.
    from training_client.gateway import Service
    data_service = None
    try:
        try:
            data_service = Service()
            print('WISEYE training data service ready on TCP 50100', flush=True)
        except OSError as error:
            print(f'WISEYE training data service unavailable: {error}', flush=True)
        asyncio.run(supervise())
    finally:
        if data_service:
            data_service.close()


if __name__ == "__main__":
    main()
