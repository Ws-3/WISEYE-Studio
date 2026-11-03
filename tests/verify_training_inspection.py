import argparse
import math
from pathlib import Path
import unittest
from tests.verify_training_fusion import fixture
from training_client.preview import QApplication, Window
from training_client.fusion import blend_pair, fusion_transform, comparison
from training_client.view import Canvas
from PySide6.QtCore import QPointF


class InspectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_baseline_raw_overlay_and_rotation_direction(self):
        pair=fixture();pair['samples']['infrared']['camera_position_cm'][1]=12
        self.assertFalse(blend_pair(pair).isNull())
        pair['samples']['infrared']['camera_rotation_pitch_yaw_roll_deg'][1]=5
        mapped=fusion_transform(pair,'rotation').map(QPointF(32,18))
        self.assertAlmostEqual(mapped.x(),32-32*math.tan(math.radians(5)),places=5)
        self.assertAlmostEqual(mapped.y(),26,places=5)

    def test_measurement_reports_time_and_mapped_gt_centers(self):
        pair=fixture();pair['request_round_trip_ms']=12.5
        obj=dict(target_id='uav-01',class_id=0,bbox_xyxy=[10,10,20,20],visible_fraction_in_frame=1)
        for packet in pair['samples'].values():packet.update(objects=[obj.copy()],negative_sample=False)
        stats=comparison(pair)
        self.assertEqual(stats['capture_delta_ms'],0)
        self.assertEqual(stats['request_round_trip_ms'],12.5)
        self.assertAlmostEqual(stats['gt_center_differences'][0]['dy_px'],8)

    def test_zoom_native_fit_and_popup_remains_live(self):
        window=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-01',output=Path('unused')))
        try:
            window.show_frame(fixture());tile=window.tiles['fusion'];canvas=tile.canvas
            canvas.resize(640,520);canvas.set_zoom(2);self.assertEqual(canvas.zoom,2)
            canvas.fit();self.assertEqual(canvas.zoom,1)
            canvas.native();self.assertAlmostEqual(canvas.scale()*canvas.zoom,1)
            tile.enlarge();self.app.processEvents()
            self.assertFalse(tile.popup.canvas.image.isNull())
            window.show_error('disconnect');self.assertTrue(tile.popup.canvas.image.isNull())
            self.assertTrue(window.display_fps.isEnabled() and window.save_fps.isEnabled())
            window.fusion_mode.setCurrentIndex(1)
        finally:
            window.close();self.app.processEvents()
