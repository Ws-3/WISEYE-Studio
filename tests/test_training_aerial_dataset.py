import base64,copy,json,tempfile,unittest
from pathlib import Path
from training_client.aerial import save_raw,validate_raw
from training_client.dataset import annotate,scan,inspect_annotation
from training_client.train import collect,prepare
from training_client.rates import Rates

def raw(run='one'):
    return dict(device_id='uav-01',channel='AERIAL_IR',sensor_id='infrared',source_sensor_id='uav-01/aerial_infrared',modality='infrared',run_id=run,frame_id=run+'/uav-01/aerial_infrared/1',frame_number=1,simulation_time_s=1,width=100,height=80,encoding='jpeg',image_base64=base64.b64encode(b'\xff\xd8'+run.encode()+b'\xff\xd9').decode())

class AerialDatasetTests(unittest.TestCase):
    def test_raw_requires_manual_annotation_and_never_creates_negative_label(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(save_raw(raw(),folder));self.assertFalse(save_raw(raw(),folder))
            self.assertFalse(list(Path(folder).rglob('*.txt')))
            result=scan(folder);self.assertEqual(result['rows'][0]['state'],'待标注')
            with self.assertRaises(ValueError):collect(folder,'infrared')
    def test_manual_person_vehicle_and_drone_export_real_classes(self):
        with tempfile.TemporaryDirectory() as folder:
            save_raw(raw(),folder);path=next(Path(folder).rglob('annotations/*.json'))
            annotate(path,[(0,[0,0,10,10]),(1,[15,5,30,40]),(2,[40,10,90,50])])
            item,_,label=inspect_annotation(path)
            self.assertTrue(item['training_eligible']);self.assertEqual([r.split()[0] for r in label.read_text().splitlines()],['0','1','2'])
            self.assertEqual(scan(folder)['rows'][0]['state'],'可训练')
            self.assertEqual(len(collect(folder,'infrared')[0]),1)
    def test_negative_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            save_raw(raw(),folder);path=next(Path(folder).rglob('annotations/*.json'));before=path.read_bytes()
            with self.assertRaises(ValueError):annotate(path,[])
            self.assertEqual(path.read_bytes(),before)
            item=annotate(path,[],True);self.assertTrue(item['negative_sample']);self.assertEqual(inspect_annotation(path)[2].read_text(),'')
    def test_invalid_boxes_and_changed_images_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            save_raw(raw(),folder);path=next(Path(folder).rglob('annotations/*.json'))
            for box in [[-1,0,5,5],[0,0,101,5],[1,1,0,2],[0,0,float('nan'),4]]:
                with self.assertRaises(ValueError):annotate(path,[(1,box)])
            image=inspect_annotation(path)[1];image.write_bytes(b'changed')
            with self.assertRaises(ValueError):annotate(path,[(0,[0,0,5,5])])
            self.assertEqual(scan(folder)['rows'][0]['state'],'损坏')
    def test_prepare_is_multiclass_and_blocks_same_session_leakage(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ('train','val'):
                save_raw(raw(name),root/name);annotate(next((root/name).rglob('annotations/*.json')),[(1,[0,0,10,10])])
            target=prepare(root/'train',root/'val',root/'prepared','infrared');spec=json.loads(target.read_text())
            self.assertEqual(spec['names'],{'0':'drone','1':'person','2':'vehicle'})
            with self.assertRaises(ValueError):prepare(root/'train',root/'train',root/'bad','infrared')
    def test_source_and_path_identity_are_checked(self):
        for field,value in [('device_id','../../elsewhere'),('channel','AERIAL'),('modality','unknown'),('simulation_time_s',float('nan'))]:
            packet=raw();packet[field]=value
            with self.assertRaises(ValueError):validate_raw(packet)
    def test_aerial_preview_rate_does_not_raise_save_limit(self):
        rates=Rates(30,1,True,max_display=30);self.assertAlmostEqual(rates.period(),1/30)
        with self.assertRaises(ValueError):rates.configure(30,11,True)
    def test_camera_counter_reset_does_not_drop_new_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            a=raw();self.assertTrue(save_raw(a,folder))
            b=raw();b['simulation_time_s']=2
            self.assertTrue(save_raw(b,folder));self.assertEqual(len(scan(folder)['rows']),2)
