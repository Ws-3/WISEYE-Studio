import base64
import copy
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from training_client.client import save_sample, validate_packet, Client, RPCError
from training_client.gateway import Server, Service, forward
from training_client.train import prepare


def packet(objects=None, ignored=None):
    objects, ignored = objects or [], ignored or []
    return dict(frame_id='run/ptz-02/infrared/1', run_id='run', device_id='ptz-02',
                sensor_id='infrared', width=640, height=512, objects=objects,
                ignored_objects=ignored, training_eligible=not ignored,
                negative_sample=not objects and not ignored, annotation_status='complete',
                encoding='jpeg', image_base64=base64.b64encode(b'\xff\xd8test\xff\xd9').decode())


class ReceiverTests(unittest.TestCase):
    def test_true_negative_has_empty_yolo_label(self):
        with tempfile.TemporaryDirectory() as folder:
            name = save_sample(packet(), folder)
            self.assertEqual((Path(folder)/'labels'/f'{name}.txt').read_bytes(), b'')
            metadata = json.loads((Path(folder)/'annotations'/f'{name}.json').read_text())
            self.assertTrue(metadata['negative_sample'])
            self.assertNotIn('image_base64', metadata)

    def test_filtered_visible_target_is_not_false_negative(self):
        obj = dict(class_id=0, bbox_xyxy=[10, 20, 30, 40])
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(save_sample(packet(ignored=[obj]), folder))
            self.assertFalse(list(Path(folder).rglob('*.txt')))

    def test_box_normalization_and_session_identity(self):
        obj = dict(class_id=0, bbox_xyxy=[0, 0, 640, 512])
        with tempfile.TemporaryDirectory() as folder:
            sample = packet(objects=[obj]); name = save_sample(sample, folder)
            self.assertEqual((Path(folder)/'labels'/f'{name}.txt').read_text().split(), ['0','0.50000000','0.50000000','1.00000000','1.00000000'])
            sample['frame_id'] = 'another-run/ptz-02/infrared/1'
            self.assertNotEqual(name, save_sample(sample, folder))

    def test_reject_corrupt_annotations(self):
        original = packet()
        for changes in [dict(annotation_status='unavailable'), dict(negative_sample=False),
                        dict(training_eligible=False), dict(image_base64='broken'),
                        dict(objects=[dict(class_id=0, bbox_xyxy=[-1,0,3,4])])]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    validate_packet(dict(original, **changes))

    def test_gateway_blocks_control_commands(self):
        for command in ['flight.takeoff', 'sim.load_scene', 'sensor.configure']:
            with self.assertRaises(ValueError):
                forward(dict(version=1, request_id='x', command=command, payload={}), '127.0.0.1', 1)

    def test_actual_gateway_framing_and_client(self):
        def reply(request, *_):
            return (json.dumps(dict(version=1, request_id=request['request_id'], status='ok', payload={'answer':42}))+'\n').encode()
        with patch('training_client.gateway.forward', side_effect=reply):
            with Server(('127.0.0.1', 0), ('127.0.0.1', 1)) as server:
                thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval':.01}, daemon=True);thread.start()
                try:
                    client = Client(port=server.server_address[1])
                    self.assertEqual(client.rpc('sim.ping'), {'answer':42})
                    with socket.create_connection(server.server_address) as sock:
                        sock.sendall(b'[]\n')
                        self.assertEqual(json.loads(sock.makefile('rb').readline())['status'], 'error')
                finally:
                    server.shutdown();thread.join()

    def test_training_split_includes_negative_and_blocks_leakage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            train_packet = packet(); save_sample(train_packet, root/'train')
            val_packet = copy.deepcopy(train_packet)
            val_packet.update(run_id='validation', frame_id='validation/ptz-02/infrared/1',
                              image_base64=base64.b64encode(b'\xff\xd8different\xff\xd9').decode())
            save_sample(val_packet, root/'val')
            spec = prepare(root/'train', root/'val', root/'experiment')
            self.assertEqual(json.loads(spec.read_text())['names'], {'0':'drone'})
            self.assertEqual(len((root/'experiment/train.txt').read_text().splitlines()), 1)
            with self.assertRaises(ValueError):
                prepare(root/'train', root/'train', root/'invalid')
            next((root/'val/images').glob('*.jpg')).write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                prepare(root/'train', root/'val', root/'invalid')

    def test_simulator_owned_service_releases_port(self):
        service=Service(bind='127.0.0.1',port=0)
        address=service.server.server_address
        self.assertTrue(service.thread.is_alive())
        service.close()
        self.assertFalse(service.thread.is_alive())
        with socket.socket() as probe:
            probe.bind(address)

    def test_rate_limit_retry_is_cancellable_and_not_a_bad_frame(self):
        client=Client()
        with patch.object(client,'rpc',side_effect=[RPCError('rate_limited','wait'),{'sample_token':'new'}]):
            self.assertEqual(client.request_sample('camera.sample_pair_request')['sample_token'],'new')
        stop=threading.Event();stop.set()
        with patch.object(client,'rpc',side_effect=RPCError('rate_limited','wait')):
            with self.assertRaises(InterruptedError):client.request_sample('camera.sample_pair_request',stop)


if __name__ == '__main__':
    unittest.main()
