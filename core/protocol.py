"""Versioned JSON Lines framing shared by UI and protocol checks."""
import json

MAX_MESSAGE = 65536

class ProtocolError(ValueError):
    pass

def encode_request(request_id, command, payload=None):
    return (json.dumps({'version': 1, 'request_id': request_id, 'command': command,
                        'payload': payload or {}}, ensure_ascii=False, allow_nan=False)+'\n').encode('utf8')

class JsonLines:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, chunk):
        self.buffer.extend(chunk)
        messages = []
        while b'\n' in self.buffer:
            line, _, rest = self.buffer.partition(b'\n')
            if len(line) > MAX_MESSAGE:
                raise ProtocolError('响应超过长度限制')
            self.buffer = bytearray(rest)
            try:
                value = json.loads(line.decode('utf8'))
            except (ValueError, UnicodeError) as exc:
                raise ProtocolError('UE 响应不是有效 JSON') from exc
            if (not isinstance(value, dict) or value.get('version') != 1
                or not isinstance(value.get('request_id'), str)
                or value.get('status') not in ('ok', 'error')
                or not isinstance(value.get('payload'), dict)):
                raise ProtocolError('UE 响应格式不正确')
            messages.append(value)
        if len(self.buffer) > MAX_MESSAGE:
            raise ProtocolError('响应超过长度限制')
        return messages
