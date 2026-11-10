"""Bounded JSON-lines client shared by the GUI and command-line receiver."""
import base64
import json
import math
import socket
import time
import uuid

MAX_RESPONSE = 16 * 1024 * 1024


class RPCError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(f'{code}: {message}')
        self.code = code


class Client:
    def __init__(self, host='127.0.0.1', port=50100, device='ptz-01', sensor='infrared'):
        self.host, self.port, self.device, self.sensor = host, port, device, sensor
        self.connect_timeout, self.response_timeout = 3, 10
        self.sample_poll_interval=.01

    def rpc(self, command, **payload):
        token = uuid.uuid4().hex
        request = dict(version=1, request_id=token, command=command,
                       payload=dict(({'device_id':self.device} if self.device else {}), **payload))
        with socket.create_connection((self.host, self.port), timeout=self.connect_timeout) as sock:
            sock.settimeout(self.response_timeout)
            sock.sendall((json.dumps(request) + '\n').encode('utf8'))
            raw = sock.makefile('rb').readline(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE or not raw.endswith(b'\n'):
            raise ValueError('Incomplete or oversized response')
        response = json.loads(raw)
        if response.get('request_id') != token:
            raise ValueError('Response ID mismatch')
        if response.get('status') != 'ok':
            error = response.get('error', {})
            raise RPCError(error.get('code', 'unknown'), error.get('message', 'Request failed'))
        return response['payload']

    def configure(self, keep_partial_occlusion=True, keep_partial_outside=True,
                  min_visible_pixels=1, min_visible_fraction=0,max_fps=None):
        options={} if max_fps is None else dict(max_fps=max_fps)
        return self.rpc('camera.gt_configure', keep_partial_occlusion=keep_partial_occlusion,
                        keep_partial_outside=keep_partial_outside,
                        min_visible_pixels=min_visible_pixels, min_visible_fraction=min_visible_fraction,**options)

    def sample(self, stop=None):
        accepted = self.request_sample('camera.sample_request',stop,sensor=self.sensor)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if stop is not None and stop.wait(self.sample_poll_interval):
                raise InterruptedError('Stopped')
            elif stop is None:
                time.sleep(self.sample_poll_interval)
            try:
                packet = self.rpc('camera.sample_frame', sensor=self.sensor,
                                  sample_token=accepted['sample_token'])
            except RPCError as error:
                if error.code == 'frame_unavailable':
                    continue
                raise
            if packet['run_id'] != accepted['run_id']:
                raise ValueError('Simulator session changed')
            validate_packet(packet, self.device, self.sensor)
            return packet
        raise TimeoutError('GT sample timed out; image or depth capture unavailable')

    def sample_pair(self, stop=None):
        started=time.monotonic()
        accepted = self.request_sample('camera.sample_pair_request',stop)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if stop is not None and stop.wait(self.sample_poll_interval):
                raise InterruptedError('Stopped')
            if stop is None:
                time.sleep(self.sample_poll_interval)
            try:
                pair = self.rpc('camera.sample_pair_frame', sample_token=accepted['sample_token'])
            except RPCError as error:
                if error.code == 'frame_unavailable':
                    continue
                raise
            validate_pair(pair, self.device)
            if pair['pair_id'] != accepted['sample_token'] or pair['run_id'] != accepted['run_id']:
                raise ValueError('Paired sample identity mismatch')
            pair['request_round_trip_ms']=(time.monotonic()-started)*1000
            return pair
        raise TimeoutError('Paired sample timed out')

    def request_sample(self,command,stop=None,**payload):
        deadline=time.monotonic()+1.5
        while True:
            try:return self.rpc(command,**payload)
            except RPCError as error:
                if error.code!='rate_limited' or time.monotonic()>=deadline:raise
                if stop is not None:
                    if stop.wait(.01):raise InterruptedError('Stopped')
                else:time.sleep(.01)


def validate_packet(packet, device=None, sensor=None):
    if device and packet.get('device_id') != device:
        raise ValueError('Wrong device')
    if sensor and packet.get('sensor_id') != sensor:
        raise ValueError('Wrong sensor')
    if packet.get('annotation_status') != 'complete':
        raise ValueError(packet.get('annotation_error', 'GT unavailable'))
    if not packet.get('frame_id') or not packet.get('run_id'):
        raise ValueError('Missing frame identity')
    width, height = packet['width'], packet['height']
    if type(width) is not int or type(height) is not int or not (0 < width <= 4096 and 0 < height <= 4096):
        raise ValueError('Invalid image dimensions')
    objects, ignored = packet['objects'], packet['ignored_objects']
    if not isinstance(objects, list) or not isinstance(ignored, list):
        raise ValueError('Invalid object lists')
    for obj in objects + ignored:
        box = obj['bbox_xyxy']
        if len(box) != 4 or not all(type(v) in (int, float) and math.isfinite(v) for v in box):
            raise ValueError('Invalid box')
        x1, y1, x2, y2 = box
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height) or type(obj['class_id']) is not int or obj['class_id'] not in (0,1,2):
            raise ValueError('Box or class out of range')
    eligible = not ignored
    if packet.get('training_eligible') is not eligible or packet.get('negative_sample') is not (eligible and not objects):
        raise ValueError('Inconsistent training/negative flags')
    if packet.get('encoding') != 'jpeg':
        raise ValueError('Unsupported image encoding')
    image = base64.b64decode(packet['image_base64'], validate=True)
    if not image.startswith(b'\xff\xd8') or not image.endswith(b'\xff\xd9'):
        raise ValueError('Invalid JPEG')
    return image


def save_sample(packet, output):
    from .storage import save_sample as write_sample
    return write_sample(packet,output)


def validate_pair(pair, device=None):
    samples = pair['samples']
    if set(samples) != {'visible', 'infrared'} or not pair.get('pair_id'):
        raise ValueError('Incomplete visible/infrared pair')
    if samples['visible']['device_id'] != samples['infrared']['device_id']:
        raise ValueError('Mixed device pair')
    value=pair['simulation_time_s']
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError('Invalid simulation time')
    for sensor, packet in samples.items():
        validate_packet(packet, device, sensor)
        if packet['run_id'] != pair['run_id'] or packet['sample_token'] != pair['pair_id']:
            raise ValueError('Mixed sessions or pair tokens')
        if packet['simulation_time_s'] != pair['simulation_time_s']:
            raise ValueError('Images were not captured at the same simulation time')
    return samples


def save_pair(pair, output):
    from .storage import save_pair as write_pair
    return write_pair(pair,output)
