"""Qt preview regressions; run in the desktop venv, separate from AirSim tests."""
import threading
import time
import unittest
from unittest.mock import patch

import apps.desktop_app.main  # Windows system ICU must precede Qt.
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from apps.desktop_app.ue_preview_client import UEPreviewClient


def jpeg(color, size=(32, 16)):
    image = QImage(*size, QImage.Format.Format_RGB888)
    image.fill(QColor(color))
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, 'JPEG')
    return bytes(buffer.data())


class FakeSource:
    def __init__(self, encoded, advance=False):
        self.encoded, self.advance = encoded, advance
        self.last_payload = dict(frame_number=1, simulation_time_s=1, width=32, height=16)
        self.closed = threading.Event()
        self.calls = 0

    def frame(self):
        self.calls += 1
        if self.advance:
            self.last_payload['frame_number'] += 1
        return self.encoded

    def close(self):
        self.closed.set()


class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.client = UEPreviewClient(size=(32, 16))
        self.frames, self.states = [], []
        self.client.frame_received.connect(lambda image, fps: self.frames.append(image.pixelColor(0, 0).name()))
        self.client.state_changed.connect(lambda ok, text: self.states.append(ok))

    def tearDown(self):
        self.client.stop()
        self.pump(.08)

    def pump(self, seconds):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            self.app.processEvents()
            time.sleep(.003)

    def test_duplicate_source_frames_expire_instead_of_refreshing_freshness(self):
        source = FakeSource(jpeg('red'))
        with patch('apps.desktop_app.ue_preview_client.UEFrameClient', return_value=source):
            self.client.start_source('127.0.0.1', 50051, 'CH1', 'ptz-02')
            self.pump(.15)
            first = self.client.last_frame
            self.pump(2.1)
            self.assertEqual(len(self.frames), 1)
            self.assertEqual(self.client.last_frame, first)
            self.assertFalse(self.states[-1])
            self.assertGreater(source.calls, 10)

    def test_busy_gui_has_one_latest_frame_slot(self):
        source = FakeSource(jpeg('blue'), advance=True)
        with patch('apps.desktop_app.ue_preview_client.UEFrameClient', return_value=source):
            self.client.start_source('127.0.0.1', 50051, 'CH2', 'ptz-03')
            time.sleep(.3)  # Deliberately do not service Qt.
            stats = self.client.statistics()
            self.assertEqual(stats['pending'], 1)
            self.assertGreaterEqual(stats['overwritten'], 3)
            self.client.stop()
            self.pump(.08)
            self.assertFalse(self.frames, 'Stopped generation must not paint a late frame')

    def test_device_switch_cannot_deliver_old_blocked_response(self):
        old = FakeSource(jpeg('red'))
        current = FakeSource(jpeg('blue'))
        release = threading.Event()
        def delayed():
            release.wait(1)
            return old.encoded
        old.frame = delayed
        with patch('apps.desktop_app.ue_preview_client.UEFrameClient', side_effect=[old, current]) as factory:
            self.client.start_source('127.0.0.1', 50051, 'CH1', 'ptz-01')
            time.sleep(.04)
            began = time.monotonic()
            self.client.start_source('127.0.0.1', 50051, 'CH2', 'ptz-02')
            self.assertLess(time.monotonic() - began, .1)
            release.set()
            self.pump(.2)
            self.assertTrue(self.frames)
            self.assertTrue(all(color == '#0000fe' for color in self.frames), self.frames)
            self.assertEqual(factory.call_args.args[2:5], ('CH2', 60, 'ptz-02'))

    def test_wrong_native_dimensions_are_rejected_and_valid_stream_recovers(self):
        source = FakeSource(jpeg('red', (16, 16)))
        with patch('apps.desktop_app.ue_preview_client.UEFrameClient', return_value=source):
            self.client.start_source('127.0.0.1', 50051, 'CH1', 'ptz-01')
            self.pump(.12)
            self.assertFalse(self.frames)
            source.encoded = jpeg('blue')
            self.pump(.45)
            self.assertTrue(self.frames)
            self.assertTrue(self.states[-1])


if __name__ == '__main__':
    unittest.main()
