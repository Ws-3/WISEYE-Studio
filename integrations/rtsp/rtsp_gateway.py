"""Publish WISEYE UE render targets as RTSP CH1 (visible) and CH2 (infrared)."""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path

from core.config import ROOT, AppConfig


class UEFrameClient:
    """One persistent UE connection per stream avoids reconnecting every frame."""

    def __init__(self, host: str, port: int, channel: str, quality: int, device_id=None, timeout=8):
        self.timeout = timeout
        self.device_id=device_id
        self.host = host
        self.port = port
        self.channel = channel
        self.quality = quality
        self.peer: socket.socket | None = None
        self.received = bytearray()
        self.last_payload: dict = {}

    def close(self) -> None:
        peer, self.peer = self.peer, None
        if peer:
            try:
                peer.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            peer.close()
        self.received.clear()

    def frame(self) -> bytes:
        peer = self.peer
        if peer is None:
            peer = socket.create_connection((self.host, self.port), timeout=min(5, self.timeout))
            peer.settimeout(self.timeout)
            self.peer = peer
        request_id = f"rtsp-{self.channel}-{uuid.uuid4().hex[:10]}"
        message = {
            "version": 1,
            "request_id": request_id,
            "command": "camera.stream_frame",
            "payload": {"channel": self.channel, "quality": self.quality},
        }
        if self.device_id:message["payload"]["device_id"]=self.device_id
        peer.sendall(json.dumps(message).encode("utf-8") + b"\n")
        while b"\n" not in self.received:
            chunk = peer.recv(262144)
            if not chunk:
                raise ConnectionError("UE closed the image connection")
            self.received.extend(chunk)
            if len(self.received) > 16 * 1024 * 1024:
                raise ValueError("UE image response exceeded 16 MiB")
        line, remainder = self.received.split(b"\n", 1)
        self.received = bytearray(remainder)
        response = json.loads(line)
        if response.get("request_id") != request_id:
            raise ValueError("UE returned an unexpected frame response")
        if response.get("status") != "ok":
            raise RuntimeError(response.get("error", {}).get("message", "UE rejected the frame request"))
        payload = response["payload"]
        if payload.get("channel") != self.channel or payload.get("encoding") != "jpeg":
            raise ValueError("UE returned an unexpected image channel or encoding")
        if self.device_id and payload.get("device_id")!=self.device_id:raise ValueError("UE returned a different device frame")
        self.last_payload = payload
        return base64.b64decode(payload["image_base64"], validate=True)


def request_frame(host: str, port: int, channel: str, quality: int) -> bytes:
    client = UEFrameClient(host, port, channel, quality)
    try:
        return client.frame()
    finally:
        client.close()


def ffmpeg_command(ffmpeg: str, fps: int, url: str) -> list[str]:
    return [
        ffmpeg, "-hide_banner", "-loglevel", "warning", "-nostdin",
        "-probesize", "32", "-analyzeduration", "0", "-fpsprobesize", "0",
        "-fflags", "nobuffer", "-flags", "low_delay", "-threads", "1",
        "-filter_threads", "1", "-use_wallclock_as_timestamps", "1",
        "-f", "image2pipe", "-framerate", str(fps), "-vcodec", "mjpeg", "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-threads", "2", "-preset", "ultrafast", "-tune", "zerolatency",
        # Every frame is independently decodable. New desktop viewers can show
        # the next low-rate simulation frame instead of waiting for a long GOP.
        "-pix_fmt", "yuv420p", "-g", "1", "-keyint_min", "1", "-sc_threshold", "0", "-bf", "0",
        # UE capture is variable-rate; do not manufacture duplicate/backfill
        # frames when the source is slower than the publication rate ceiling.
        "-fps_mode", "passthrough",
        "-flush_packets", "1", "-muxdelay", "0",
        "-f", "rtsp", "-rtsp_transport", "tcp", url,
    ]


