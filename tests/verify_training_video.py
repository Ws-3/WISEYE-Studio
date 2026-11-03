"""Regressions for preview/GT isolation and bounded buffering."""
import argparse
import base64
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
import training_client.preview  # Load system ICU before standalone Qt imports.
from PySide6.QtWidgets import QApplication
from tests.verify_training_fusion import fixture
from training_client.workbench import Window
from training_client.video import VideoPreview
from training_client.preview import Receiver
from training_client.gateway import forward


class VideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_preview_overwrites_pending_without_gt_and_stops(self):
        packet=fixture()['samples']['infrared'];counter=[0]
        def rpc(*args,**kwargs):
            counter[0]+=1
            return dict(packet,channel='CH2',device_id='ptz-01',frame_number=counter[0],simulation_time_s=counter[0]/20)
        video=VideoPreview('unused',1,'ptz-01',['infrared'],30)
        with patch('training_client.video.Client.rpc',side_effect=rpc):
            video.start()
            try:
                deadline=time.monotonic()+2
                while counter[0]<5 and time.monotonic()<deadline:time.sleep(.01)
                pending=video.take()
                self.assertEqual(set(pending),{'infrared'})
                self.assertGreaterEqual(pending['infrared']['frame_number'],4)
                self.assertNotIn('objects',pending['infrared'])
                self.assertEqual(video.take(),{})
            finally:video.stop();self.assertTrue(video.wait())

    def test_unified_preview_gt_toggle_keeps_same_frame_and_fusion(self):
        window=Window(argparse.Namespace(host='unused',port=50100,device='ptz-01',output=Path('unused')))
        try:
            bundle=fixture()
            for packet in bundle['samples'].values():
                packet['objects']=[dict(target_id='uav-01',class_id=0,bbox_xyxy=[5,6,15,16],visible_fraction_in_frame=1)]
                packet['negative_sample']=False
            window.show_frame(bundle);with_gt=window.tiles['visible'].canvas.image.copy()
            self.assertFalse(hasattr(window,'view_mode'))
            self.assertTrue(all(not t.canvas.image.isNull() for t in window.tiles.values()))
            window.show_gt.setChecked(False)
            self.assertIs(window.latest,bundle)
            for sensor in ('visible','infrared'):self.assertEqual(window.tiles[sensor].canvas.image,window.decoded[sensor])
            self.assertNotEqual(with_gt,window.tiles['visible'].canvas.image)
            self.assertFalse(window.tiles['fusion'].canvas.image.isNull())
            window.show_gt.setChecked(True);self.assertIs(window.latest,bundle)
        finally:window.close()

    def test_receiver_mailbox_keeps_only_latest_decoded_pair(self):
        client=unittest.mock.Mock();count=[0]
        def sample(stop):
            count[0]+=1;bundle=fixture()
            for packet in bundle['samples'].values():packet['frame_number']=count[0]
            return bundle
        client.sample_pair.side_effect=sample
        receiver=Receiver(client,{},None,display_fps=10,recording=False);receiver.latest_only=True
        receiver.start()
        try:
            deadline=time.monotonic()+2
            while count[0]<3 and time.monotonic()<deadline:time.sleep(.01)
            time.sleep(.03);bundle=receiver.take_frame()
            self.assertGreaterEqual(bundle['samples']['visible']['frame_number'],3)
            self.assertEqual(set(bundle['_images']),{'visible','infrared'})
            self.assertIsNone(receiver.take_frame())
        finally:receiver.stop_event.set();self.assertTrue(receiver.wait(2000))

    def test_disabled_capture_gate_never_requests_depth_or_gt(self):
        client=unittest.mock.Mock()
        receiver=Receiver(client,{},None)
        receiver.capture_gate=threading.Event()
        receiver.start();time.sleep(.15);receiver.stop_event.set()
        self.assertTrue(receiver.wait(1000))
        client.configure.assert_not_called();client.sample_pair.assert_not_called()

    def test_preview_gateway_cannot_retarget_observer_or_control(self):
        for payload in ({'channel':'OBS','device_id':'ptz-01'}, {'channel':'CH1'},
                        {'channel':'CH1','device_id':'ptz-01','enabled':True}):
            with self.assertRaises(ValueError):
                forward(dict(version=1,request_id='x',command='camera.stream_frame',payload=payload),'unused',1)


if __name__=='__main__':unittest.main()
