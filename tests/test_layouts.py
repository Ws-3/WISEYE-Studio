import json
import tempfile
from pathlib import Path
import unittest
from core.layouts import LayoutStore


class LayoutTests(unittest.TestCase):
    def test_initial_pose_roundtrip_is_separate_and_invalid_write_preserves_saved_file(self):
        with tempfile.TemporaryDirectory() as root:
            store = LayoutStore(root)
            scene = dict(id='original', flight_origin_cm=[100,200,300], gimbal_location_cm=[0,0,5])
            data = store.load(scene)
            data['flight_origin_cm'][0] = 450
            path = store.save(data)
            self.assertEqual(scene['flight_origin_cm'], [100,200,300])
            self.assertEqual(store.load(scene)['flight_origin_cm'], [450,200,300])
            data['flight_origin_cm'][0] = float('nan')
            with self.assertRaises(ValueError):
                store.save(data)
            self.assertEqual(json.loads(path.read_text())['flight_origin_cm'], [450,200,300])
            self.assertEqual(list(path.parent.glob('*.tmp')), [])

    def test_invalid_scene_id_cannot_escape_layout_directory(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                LayoutStore(root).load(dict(id='../other'))

    def test_named_presets_remain_separate_from_active_and_other_scenes(self):
        with tempfile.TemporaryDirectory() as root:
            store = LayoutStore(root)
            data = dict(version=1,scene_id='original',flight_origin_cm=[100,200,300],gimbal_location_cm=[0,0,5])
            active = store.save(data).read_bytes()
            named = store.save_preset(data, '沙漠近距离观察')
            self.assertEqual(store.load_preset('original',named['preset_id'])['name'], '沙漠近距离观察')
            data['flight_origin_cm'][0] = 900
            store.save_preset(data, '更新后的观察点', named['preset_id'])
            self.assertEqual(store.load_preset('original',named['preset_id'])['flight_origin_cm'][0],900)
            self.assertEqual((store.directory/'original.json').read_bytes(),active)
            self.assertEqual(store.list_presets('test_range'), ([],[]))

    def test_duplicate_names_and_unknown_update_ids_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            store=LayoutStore(root)
            data=dict(version=1,scene_id='original',flight_origin_cm=[0,0,20],gimbal_location_cm=[0,0,0])
            saved=store.save_preset(data,'Demo')
            with self.assertRaises(ValueError):
                store.save_preset(data,'demo')
            with self.assertRaises(OSError):
                store.save_preset(data,'other','missing')
            with self.assertRaises(ValueError):
                store.load_preset('original','../escape')
            self.assertEqual(len(store.list_presets('original')[0]),1)
            self.assertEqual(store.load_preset('original',saved['preset_id'])['name'],'Demo')

    def test_broken_preset_does_not_hide_valid_presets(self):
        with tempfile.TemporaryDirectory() as root:
            store=LayoutStore(root)
            data=dict(version=1,scene_id='original',flight_origin_cm=[0,0,20],gimbal_location_cm=[0,0,0])
            saved=store.save_preset(data,'Good')
            (store.directory/'Presets/original/broken.json').write_text('{broken',encoding='utf-8')
            items,errors=store.list_presets('original')
            self.assertEqual(items[0]['preset_id'],saved['preset_id'])
            self.assertEqual(len(errors),1)
