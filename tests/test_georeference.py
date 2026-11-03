import math
import tempfile
import unittest
from unittest.mock import patch
from core.georeference import GeoReference,GeoReferenceStore,ecef,geodetic,A,F
from integrations.gimbal_client import GimbalClient,GimbalError


class GeoTests(unittest.TestCase):
    def test_known_wgs84_axes(self):
        for geo,expected in [((0,0,0),(A,0,0)),((0,90,0),(0,A,0)),((90,0,0),(0,0,A*(1-F)))]:
            for actual,want in zip(ecef(*geo),expected):self.assertAlmostEqual(actual,want,places=6)
            recovered=geodetic(*expected)
            self.assertAlmostEqual(recovered[0],geo[0],places=8)
            self.assertAlmostEqual(recovered[2],geo[2],places=6)

    def test_heading_and_centimeter_units(self):
        r=GeoReference('city',30,120,100,(1200,-500,4000),0)
        self.assertEqual(r.world_to_enu((2200,-500,4000)),(0,10,0))
        self.assertEqual(r.world_to_enu((1200,500,4000)),(10,0,0))
        rotated=GeoReference('city',30,120,100,(0,0,0),90)
        east,north,up=rotated.world_to_enu((10000,0,100))
        self.assertAlmostEqual(east,100);self.assertAlmostEqual(north,0);self.assertAlmostEqual(up,1)

    def test_round_trip_for_longitudes_poles_and_headings(self):
        for lat,lon in [(0,0),(30,120),(-45,-160),(89.9,179.999)]:
            for heading in (0,45,180,270):
                r=GeoReference('city',lat,lon,120,(100,-250,4000),heading)
                for point in ((100,-250,4000),(123456,-45678,19000),(-99900,100000,0)):
                    recovered=r.geodetic_to_world(*r.world_to_geodetic(point))
                    for actual,expected in zip(recovered,point):self.assertAlmostEqual(actual,expected,places=4)

    def test_unconfigured_store_never_fabricates_geography(self):
        with tempfile.TemporaryDirectory() as folder:
            store=GeoReferenceStore(folder);self.assertIsNone(store.load('city'))
            r=GeoReference('city',31.2,121.5,25,(-27000,-2000,4000),45)
            store.save(r);self.assertEqual(store.load('city'),r)
            self.assertEqual(store.load('city').to_dict()['purpose'],'simulation_anchor')
            with self.assertRaises(ValueError):store.load('../bad')

    def test_invalid_values_and_height_reference_rejected(self):
        for lat,lon,h in [(True,0,0),(91,0,0),(0,181,0),(0,0,float('nan'))]:
            with self.assertRaises(ValueError):GeoReference('city',lat,lon,h)
        data=GeoReference('city',0,0,0).to_dict();data['height_reference']='mean_sea_level'
        with self.assertRaises(ValueError):GeoReference.from_dict(data)

    def test_sdk_rejects_scene_mismatch_before_pointing(self):
        c=GimbalClient('ptz-02')
        with patch.object(c,'state',return_value=dict(scene_id='other',run_id='run')),patch.object(c,'request') as request:
            with self.assertRaises(GimbalError):c.point_at_geodetic(GeoReference('city',0,0,0),0,0,0)
            request.assert_not_called()

    def test_sdk_sends_sensor_and_current_session(self):
        c=GimbalClient('ptz-02')
        with patch.object(c,'state',return_value=dict(scene_id='city',run_id='run')),patch.object(c,'request') as request:
            c.point_at_world([100,200,300],'infrared',run_id='run')
            request.assert_called_once_with('gimbal.point_at',position_cm=(100.,200.,300.),sensor='infrared',scene_id='city',run_id='run')
            request.reset_mock()
            with self.assertRaises(GimbalError):c.point_at_world([100,200,300],run_id='stale')
            request.assert_not_called()

    def test_coordinate_export_does_not_invent_unconfigured_latitude(self):
        c=GimbalClient();state=dict(scene_id='city',run_id='run',devices=[dict(id='uav-01',kind='drone',position_cm=[0,0,100])])
        with patch.object(c,'state',return_value=state):
            self.assertIsNone(c.coordinates()['devices'][0]['geodetic'])
            result=c.coordinates(GeoReference('city',30,120,100))
            self.assertAlmostEqual(result['devices'][0]['geodetic']['ellipsoid_height_m'],101,places=6)


if __name__=='__main__':unittest.main()