def publish_channel(args, channel: str, path: str, fps: int, device_id=None, stop=None) -> None:
    url = f"rtsp://{args.rtsp_host}:{args.rtsp_port}/{path}"
    period = 1.0 / fps
    process: subprocess.Popen | None = None
    source = UEFrameClient(args.ue_host, args.ue_port, channel, args.quality,device_id)
    failures = 0
    previous = None
    while stop is None or not stop.is_set():
        started = time.monotonic()
        try:
            if process is None or process.poll() is not None:
                if process:
                    process.wait(timeout=1)
                process = subprocess.Popen(
                    ffmpeg_command(args.ffmpeg, fps, url),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                previous = None
            frame = source.frame()
            identity = (source.last_payload.get('frame_number'), source.last_payload.get('simulation_time_s'))
            if identity != previous:
                assert process.stdin is not None
                process.stdin.write(frame)
                process.stdin.flush()
                previous = identity
            failures = 0
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            source.close()
            failures += 1
            if failures == 1 or failures % 20 == 0:
                print(f"{channel}: waiting for stream source ({exc})", flush=True)
            if process and process.poll() is not None:
                process = None
            time.sleep(min(2.0, 0.2 * failures))
        remaining = period - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)

    source.close()
    if process and process.poll() is None:process.terminate()

def discover_gimbals(args):
    with socket.create_connection((args.ue_host,args.ue_port),timeout=3) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id='gateway-discovery',command='sim.get_state',payload={}))+chr(10)).encode())
        data=json.loads(peer.makefile('rb').readline(65536))
    if data.get('status')!='ok':raise ValueError('UE discovery failed')
    return {d['id'] for d in data['payload'].get('devices',[]) if d['kind']=='gimbal'}


def main() -> None:
    from dataclasses import asdict
    settings = AppConfig.load()
    config = asdict(settings)
    parser = argparse.ArgumentParser()
    parser.add_argument("--ue-host", default=config["host"])
    parser.add_argument("--ue-port", type=int, default=config["port"])
    parser.add_argument("--rtsp-host", default=settings.rtsp_host)
    parser.add_argument("--rtsp-port", type=int, default=config["rtsp_port"])
    parser.add_argument("--visible-fps", type=int, default=config["rtsp_visible_fps"])
    parser.add_argument("--infrared-fps", type=int, default=config["rtsp_infrared_fps"])
    parser.add_argument("--quality", type=int, default=config["rtsp_jpeg_quality"])
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    args = parser.parse_args()
    if not args.ffmpeg or not Path(args.ffmpeg).is_file():
        raise SystemExit("FFmpeg was not found. Add ffmpeg.exe to PATH.")
    channels = (("CH1", settings.stream_path('ptz-01', 'visible'), args.visible_fps),
                ("CH2", settings.stream_path('ptz-01', 'infrared'), args.infrared_fps),
                ("OBS", settings.stream_path('scene', 'observer'), 15))
    workers = [threading.Thread(target=publish_channel, args=(args, *item), daemon=False) for item in channels]
    for worker in workers:
        worker.start()
    print("WISEYE RTSP gateway: CH1 visible, CH2 infrared, OBS observer", flush=True)
    extra={}
    while True:
        try:
            ids=discover_gimbals(args)-{'ptz-01'}
            for ident in ids-extra.keys():
                stop=threading.Event();threads=[]
                for channel,sensor,fps in [('CH1','visible',args.visible_fps),('CH2','infrared',args.infrared_fps)]:
                    thread=threading.Thread(target=publish_channel,args=(args,channel,settings.stream_path(ident,sensor),fps,ident,stop),daemon=True);thread.start();threads.append(thread)
                extra[ident]=(stop,threads)
            for ident in list(extra):
                if ident not in ids:extra.pop(ident)[0].set()
        except (OSError,ValueError):pass
        time.sleep(2)


if __name__ == "__main__":
    main()
