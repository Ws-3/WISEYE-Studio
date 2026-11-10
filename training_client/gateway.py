"""Run on the simulation computer: limited data-only LAN gateway, stdlib only."""
import argparse
import json
import socket
import socketserver
import threading

ALLOWED = {'camera.stream_frame', 'sim.ping', 'sim.get_state', 'camera.gt_configure',
           'camera.sample_request', 'camera.sample_frame',
           'camera.sample_pair_request', 'camera.sample_pair_frame'}
MAX_REQUEST = 65536
MAX_RESPONSE = 16 * 1024 * 1024


def forward(request, host, port):
    if request.get('version') != 1 or not isinstance(request.get('request_id'), str) or not request['request_id'] or len(request['request_id']) > 128:
        raise ValueError('Invalid version or request_id')
    if request.get('command') not in ALLOWED or not isinstance(request.get('payload'), dict):
        raise ValueError('This gateway only accepts data and GT policy commands')
    if request['command'] == 'camera.stream_frame':
        payload = request['payload']
        if payload.get('channel') not in ('CH1','CH2','AERIAL','AERIAL_IR') or not isinstance(payload.get('device_id'), str) or not payload['device_id']:
            raise ValueError('Preview requires an explicit device and CH1/CH2')
        if set(payload) - {'channel','device_id','quality'}:
            raise ValueError('Unexpected preview parameters')
    with socket.create_connection((host, port), timeout=3) as upstream:
        upstream.settimeout(10)
        upstream.sendall((json.dumps(request) + '\n').encode())
        response = upstream.makefile('rb').readline(MAX_RESPONSE + 1)
    if len(response) > MAX_RESPONSE or not response.endswith(b'\n'):
        raise ValueError('Incomplete or oversized upstream response')
    return response


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 8

    def __init__(self, address, upstream):
        self.upstream = upstream
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(12)
        request = {}
        try:
            raw = self.rfile.readline(MAX_REQUEST + 1)
            if len(raw) > MAX_REQUEST or not raw.endswith(b'\n'):
                raise ValueError('Incomplete or oversized request')
            request = json.loads(raw)
            if not isinstance(request, dict):
                raise ValueError('Request must be an object')
            response = forward(request, *self.server.upstream)
        except (OSError, ValueError) as error:
            response = (json.dumps(dict(version=1, request_id=request.get('request_id') if isinstance(request, dict) else '',
                                        status='error', payload={}, error=dict(code='gateway_error', message=str(error)))) + '\n').encode()
        try:
            self.wfile.write(response)
        except OSError:
            pass


class Service:
    """Owned by the simulator process; no second user-facing launcher."""
    def __init__(self, bind='0.0.0.0', port=50100, upstream=('127.0.0.1', 50051)):
        self.server = Server((bind, port), upstream)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval':.2}, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=50100)
    parser.add_argument('--ue-host', default='127.0.0.1')
    parser.add_argument('--ue-port', type=int, default=50051)
    args = parser.parse_args()
    with Server((args.bind, args.port), (args.ue_host, args.ue_port)) as server:
        print(f'WISEYE data gateway {args.bind}:{args.port} -> {args.ue_host}:{args.ue_port}', flush=True)
        try:
            server.serve_forever(poll_interval=.2)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
