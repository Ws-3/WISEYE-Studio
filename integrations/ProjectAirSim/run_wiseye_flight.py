"""Run Project AirSim as WISEYE's flight-dynamics and flight-control authority."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import socket
import time
from contextlib import suppress
from pathlib import Path

from projectairsim import Drone, ProjectAirSimClient, World


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "integrations" / "ProjectAirSim" / "config"
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


class FlightController:
    """Serializes desktop and automatic commands for one AirSim drone."""

    def __init__(self, world: World, drone: Drone, loops: int, velocity: float):
        self.world = world
        self.drone = drone
        self.max_loops = loops
        self.velocity = velocity
        self.mode = "auto"
        self.paused = False
        self.completed_loops = 0
        self.command_generation = 0
        self.active_task: asyncio.Task | None = None
        self.route_wakeup = asyncio.Event()
        self.finished = asyncio.Event()
        self.route_task: asyncio.Task | None = None
        self.last_error = ""
        self.initial_position: tuple[float, float, float] | None = None
        self.path: list[list[float]] = []

    def initialize_route(self) -> None:
        state = self.drone.get_ground_truth_kinematics()["pose"]["position"]
        x, y, z = (float(state[key]) for key in "xyz")
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

    async def _issue(self, command, *, wake_route: bool = False) -> None:
        generation = self._cancel_active()
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
                    status = wiseeye_request("sim.get_state")
                    if status:
                        payload = status.get("payload", {})
                        print(
                            f"loop={self.completed_loops} linked={payload.get('dynamics_connected')} "
                            f"lidar={payload.get('lidar_hits')}/{payload.get('lidar_rays')}",
                            flush=True,
                        )
                else:
                    self.last_error = "Automatic route did not complete"
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if generation == self.command_generation:
                    self.last_error = str(exc)
                    await asyncio.sleep(0.5)
            finally:
                if generation == self.command_generation and not self.paused and self.mode == "auto":
                    self.route_wakeup.set()

    def state(self) -> dict:
        position = [0.0, 0.0, 0.0]
        try:
            pose = self.drone.get_ground_truth_kinematics()["pose"]["position"]
            position = [float(pose[key]) for key in "xyz"]
        except Exception as exc:
            self.last_error = str(exc)
        return {
            "application": "WISEYE AirSim Control",
            "connected": True,
            "paused": self.paused,
            "flight_mode": self.mode,
            "position_ned_m": position,
            "route_loops": self.completed_loops,
            "velocity_mps": self.velocity,
            "command_active": self.active_task is not None,
            "last_error": self.last_error,
        }

    async def execute(self, command: str, payload: dict) -> dict:
        if command in ("sim.ping", "sim.get_state"):
            return self.state()
        if command == "sim.pause":
            self.paused = True
            await self._issue(self.drone.hover_async())
        elif command == "sim.resume":
            self.paused = False
            if self.mode == "auto":
                self.route_wakeup.set()
        elif command == "sim.reset":
            if self.initial_position is None:
                raise ValueError("Flight origin is unavailable")
            self.paused = False
            self.mode = "auto"
            self.completed_loops = 0
            x, y, z = self.initial_position
            await self._issue(
                self.drone.move_to_position_async(x, y, z, velocity=max(1.0, self.velocity)),
                wake_route=True,
            )
        elif command == "flight.takeoff":
            self.paused = True
            self.mode = "manual"
            self.drone.arm()
            await self._issue(self.drone.takeoff_async())
        elif command == "flight.hover":
            self.paused = True
            self.mode = "manual"
            await self._issue(self.drone.hover_async())
        elif command == "flight.land":
            self.paused = True
            self.mode = "manual"
            await self._issue(self.drone.land_async())
        elif command == "flight.set_mode":
            mode = payload.get("mode")
            if mode not in ("auto", "manual"):
                raise ValueError("mode must be auto or manual")
            self.mode = mode
            if mode == "manual":
                await self._issue(self.drone.hover_async())
            elif not self.paused:
                self.route_wakeup.set()
        elif command == "flight.set_input":
            if self.mode != "manual":
                raise ValueError("Manual input requires manual flight mode")
            if self.paused:
                raise ValueError("Resume simulation before manual flight")
            names = ("forward", "right", "up", "yaw")
            values = []
            for name in names:
                value = payload.get(name, 0.0)
                if type(value) not in (int, float) or not math.isfinite(value) or not -1 <= value <= 1:
                    raise ValueError(f"{name} must be a finite number in [-1,1]")
                values.append(float(value))
            forward, right, up, yaw = values
            await self._issue(
                self.drone.move_by_velocity_body_frame_async(
                    forward * self.velocity,
                    right * self.velocity,
                    -up * self.velocity,
                    duration=0.35,
                    yaw_is_rate=True,
                    yaw=yaw * math.radians(70.0),
                )
            )
        else:
            raise KeyError("Command is not supported")
        return self.state()

    async def close(self) -> None:
        self.finished.set()
        self._cancel_active()
        if self.route_task:
            self.route_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.route_task


def response(request_id: str, payload: dict, error: tuple[str, str] | None = None) -> dict:
    result = {"version": 1, "request_id": request_id, "status": "error" if error else "ok", "payload": payload}
    if error:
        result["error"] = {"code": error[0], "message": error[1]}
    return result


async def handle_control(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, controller: FlightController
) -> None:
    try:
        while True:
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
    finally:
        writer.close()
        with suppress(Exception):
            await writer.wait_closed()


async def fly(scene: str, loops: int, velocity: float, connection_timeout: float) -> None:
    client = ProjectAirSimClient()
    drone: Drone | None = None
    controller: FlightController | None = None
    server: asyncio.Server | None = None
    try:
        print("Waiting for WISEYE Play mode and Project AirSim server...", flush=True)
        await connect_with_retry(client, connection_timeout)
        # UE can accept the service socket a moment before a full scene reload is
        # ready. Allow the real reload/actor creation operation to complete.
        client.socket_services.recv_timeout = 60000
        config_name = f"scene_wiseye_{scene}.jsonc"
        world = World(client, config_name, delay_after_load_sec=2, sim_config_path=str(CONFIG))
        drone = Drone(client, world, "Drone1")
        drone.enable_api_control()
        drone.arm()
        takeoff = await drone.takeoff_async()
        await takeoff

        controller = FlightController(world, drone, loops, velocity)
        controller.initialize_route()
        server = await asyncio.start_server(
            lambda reader, writer: handle_control(reader, writer, controller),
            CONTROL_HOST,
            CONTROL_PORT,
            limit=MAX_MESSAGE,
        )
        controller.start()
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
            async with server:
                await server.serve_forever()
    finally:
        if server:
            server.close()
            await server.wait_closed()
        if controller:
            await controller.close()
        if drone is not None:
            with suppress(Exception):
                drone.disable_api_control()
        with suppress(Exception):
            client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", choices=("original", "test_range"), default="original")
    parser.add_argument("--loops", type=int, default=0, help="0 repeats until Ctrl+C")
    parser.add_argument("--velocity", type=float, default=3.0)
    parser.add_argument("--connection-timeout", type=float, default=180.0)
    args = parser.parse_args()
    asyncio.run(fly(args.scene, args.loops, args.velocity, args.connection_timeout))


if __name__ == "__main__":
    main()
