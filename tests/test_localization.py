import unittest
from core.localization import set_language, tr


class LocalizationTests(unittest.TestCase):
    def tearDown(self):
        set_language('zh_CN')

    def test_invalid_locale_and_unchanged_wire_values(self):
        with self.assertRaises(ValueError):
            set_language('xx')
        set_language('en_US')
        for value in ('uav-01', 'fixedwing', 'rtsp://127.0.0.1:8554/ir', 'flight.takeoff'):
            self.assertEqual(tr(value), value)

    def test_switch_is_reversible_and_keeps_values(self):
        set_language('en_US')
        self.assertEqual(tr('启动仿真'), 'Start simulation')
        self.assertEqual(tr('三维距离 25.4 m'), 'Slant range 25.4 m')
        set_language('zh_CN')
        self.assertEqual(tr('启动仿真'), '启动仿真')
