"""Bounded flight input and training configuration changes during reception."""
import argparse
import json
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import Mock,patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QAbstractSocket
from apps.desktop_app.airsim_client import AirSimClient
from core.config import AppConfig
from training_client.workbench import Window
from training_client.preview import Receiver
from tests.verify_training_fusion import fixture


class OnlineInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def client(self):
        c=AirSimClient(AppConfig());c.socket=Mock()
        c.socket.state.return_value=QAbstractSocket.SocketState.ConnectedState
        c.socket.bytesToWrite.return_value=0;c.socket.write.return_value=1
        return c

    def test_thousands_of_inputs_keep_only_newest_and_release_is_next(self):
        c=self.client()
        first=c.request('flight.set_input',dict(forward=1))
        for _ in range(1000):c.request('flight.set_input',dict(forward=-1))
        c.request('flight.set_input',dict(forward=0,right=0,up=0,yaw=0))
        self.assertEqual(c.socket.write.call_count,1);self.assertEqual(len(c.pending),1)
        self.assertEqual(len(c.latest_input),1)
        c.pending.pop(first);c._input_finished(first,True)
        sent=json.loads(c.socket.write.call_args.args[0])
        self.assertEqual(sent['payload']['forward'],0);self.assertEqual(c.socket.write.call_count,2)
        self.assertFalse(c.latest_input)

    def test_land_and_disconnect_discard_queued_movement_for_that_device(self):
        c=self.client();first=c.request('flight.set_input',dict(forward=1))
        c.request('flight.set_input',dict(forward=-1));c.request('flight.land')
        c._input_finished(first,True);self.assertEqual(c.socket.write.call_count,2)
        c.request('flight.set_input',dict(device_id='uav-02',forward=1))
        c.request('flight.set_input',dict(device_id='uav-02',forward=-1))
        c.disconnect_from();self.assertFalse(c.latest_input);self.assertFalse(c.input_requests)

    def test_receiver_discards_frame_in_flight_when_policy_or_directory_changes(self):
        entered=threading.Event();release=threading.Event();saved=threading.Event();c=Mock();calls=[0]
        receiver=Receiver(c,dict(keep_partial_occlusion=True),'old',recording=True)
        def sample(stop):
            calls[0]+=1
            if calls[0]==1:entered.set();release.wait(3)
            return fixture()
        def save(bundle,output):
            self.assertEqual(output,'new');saved.set();receiver.stop_event.set();return 'ok'
        c.sample_pair.side_effect=sample
        with patch('training_client.preview.save_pair',side_effect=save):
            receiver.start()
            try:
                self.assertTrue(entered.wait(2))
                receiver.update_settings(dict(keep_partial_occlusion=False),'new');release.set()
                self.assertTrue(saved.wait(3));self.assertTrue(receiver.wait(2000))
            finally:release.set();receiver.stop_event.set();receiver.wait(3000)
        self.assertEqual(c.configure.call_count,2)
        self.assertFalse(c.configure.call_args.kwargs['keep_partial_occlusion'])

    def test_online_widgets_update_receiver_without_disconnect(self):
        w=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-01',output=Path('old')))
        worker=Mock();worker.capture_gate=threading.Event();worker.update_settings.return_value=1
        try:
            w.worker=worker
            self.assertTrue(all(item.isEnabled() for item in (w.occlusion,w.outside,w.directory,w.visible,w.infrared,w.host,w.port,w.device)))
            w.directory.setText('new');w.occlusion.setChecked(False);w.change_settings()
            self.assertEqual(worker.update_settings.call_args.args[1],'new')
            worker.stop_event.set.assert_not_called()
            w.infrared.setChecked(False);self.assertTrue(w.source_timer.isActive())
            w.source_timer.stop();w.restart_sources();self.assertTrue(w._restart_requested)
            worker.stop_event.set.assert_called_once()
        finally:w.source_timer.stop();w.worker=None;w.close()
