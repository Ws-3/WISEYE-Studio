import argparse,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QMessageBox
from tests.verify_training_fusion import sample
from training_client.workbench import Window
from training_client.dataset_ui import ReviewDialog
from training_client.aerial import save_raw

class DatasetUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_source_picker_selects_aerial_without_flight_or_auto_recording(self):
        w=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-01',output=Path('unused'),sensor='both'))
        try:
            self.assertEqual(w.workspace_tabs.count(),2)
            w.sources_loaded([dict(id='ptz-01',kind='gimbal',name='PTZ'),dict(id='uav-02',kind='drone',name='Drone')])
            w.source_picker.setCurrentIndex(2)
            self.assertEqual(w.device.text(),'uav-02');self.assertEqual(w.source_kind.currentData(),'aerial');self.assertEqual(w.display_fps.maximum(),30)
            self.assertIsNone(w.worker);self.assertFalse(w.record.isChecked())
        finally:w.close();self.app.processEvents()
    def test_manual_drag_respects_zoom_coordinates_and_close_protects_draft(self):
        with tempfile.TemporaryDirectory() as folder:
            packet=sample('infrared',100,80,'#556677');packet.update(device_id='uav-01',source_sensor_id='uav-01/aerial_infrared',channel='AERIAL_IR',modality='infrared')
            save_raw(packet,folder);path=next(Path(folder).rglob('annotations/*.json'));d=ReviewDialog(path);d.show();self.app.processEvents()
            try:
                c=d.canvas;c.set_zoom(2);s=c.scale()*c.zoom
                def point(x,y):return QPoint(round((c.width()-100*s)/2+c.offset.x()+x*s),round((c.height()-80*s)/2+c.offset.y()+y*s))
                d.classes.setCurrentIndex(1);QTest.mousePress(c,Qt.MouseButton.LeftButton,pos=point(30,25));QTest.mouseRelease(c,Qt.MouseButton.LeftButton,pos=point(65,50))
                self.assertEqual(c.boxes[0][0],1)
                for actual,expected in zip(c.boxes[0][1],[30,25,65,50]):self.assertAlmostEqual(actual,expected,delta=.3)
                with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel):self.assertFalse(d.close())
                d.commit();self.assertFalse(d.dirty)
                from training_client.dataset import inspect_annotation
                self.assertTrue(inspect_annotation(path)[0]['training_eligible'])
            finally:
                d.dirty=False;d.close();self.app.processEvents()

if __name__=='__main__':unittest.main()
