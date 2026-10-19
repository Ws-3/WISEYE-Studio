"""Isolated Blocks acceptance test; does not connect to WISEYE or real aircraft."""
import argparse
import asyncio
import json
import math
from pathlib import Path

from projectairsim import Drone, ProjectAirSimClient, World
from projectairsim.types import LandedState


async def run(args, report):
    client = ProjectAirSimClient()
    drone = None
    armed = False
    try:
        client.connect()
        client.socket_services.recv_timeout = 60000
        world = World(client, "scene_basic_drone.jsonc", delay_after_load_sec=3,
                      sim_config_path=str(args.airsim_root / "client/python/example_user_scripts/sim_config"))
        drone = Drone(client, world, "Drone1")
        frames = report["frames"] = {"rgb": 0, "depth": 0}
        for kind, topic in (("rgb", "scene_camera"), ("depth", "depth_camera")):
            def receive(_, message, kind=kind):
                if message:
                    frames[kind] += 1
            client.subscribe(drone.sensors["DownCamera"][topic], receive)

        async def command(name, pending, expected=True):
            task = await pending
            result = await asyncio.wait_for(task, timeout=60)
            report["steps"].append({"name": name, "result": result,
                                    "expected": expected,
                                    "pose": drone.get_ground_truth_pose()})
            if result is not expected and not args.diagnostic_continue:
                raise RuntimeError(f"{name} returned {result}, expected {expected}")
            print(name, "returned", result, flush=True)

        if drone.enable_api_control() is False:
            raise RuntimeError("API control rejected")
        if drone.arm() is False:
            raise RuntimeError("Arming rejected")
        armed = True
        report["before_takeoff"] = drone.get_ground_truth_kinematics()
        await command("takeoff", drone.takeoff_async(timeout_sec=50))
        assert drone.get_landed_state() == LandedState.FLYING
        await command("hover", drone.hover_async())
        p0 = drone.get_ground_truth_pose()["translation"]
        await asyncio.sleep(3)
        p1 = drone.get_ground_truth_pose()["translation"]
        report["hover_drift_m"] = math.dist([p0[k] for k in "xyz"], [p1[k] for k in "xyz"])
        assert report["hover_drift_m"] < 1.0, "Hover drift exceeds 1 metre"
        assert drone.get_landed_state() == LandedState.FLYING, "Stationary hover misclassified as landed"
        target = (p1["x"] + 3, p1["y"], p1["z"])
        await command("waypoint", drone.move_to_position_async(*target, velocity=1, timeout_sec=30))
        p2 = drone.get_ground_truth_pose()["translation"]
        report["waypoint_error_m"] = math.dist(target, [p2[k] for k in "xyz"])
        assert report["waypoint_error_m"] < 1.0, "Waypoint error exceeds 1 metre"
        if args.regression:
            # A short path smaller than lookahead must still move the aircraft.
            p = drone.get_ground_truth_pose()["translation"]
            short_start = tuple(p[k] for k in "xyz")
            short = (p["x"] + 0.75, p["y"], p["z"])
            await command("short_waypoint", drone.move_to_position_async(*short, velocity=0.5, timeout_sec=15, lookahead=1))
            p = drone.get_ground_truth_pose()["translation"]
            report["short_error_m"] = math.dist(short, [p[k] for k in "xyz"])
            # SimpleFlight's documented controller accuracy is 0.5 m; require
            # motion toward the target without inventing a tighter guarantee.
            report["short_moved_m"] = math.dist(short_start, [p[k] for k in "xyz"])
            assert report["short_error_m"] <= 0.5, "Short path exceeded controller accuracy"
            assert report["short_moved_m"] >= 0.2, "Short path incorrectly completed without moving"
            await command("already_at_goal", drone.move_to_position_async(*[p[k] for k in "xyz"], velocity=1, timeout_sec=5))
            await command("timeout", drone.move_to_position_async(p["x"] + 100, p["y"], p["z"], velocity=1, timeout_sec=0.2), expected=False)
            await command("recover_after_timeout", drone.hover_async())
            p = drone.get_ground_truth_pose()["translation"]
            pending = await drone.move_to_position_async(p["x"] + 100, p["y"], p["z"], velocity=1, timeout_sec=30)
            await asyncio.sleep(0.5)
            await command("cancel_with_hover", drone.hover_async())
            cancelled_result = await asyncio.wait_for(pending, 10)
            report["cancelled_command_result"] = cancelled_result
            assert cancelled_result is False, "Replaced flight command should not report success"
            assert drone.get_landed_state() == LandedState.FLYING
        await command("land", drone.land_async())
        for _ in range(25):
            report["landed_state"] = drone.get_landed_state()
            if report["landed_state"] == LandedState.LANDED:
                break
            await asyncio.sleep(0.2)
        assert report["landed_state"] == LandedState.LANDED, "Landed state not confirmed within 5 seconds"
        drone.disarm()
        armed = False
        drone.disable_api_control()
        assert all(frames.values()), "RGB or depth messages missing"
        report["passed"] = all(step["result"] is step["expected"] for step in report["steps"])
        if not report["passed"]:
            raise RuntimeError("Physical checks completed but a flight command returned False")
    finally:
        if armed and drone is not None:
            try:
                task = await drone.land_async()
                await asyncio.wait_for(task, 30)
                drone.disarm()
                drone.disable_api_control()
            except Exception as error:
                report["cleanup_error"] = str(error)
        client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--airsim-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--regression", action="store_true", help="Also test short paths, no-op, timeout, and command replacement")
    parser.add_argument("--diagnostic-continue", action="store_true",
                        help="Record rejected command results and inspect subsequent state; never counts as passing")
    args = parser.parse_args()
    report = {"passed": False, "steps": [], "scope": "isolated Blocks; message receipt only, not image quality"}
    try:
        asyncio.run(run(args, report))
    except Exception as error:
        report["error"] = repr(error)
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
