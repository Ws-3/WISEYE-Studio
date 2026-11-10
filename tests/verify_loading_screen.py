import unittest
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.main_window import MainWindow
from core.config import AppConfig

class LoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.w=MainWindow(AppConfig());self.w.show();self.loading=self.w.loading_screen
        self.w.health_timer.stop()
    def tearDown(self):
        self.w.client.ready=False;self.w.air_client.ready=False;self.w.close()
    def test_real_stages_and_full_readiness(self):
        s=self.loading;s.begin({'id':'city','name':'测试城市'})
        self.assertTrue(s.pulse.timer.isActive())
        data=dict(scene_id='city',run_id='new',devices=[{'id':'uav-01'}],population={'pending':True})
        s.observe(data);self.assertEqual(s.stage,'population');self.assertTrue(s.active)
        data['population']['pending']=False;data['runtime_hardware']={'shader_compile_jobs':3}
        s.observe(data);self.assertTrue(s.active)
        data['runtime_hardware']['shader_compile_jobs']=0;s.observe(data);self.assertEqual(s.stage,'devices')
        self.w.client.ready=self.w.air_client.ready=True;s.observe(data)
        self.assertFalse(s.active);self.assertFalse(s.pulse.timer.isActive());self.assertTrue(s.isHidden())
    def test_switch_does_not_accept_old_run_or_other_scene(self):
        self.w.state={'run_id':'old'};s=self.loading;s.begin({'id':'city_large'},switch=True)
        self.w.client.ready=self.w.air_client.ready=True
        for scene,run in [('city','new'),('city_large','old')]:
            s.observe(dict(scene_id=scene,run_id=run,devices=[{}]));self.assertTrue(s.active)
    def test_first_frame_and_distinct_stable_samples(self):
        self.w.pages.setCurrentIndex(1);s=self.loading;s.begin({'id':'city'})
        self.w.client.ready=self.w.air_client.ready=True
        data=dict(scene_id='city',run_id='new',devices=[{}],runtime_hardware={'sample_time_s':1})
        s.observe(data);self.assertTrue(s.active)
        key=next(iter(self.w.gallery.displayed()));self.w.gallery.frames[key]=object();self.w.gallery.messages.pop(key,None)
        for _ in range(5):s.observe(data)
        self.assertTrue(s.active)
        for stamp in (2,3):data['runtime_hardware']['sample_time_s']=stamp;s.observe(data)
        self.assertFalse(s.active)
        self.w.pages.setCurrentIndex(3);s.begin({'id':'city'})
        for stamp in (4,5,6):data['runtime_hardware']['sample_time_s']=stamp;s.observe(data)
        self.assertFalse(s.active)
    def test_background_failure_and_animation_stop(self):
        s=self.loading;s.begin({'id':'city'});s.hide()
        self.assertFalse(s.pulse.timer.isActive());self.assertFalse(s.clock.isActive());self.assertTrue(s.active)
        s.reveal();self.assertTrue(s.pulse.timer.isActive())
        s.fail('真实错误');self.assertTrue(s.failed);self.assertFalse(s.pulse.timer.isActive())
        self.assertEqual(s.detail.text(),'真实错误');s.stopped();self.assertTrue(s.failed)
        s.begin({'id':'city'});s.stopped();self.assertFalse(s.active)

if __name__=='__main__':unittest.main()
