import json
import unittest
import copy
from core.protocol import JsonLines, ProtocolError, MAX_MESSAGE
from core.models import validate_state

def response(request_id='1'):
    return {'version':1,'request_id':request_id,'status':'ok','payload':{'message':'智瞳'}}

class FramingTests(unittest.TestCase):
    def test_utf8_fragmentation_and_coalesced_messages(self):
        packet=(json.dumps(response('1'),ensure_ascii=False)+'\n'+json.dumps(response('2'))+'\n').encode('utf8')
        decoder=JsonLines()
        result=[]
        for byte in packet:
            result.extend(decoder.feed(bytes([byte])))
        self.assertEqual([item['request_id'] for item in result],['1','2'])
        self.assertEqual(result[0]['payload']['message'],'智瞳')

    def test_invalid_utf8_json_and_envelope(self):
        for packet in (b'\xff\n', b'{oops}\n', b'[]\n', b'{"version":2}\n'):
            with self.subTest(packet=packet), self.assertRaises(ProtocolError):
                JsonLines().feed(packet)

    def test_unterminated_and_complete_oversized_messages(self):
        for packet in (b'x'*(MAX_MESSAGE+1), b'x'*(MAX_MESSAGE+1)+b'\n'):
            with self.assertRaises(ProtocolError): JsonLines().feed(packet)

    def test_incomplete_state_cannot_reach_ui(self):
        with self.assertRaises(ProtocolError):
            validate_state({'application':'WISEYE Studio'})

    def test_legacy_disabled_camera_is_not_a_disconnect(self):
        state=dict(application='WISEYE Studio',paused=False,tracking=False,rotors_running=False,
                   simulation_time_s=0,yaw_deg=0,pitch_deg=0,pointing_error_deg=0,fov_deg=25,
                   flight_mode='manual',sensor_mode='visible',palette='white_hot',width=0,height=0,
                   drone_position_cm=[0,0,25],sensors=dict(visible=dict(enabled=False)))
        self.assertIs(validate_state(state),state)
        for enabled in (True,0,None):
            invalid=copy.deepcopy(state);invalid['sensors']['visible']['enabled']=enabled
            with self.assertRaises(ProtocolError):validate_state(invalid)
        invalid=dict(state,width=640)
        with self.assertRaises(ProtocolError):validate_state(invalid)
        for malformed in (None,[],{'visible':None}):
            with self.assertRaises(ProtocolError):validate_state(dict(state,sensors=malformed))

if __name__=='__main__': unittest.main()
