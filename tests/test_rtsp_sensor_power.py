import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
from integrations.rtsp.rtsp_gateway import UEFrameClient,SensorDisabled,publish_channel


class RtspSensorPowerTests(unittest.TestCase):
    def test_sensor_disabled_has_a_distinct_error(self):
        peer=MagicMock();sent=[]
        peer.sendall.side_effect=lambda data:sent.append(json.loads(data))
        peer.recv.side_effect=lambda _: (json.dumps(dict(request_id=sent[-1]['request_id'],status='error',error=dict(code='sensor_disabled',message='disabled')))+'\n').encode()
        with patch('socket.create_connection',return_value=peer):
            client=UEFrameClient('localhost',1,'CH2',60)
            with self.assertRaises(SensorDisabled):client.frame()
            client.close()

    def test_encoder_is_absent_when_disabled_and_released_on_stop(self):
        stop=threading.Event();source=MagicMock();process=MagicMock();process.poll.return_value=None
        source.last_payload=dict(frame_number=1,simulation_time_s=1)
        calls=[]
        def frame():
            calls.append(1)
            if len(calls)==1:raise SensorDisabled()
            if len(calls)==2:return b'jpeg'
            stop.set();raise SensorDisabled()
        source.frame.side_effect=frame
        args=SimpleNamespace(rtsp_host='localhost',rtsp_port=8554,ue_host='localhost',ue_port=1,quality=60,ffmpeg='ffmpeg')
        with patch('integrations.rtsp.rtsp_gateway.UEFrameClient',return_value=source),patch('integrations.rtsp.rtsp_gateway.subprocess.Popen',return_value=process) as spawn,patch('integrations.rtsp.rtsp_gateway.time.sleep'):
            publish_channel(args,'CH2','ir',10,stop=stop)
        spawn.assert_called_once();process.stdin.write.assert_called_once_with(b'jpeg')
        process.terminate.assert_called_once();process.wait.assert_called_once();source.close.assert_called_once()


if __name__=='__main__':unittest.main()
