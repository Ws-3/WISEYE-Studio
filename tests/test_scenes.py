import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from core.scenes import SceneStore, validate_scene


def scene():
    return dict(version=1, id='sample', name='测试场景', map='/Game/WISEYE/Scenes/sample/Map', rig='standard_v1', prepared=True,
                gimbal_location_cm=[0,0,0], flight_origin_cm=[100,0,600], overview_location_cm=[0,0,1000],
                overview_rotation_deg=[-30,0,0], flight_radius_cm=600, period_s=24, vertical_amplitude_cm=150, fov_deg=25)


class SceneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = SceneStore(self.root)
        self.store.project.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def pack(self, files=None, bad_hash=False):
        files = files or {'Content/WISEYE/Scenes/sample/Map.umap': b'fixture map'}
        manifest = dict(scene=scene(), files={name: '0'*64 if bad_hash else hashlib.sha256(value).hexdigest() for name,value in files.items()})
        path = self.root/'sample.zip'
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr('scene.json',json.dumps(manifest))
            for name,value in files.items():
                archive.writestr(name,value)
        return path

    def test_install_and_refuse_overwrite(self):
        path=self.pack()
        self.store.import_pack(path)
        items, errors=self.store.list()
        self.assertFalse(errors)
        self.assertTrue(items[0]['installed'])
        with self.assertRaises(ValueError): self.store.import_pack(path)
        self.assertEqual(self.store.map_file(scene()['map']).read_bytes(),b'fixture map')

    def test_hash_failure_is_atomic(self):
        with self.assertRaises(ValueError): self.store.import_pack(self.pack(bad_hash=True))
        self.assertFalse(self.store.map_file(scene()['map']).exists())
        self.assertEqual(self.store.list(),([],[]))

    def test_traversal_and_executable_rejected(self):
        for name in ['Content/WISEYE/Scenes/sample/../../evil.uasset', 'Content/WISEYE/Scenes/sample/run.py',
                     'C:/evil.uasset', 'Content/WISEYE/Scenes/sample/x:stream.uasset']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.store.import_pack(self.pack({name:b'x'}))

    def test_invalid_configuration(self):
        for key,value in [('id','../bad'), ('map','/Game/../bad'), ('fov_deg',float('nan')),
                          ('period_s',0),('flight_origin_cm',[True,0,0]),('gimbal_location_cm',[0,0])]:
            data=scene(); data[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): validate_scene(data)

    def test_one_bad_manifest_does_not_hide_other_scenes(self):
        self.store.import_pack(self.pack())
        (self.store.directory/'broken.json').write_text('{',encoding='utf-8')
        items,errors=self.store.list()
        self.assertEqual(len(items),1)
        self.assertEqual(len(errors),1)

    def test_missing_map_is_not_installed(self):
        self.store.register(scene(), require_map=False)
        self.assertFalse(self.store.list()[0][0]['installed'])

    def test_required_asset_mismatch_refuses_install(self):
        path=self.pack()
        with zipfile.ZipFile(path) as source:
            contents={name:source.read(name) for name in source.namelist()}
        manifest=json.loads(contents['scene.json'])
        manifest['required_assets']={'/Game/SharedMesh':'0'*64}
        contents['scene.json']=json.dumps(manifest).encode()
        with zipfile.ZipFile(path,'w') as output:
            for name,value in contents.items(): output.writestr(name,value)
        with self.assertRaisesRegex(ValueError,'SharedMesh'):
            self.store.import_pack(path)
        self.assertFalse(self.store.map_file(scene()['map']).exists())


if __name__ == '__main__': unittest.main()
