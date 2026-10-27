"""SDK transport contract: identity, device routing, errors and safe hold sequence."""
import io
import json
import unittest
from unittest.mock import patch
from integrations.gimbal_client import GimbalClient,GimbalError

class Peer:
    def __init__(self,alter=None):self.sent=[];self.alter=alter
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def sendall(self,data):self.sent.append(json.loads(data))
    def makefile(self,*args):
        request=self.sent[-1]
        reply=dict(version=1,request_id=request['request_id'],status='ok',payload={'gimbal_id':'ptz-02'})
        if self.alter:self.alter(reply)
        return io.BytesIO((json.dumps(reply)+'\n').encode())

class GimbalContractTests(unittest.TestCase):
    def test_device_and_request_identity_on_wire(self):
        peer=Peer()
        with patch('integrations.gimbal_client.socket.create_connection',return_value=peer):
            client=GimbalClient('ptz-02');client.set_angles(20,5);client.state()
        self.assertEqual(peer.sent[0]['payload'],dict(device_id='ptz-02',yaw_deg=20,pitch_deg=5))
        self.assertNotEqual(peer.sent[0]['request_id'],peer.sent[1]['request_id'])
    def test_rejects_mismatched_response(self):
        peer=Peer(lambda r:r.update(request_id='wrong'))
        with patch('integrations.gimbal_client.socket.create_connection',return_value=peer):
            with self.assertRaises(GimbalError):GimbalClient().state()
    def test_propagates_server_rejection(self):
        peer=Peer(lambda r:r.update(status='error',error='unknown device'))
        with patch('integrations.gimbal_client.socket.create_connection',return_value=peer):
            with self.assertRaisesRegex(GimbalError,'unknown device'):GimbalClient().set_angles(0,0)
    def test_hold_stops_velocity_before_disabling_tracking(self):
        peer=Peer()
        with patch('integrations.gimbal_client.socket.create_connection',return_value=peer):GimbalClient('ptz-02').hold()
        self.assertEqual([r['command'] for r in peer.sent],['gimbal.set_input','gimbal.set_tracking'])
        self.assertEqual(peer.sent[0]['payload'],dict(device_id='ptz-02',yaw=0,pitch=0))
        self.assertFalse(peer.sent[1]['payload']['enabled'])

if __name__=='__main__':unittest.main()
