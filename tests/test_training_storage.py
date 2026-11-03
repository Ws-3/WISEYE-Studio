import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.test_training_receiver import packet
from training_client.client import save_pair,save_sample
from training_client.storage import weather_name
from training_client.train import collect,prepare


def pair_fixture(session='run',suffix='one'):
    environment=dict(clouds=0,rain=0,fog=0,time_override=True,hour=12)
    samples={}
    for sensor in ('visible','infrared'):
        item=packet()
        item.update(sensor_id=sensor,frame_id=f'{session}/ptz-02/{sensor}/{suffix}',run_id=session,scene_id='city',
                    sample_token=suffix,simulation_time_s=1,scenario_models=['mavic3'],environment=dict(environment),context_source='capture_tick')
        # Distinct fake JPEG bytes suffice for storage/hash tests; Qt rendering
        # is covered separately with decoded real JPEG fixtures.
        item['image_base64']=base64.b64encode(b'\xff\xd8'+f'{session}/{sensor}/{suffix}'.encode()+b'\xff\xd9').decode()
        samples[sensor]=item
    return dict(pair_id=suffix,run_id=session,simulation_time_s=1,samples=samples)


class StorageTests(unittest.TestCase):
    def test_readable_names_negative_model_and_shared_suffix(self):
        pair=pair_fixture()
        with tempfile.TemporaryDirectory() as folder:
            group=save_pair(pair,folder);sample=Path(folder)
            images=list(sample.glob('*/images/*.jpg'));self.assertEqual(len(images),2)
            self.assertTrue(any(p.name.startswith('VIS_Mavic3_Clear-Day_city_') for p in images))
            self.assertTrue(any(p.name.startswith('IR_Mavic3_Clear-Day_city_') for p in images))
            self.assertEqual(len({p.stem.split('_',1)[1] for p in images}),1)
            self.assertFalse((Path(folder)/'pairs').exists())
            for path in sample.glob('*/annotations/*.json'):
                item=json.loads(path.read_text());self.assertTrue(item['negative_sample'])
                self.assertTrue((sample/item['counterpart_directory']/'images'/item['counterpart_image']).is_file())
            self.assertEqual(save_pair(pair,folder),group)
            save_pair(pair_fixture(suffix='two'),folder)
            for modality in ('visible','IR'):
                self.assertEqual(len(list((sample/modality/'images').glob('*.jpg'))),2)
                self.assertEqual(len(list((sample/modality/'labels').glob('*.txt'))),2)
            self.assertFalse((sample/'samples').exists())

    def test_policy_exclusion_skips_whole_pair(self):
        pair=pair_fixture();packet=pair['samples']['infrared']
        packet.update(ignored_objects=[dict(class_id=0,bbox_xyxy=[1,2,3,4])],training_eligible=False,negative_sample=False)
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(save_pair(pair,folder));self.assertFalse(list(Path(folder).rglob('*.jpg')))

    def test_failed_write_never_publishes_half_pair(self):
        original=Path.write_bytes
        def write(path,data):
            if path.name.startswith('IR_') and path.suffix=='.jpg':raise OSError('simulated full disk')
            return original(path,data)
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(Path,'write_bytes',write):
                with self.assertRaises(OSError):save_pair(pair_fixture(),folder)
            self.assertFalse(list(Path(folder).rglob('*.jpg')))

    def test_weather_tags_and_unknown_are_explicit(self):
        self.assertEqual(weather_name(None),'EnvUnknown')
        self.assertEqual(weather_name(dict(clouds=0,rain=0,fog=0)),'Clear')
        self.assertEqual(weather_name(dict(clouds=.2,rain=.1,fog=.3,time_override=True,hour=22)),'Clouds-Rain-Fog-Night')
        self.assertEqual(weather_name(dict(clouds=float('nan'),rain=0,fog=0)),'EnvUnknown')
        pair=pair_fixture();pair['samples']['infrared']['environment']['rain']=1
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):save_pair(pair,folder)

    def test_reader_selects_modality_and_rejects_broken_pairs(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);group=save_pair(pair_fixture(),root/'train');save_pair(pair_fixture('val'),root/'val')
            with self.assertRaises(ValueError):collect(root/'train')
            images,_,_=collect(root/'train','infrared');self.assertEqual(len(images),1);self.assertTrue(Path(images[0]).name.startswith('IR_'))
            spec=prepare(root/'train',root/'val',root/'experiment','infrared');self.assertTrue(spec.is_file())
            next((root/'train/visible/images').glob('VIS_*.jpg')).unlink()
            with self.assertRaises(ValueError):collect(root/'train','infrared')

    def test_publish_failure_rolls_back_only_new_files(self):
        original=Path.rename
        def rename(path,target):
            if '/IR/annotations/' in target.as_posix():raise OSError('publish failed')
            return original(path,target)
        with tempfile.TemporaryDirectory() as folder:
            save_pair(pair_fixture(),folder)
            before={p.relative_to(folder):p.read_bytes() for p in Path(folder).rglob('*') if p.is_file()}
            with patch.object(Path,'rename',rename):
                with self.assertRaises(OSError):save_pair(pair_fixture(suffix='next'),folder)
            after={p.relative_to(folder):p.read_bytes() for p in Path(folder).rglob('*') if p.is_file()}
            self.assertEqual(before,after)

    def test_reader_accepts_legacy_group_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);save_pair(pair_fixture(),root)
            legacy=root/'samples'/'legacy'
            for source in list(root.glob('*/annotations/*.json')):
                data=json.loads(source.read_text());data['dataset_schema']=2;data.pop('counterpart_directory')
                source.write_text(json.dumps(data))
            for modality in ('visible','IR'):
                for source in list((root/modality).rglob('*')):
                    if source.is_file():
                        target=legacy/source.relative_to(root/modality);target.parent.mkdir(parents=True,exist_ok=True);source.rename(target)
            self.assertEqual(len(collect(root,'infrared')[0]),1)

    def test_unknown_sensor_name_is_safe_and_new_session_is_unique(self):
        item=pair_fixture()['samples']['visible'];item['scenario_models']=['../../escape']
        with tempfile.TemporaryDirectory() as folder:
            name=save_sample(item,folder)
            self.assertNotIn('/',name);self.assertNotIn('\\',name)
            item['run_id']='another';item['frame_id']='another/frame'
            self.assertNotEqual(name,save_sample(item,folder))
