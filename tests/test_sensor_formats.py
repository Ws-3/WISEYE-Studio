import struct
import unittest
from core.sensor_formats import pointcloud2,metavision_events


class SensorFormatTests(unittest.TestCase):
    def packet(self):return dict(lidar_downsampled=False,lidar_coordinate_frame='sensor_local_x_forward_y_right_z_up',lidar_units='meters',lidar_capture_time_s=1.125,lidar_sensor_id='ptz-01/lidar',lidar_points_m=[[1,2,3]])
    def test_ros_handedness_and_timestamp(self):
        r=pointcloud2(self.packet());self.assertEqual(struct.unpack('<fff',r['data']),(1,-2,3));self.assertEqual(r['header']['stamp'],{'sec':1,'nanosec':125000000});self.assertEqual(r['point_step'],12);self.assertEqual(r['row_step'],12)
    def test_preview_cannot_masquerade_as_full_scan(self):
        with self.assertRaises(ValueError):pointcloud2(dict(self.packet(),lidar_downsampled=True))
    def test_empty_scan_is_valid(self):
        r=pointcloud2(dict(self.packet(),lidar_points_m=[]));self.assertEqual(r['width'],0);self.assertEqual(r['data'],b'')
    def test_bad_point_rejected(self):
        with self.assertRaises(ValueError):pointcloud2(dict(self.packet(),lidar_points_m=[[float('nan'),1,2]]))
    def test_event_layout_and_polarity(self):
        r=metavision_events(dict(columns='x,y,t_us,p',width=640,height=480,events=[[1,2,100,-1],[3,4,120,1]]))
        self.assertEqual(r.dtype.itemsize,16);self.assertEqual(r['p'].tolist(),[0,1]);self.assertEqual(r['t'].tolist(),[100,120])
    def test_event_time_reversal_rejected(self):
        with self.assertRaises(ValueError):metavision_events(dict(columns='x,y,t_us,p',width=640,height=480,events=[[1,2,100,1],[1,2,90,1]]))
    def test_invalid_coordinate_rejected(self):
        with self.assertRaises(ValueError):metavision_events(dict(columns='x,y,t_us,p',width=640,height=480,events=[[640,2,100,1]]))
    def test_pixel_preview_is_not_event_stream(self):
        with self.assertRaises(ValueError):metavision_events(dict(events=[]))


if __name__=='__main__':unittest.main()
