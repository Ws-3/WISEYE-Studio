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

ROOT = Path(__file__).resolve().parents[2]


class UEFrameClient:
    """One persistent UE connection per stream avoids reconnecting every frame."""

    def __init__(self, host: str, port: int, channel: str, quality: int):
        self.host = host
        self.port = port
        self.channel = channel
        self.quality = quality
        self.peer: socket.socket | None = None
        self.received = bytearray()
        self.last_payload: dict = {}

    def close(self) -> None:
        if self.peer:
            try:
                self.peer.close()
            finally:
                self.peer = None
        self.received.clear()

    def frame(self) -> bytes:
        if self.peer is None:
            self.peer = socket.create_connection((self.host, self.port), timeout=5)
            self.peer.settimeout(8)
        request_id = f"rtsp-{self.channel}-{uuid.uuid4().hex[:10]}"
        message = {
            "version": 1,
            "request_id": request_id,
            "command": "camera.stream_frame",
            "payload": {"channel": self.channel, "quality": self.quality},
        }
        self.peer.sendall(json.dumps(message).encode("utf-8") + b"\n")
        while b"\n" not in self.received:
            chunk = self.peer.recv(262144)
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
        "-f", "image2pipe", "-framerate", str(fps), "-vcodec", "mjpeg", "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        # Every frame is independently decodable. New desktop viewers can show
        # the next low-rate simulation frame instead of waiting for a long GOP.
        "-pix_fmt", "yuv420p", "-g", "1", "-keyint_min", "1", "-sc_threshold", "0", "-bf", "0",
        "-f", "rtsp", "-rtsp_transport", "tcp", url,
    ]


def publish_channel(args, channel: str, path: str, fps: int) -> None:
    url = f"rtsp://{args.rtsp_host}:{args.rtsp_port}/{path}"
    period = 1.0 / fps
    process: subprocess.Popen | None = None
    source = UEFrameClient(args.ue_host, args.ue_port, channel, args.quality)
    failures = 0
    while True:
        started = time.monotonic()
        try:
            if process is None or process.poll() is not None:
                if process:
                    process.wait(timeout=1)
                process = subprocess.Popen(
                    ffmpeg_command(args.ffmpeg, fps, url),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            frame = source.frame()
            assert process.stdin is not None
            process.stdin.write(frame)
            process.stdin.flush()
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


def main() -> None:
    config = json.loads((ROOT / "configs" / "app.json").read_text(encoding="utf-8-sig"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--ue-host", default=config["host"])
    parser.add_argument("--ue-port", type=int, default=config["port"])
    parser.add_argument("--rtsp-host", default="127.0.0.1")
    parser.add_argument("--rtsp-port", type=int, default=config["rtsp_port"])
    parser.add_argument("--visible-fps", type=int, default=config["rtsp_visible_fps"])
    parser.add_argument("--infrared-fps", type=int, default=config["rtsp_infrared_fps"])
    parser.add_argument("--quality", type=int, default=config["rtsp_jpeg_quality"])
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    args = parser.parse_args()
    if not args.ffmpeg or not Path(args.ffmpeg).is_file():
        raise SystemExit("FFmpeg was not found. Add ffmpeg.exe to PATH.")
    channels = (("CH1", config["rtsp_visible_path"], args.visible_fps),
                ("CH2", config["rtsp_infrared_path"], args.infrared_fps))
    workers = [threading.Thread(target=publish_channel, args=(args, *item), daemon=False) for item in channels]
    for worker in workers:
        worker.start()
    print("WISEYE RTSP gateway: CH1 visible, CH2 infrared", flush=True)
    for worker in workers:
        worker.join()


if __name__ == "__main__":
    main()
