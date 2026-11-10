import copy
import unittest
from core.live_devices import changes, apply


class LiveDeviceTests(unittest.TestCase):
    def setUp(self):
        self.before=dict(version=1,scene_id='city',devices=[
            dict(id='uav-01',kind='drone',model_id='mavic3',name='UAV',position_cm=[1,2,3],rotation_deg=[0,0,0]),
            dict(id='ptz-01',kind='gimbal',model_id='eo80',name='EO',position_cm=[4,5,6],rotation_deg=[0,0,0],tracking_target='uav-01')])

    def test_name_change_never_overwrites_an_airborne_position(self):
        desired=copy.deepcopy(self.before);desired['devices'][0]['name']='Renamed'
        patch=changes(self.before,desired)
        self.assertEqual(patch,[dict(id='uav-01',action='update',name='Renamed')])
        moved=copy.deepcopy(self.before);moved['devices'][0]['position_cm']=[1000,2000,3000]
        self.assertEqual(apply(moved,patch)['devices'][0]['position_cm'],[1000,2000,3000])

    def test_add_and_remove_are_separate_from_the_initial_file(self):
        desired=copy.deepcopy(self.before)
        desired['devices'].append(dict(desired['devices'][0],id='uav-02',model_id='fixedwing'))
        patch=changes(self.before,desired)
        self.assertEqual(apply(self.before,patch),desired)
        self.assertEqual(len(self.before['devices']),2)
        self.assertEqual(apply(desired,[dict(id='uav-02',action='remove')]),self.before)

    def test_invalid_defaults_duplicate_and_foreign_fields_rejected(self):
        for edits in ([dict(id='uav-01',action='remove')],
                      [dict(id='ptz-01',action='update',kind='drone')],
                      [dict(id='uav-01',action='update',name='A'),dict(id='uav-01',action='update',name='B')]):
            with self.assertRaises(ValueError):apply(self.before,edits)
