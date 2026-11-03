"""Qt checks for registration, paired identities and the three-view workspace."""
import argparse
import base64
import copy
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
import sys

from training_client.preview import QApplication, QImage, Window
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QColor
from training_client.client import validate_pair, save_pair
from training_client.fusion import blend_pair, registration, fusion_transform, comparison
from PySide6.QtCore import QPointF
from training_client.theme import STYLE
from apps.desktop_app.ui.theme import STYLE as SIM_STYLE
from training_client._theme import STYLE as BUNDLED_STYLE


def sample(sensor,width,height,color):
    image=QImage(width,height,QImage.Format.Format_RGB32);image.fill(QColor(color))
    buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly);image.save(buffer,'JPEG',100)
    return dict(frame_id=f'run/device/{sensor}/1',run_id='run',device_id='ptz-02',sensor_id=sensor,
                sample_token='pair',simulation_time_s=1,width=width,height=height,frame_number=1,
                horizontal_fov_deg=90,camera_position_cm=[0,0,0],camera_rotation_pitch_yaw_roll_deg=[0,0,0],
                annotation_status='complete',objects=[],ignored_objects=[],training_eligible=True,negative_sample=True,
                encoding='jpeg',image_base64=base64.b64encode(buffer.data().data()).decode())


def fixture():
    return dict(pair_id='pair',run_id='run',simulation_time_s=1,
                samples={'visible':sample('visible',64,36,'red'),'infrared':sample('infrared',64,52,'blue')})


class FusionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_aspect_ratio_keeps_common_optical_center(self):
        pair=fixture();rect=registration(pair)
        self.assertAlmostEqual(rect.width(),64);self.assertAlmostEqual(rect.height(),36);self.assertAlmostEqual(rect.y(),8)
        fused=blend_pair(pair,.5)
        center=fused.pixelColor(32,26);edge=fused.pixelColor(32,0)
        self.assertLess(abs(center.red()-center.blue()),3)
        self.assertGreater(edge.blue(),250);self.assertLess(edge.red(),3)

    def test_alpha_extremes_and_fov_scaling(self):
        pair=fixture()
        self.assertGreater(blend_pair(pair,0).pixelColor(32,26).red(),250)
        self.assertGreater(blend_pair(pair,1).pixelColor(32,26).blue(),250)
        pair['samples']['visible']['horizontal_fov_deg']=60
        self.assertLess(registration(pair).width(),64)

    def test_refuses_unaligned_or_unsynchronized_pairs(self):
        for field,value in [('run_id','different'),('simulation_time_s',2),('sample_token','different')]:
            pair=fixture();pair['samples']['visible'][field]=value
            with self.assertRaises(ValueError):validate_pair(pair)
        pair=fixture();pair['samples']['visible']['camera_position_cm'][0]=1
        with self.assertRaises(ValueError):blend_pair(pair,mode='strict')
        pair=fixture();pair['samples']['visible']['device_id']='ptz-01'
        with self.assertRaises(ValueError):validate_pair(pair)

    def test_pair_saves_two_negative_labels_in_modality_folders_without_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            save_pair(fixture(),folder)
            self.assertEqual(len(list(Path(folder).rglob('*.txt'))),2)
            self.assertTrue(all(p.read_bytes()==b'' for p in Path(folder).rglob('*.txt')))
            self.assertFalse((Path(folder)/'pairs').exists())
            self.assertTrue((Path(folder)/'visible/images').is_dir());self.assertTrue((Path(folder)/'IR/images').is_dir())
            images=sorted(Path(folder).glob('*/images/*.jpg'))
            self.assertEqual(len(images),2);self.assertEqual(images[0].stem.split('_',1)[1],images[1].stem.split('_',1)[1])

    def test_workspace_theme_three_views_and_stale_clear(self):
        self.assertEqual(STYLE,SIM_STYLE)
        self.assertEqual(STYLE,BUNDLED_STYLE)
        window=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-02',output=Path('unused')))
        try:
            self.assertTrue(window.visible.isChecked() and window.infrared.isChecked())
            window.show_frame(fixture())
            self.assertTrue(all(not tile.canvas.image.isNull() for tile in window.tiles.values()))
            window.alpha.setValue(100);window.show_gt.setChecked(False)
            window.show_error('test disconnect')
            self.assertTrue(all(tile.canvas.image.isNull() for tile in window.tiles.values()))
            self.assertIsNone(window.latest)
        finally:window.close()

    def test_folder_runs_without_simulator_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(__file__).resolve().parents[1]/'training_client'
            shutil.copytree(source,Path(folder)/'training_client',ignore=shutil.ignore_patterns('__pycache__'))
            code="import sys;sys.path.insert(0,sys.argv[1]);from training_client.theme import STYLE;from training_client.preview import Window;assert 'apps.desktop_app' not in sys.modules;print('standalone imports passed')"
            result=subprocess.run([sys.executable,'-I','-c',code,folder],cwd=folder,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
