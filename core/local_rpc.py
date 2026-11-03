"""Bounded local session control RPC (stdlib only)."""
import json
import socket
import time

def request(port, command, payload=None, *, timeout=2):
    deadline = time.monotonic() + timeout
    with socket.create_connection(('127.0.0.1', port), timeout=min(1, timeout)) as peer:
        peer.settimeout(max(.01, deadline-time.monotonic()))
        request_id = f'launcher-{time.time_ns()}'
        peer.sendall(json.dumps({'version': 1, 'request_id': request_id,
                                'command': command, 'payload': payload or {}}).encode() + b'\n')
        data = b''
        while b'\n' not in data:
            remaining = deadline-time.monotonic()
            if remaining <= 0:raise TimeoutError('Local RPC deadline exceeded')
            peer.settimeout(remaining)
            part = peer.recv(65536)
            if not part:
                raise ConnectionError('Connection closed during startup')
            data += part
            if len(data) > 4 * 1024**2:
                raise ValueError('Startup response exceeded limit')
        reply = json.loads(data.split(b'\n', 1)[0])
        if not isinstance(reply, dict) or reply.get('request_id') != request_id or reply.get('version') != 1:
            raise ValueError('Invalid startup response identity')
        return reply
