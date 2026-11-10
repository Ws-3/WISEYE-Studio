import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from scripts.infrared_baseline import (pixels_summary, polygon_mask, box_mask,
    target_proxies, distribution_gap, measure, cropped_boxes, normalized_box)
from scripts.infrared_reference_data import yolo_boxes


class InfraredBaselineTests(unittest.TestCase):
    def test_bright_is_distinct_from_clipping(self):
        result=pixels_summary([210,210,210])
        self.assertEqual(result['bright_ge204'],1)
        self.assertEqual(result['clipped_ge254'],0)

    def test_empty_roi_is_unavailable(self):
        self.assertIsNone(pixels_summary([]))

    def test_road_roi_excludes_targets(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            a=np.full((20,20),100,dtype=np.uint8);a[7:13,7:13]=250
            Image.fromarray(a).save(root/'frame.png')
            r=measure(dict(path='frame.png',boxes=[{'class_id':0,'xywh_normalized':[.5,.5,.3,.3]}],
                road_polygons=[[[0,0],[1,0],[1,1],[0,1]]]),root)
            self.assertEqual(r['road']['mean'],100)
            self.assertGreater(r['frame']['mean'],100)

    def test_flat_background_cnr_is_null(self):
        a=np.full((30,30),30.);a[13:17,13:17]=60
        t=target_proxies(a,[dict(class_id=0,xywh_normalized=[.5,.5,4/30,4/30])],np.ones(a.shape,bool))[0]
        self.assertEqual(t['signed_contrast_dn'],30)
        self.assertIsNone(t['cnr_proxy'])

    def test_small_ring_is_unavailable(self):
        t=target_proxies(np.zeros((10,10)),[dict(class_id=0,xywh_normalized=[.5,.5,1,1])],np.ones((10,10),bool))[0]
        self.assertIsNone(t['signed_contrast_dn'])

    def test_histogram_distance_known_shift(self):
        a=np.zeros(256);b=a.copy();a[100]=1;b[120]=1
        self.assertEqual(distribution_gap(a,b),20)
        self.assertEqual(distribution_gap(a,a),0)

    def test_invalid_geometry_rejected(self):
        for p in [[[0,0],[2,0],[1,1]],[[0,0],[1,1]]]:
            with self.assertRaises(ValueError):polygon_mask((20,20),p)
        with self.assertRaises(ValueError):normalized_box([.5,.5,-.1,.2],(20,20))

    def test_label_parser_rejects_bad_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.txt';p.write_text('0 0.5 0.5 -0.2 0.1')
            with self.assertRaises(ValueError):yolo_boxes(p)

    def test_border_crop_removes_white_and_translates_boxes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);a=np.full((712,840),255,dtype=np.uint8);a[100:-100,100:-100]=80
            Image.fromarray(a).save(root/'frame.png')
            entry=dict(path='frame.png',crop_border_px=100,boxes_coordinate_space='raw',
                boxes=[dict(class_id=0,xywh_normalized=[420/840,356/712,64/840,52/712])])
            r=measure(entry,root)
            self.assertEqual((r['width'],r['height']),(640,512))
            self.assertEqual(r['frame']['mean'],80)
            b=cropped_boxes(entry,(512,640))[0]['xywh_normalized']
            np.testing.assert_allclose(b,[.5,.5,.1,52/512],atol=.004)

    def test_crop_coordinates_must_be_explicit(self):
        with self.assertRaises(ValueError):cropped_boxes(dict(crop_border_px=100,boxes=[]),(512,640))

    def test_image_change_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);Image.new('L',(10,10),50).save(root/'a.png')
            with self.assertRaises(ValueError):measure(dict(path='a.png',sha256='bad'),root)

    def test_polarity_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);Image.new('L',(10,10),30).save(root/'a.png')
            r=measure(dict(path='a.png',polarity='black_hot'),root)
            self.assertEqual(r['frame']['p50'],30)


if __name__=='__main__':unittest.main()
