import unittest
from core.runtime_metrics import PerformanceAdvice,number


class RuntimeMetricsTests(unittest.TestCase):
    def test_unknown_values_do_not_become_zero_load(self):
        self.assertIsNone(number({},'gpu'))
        for value in [True,-1,float('nan'),'20']:
            self.assertIsNone(number({'gpu':value},'gpu'))
        self.assertEqual(PerformanceAdvice().update({'sample_time_s':1}),'')

    def test_advice_requires_distinct_sustained_samples_and_recovers(self):
        monitor=PerformanceAdvice()
        data=dict(sample_time_s=1,ue_vram_used_bytes=95,ue_vram_budget_bytes=100,ue_fps=10)
        self.assertEqual(monitor.update(data),'')
        for _ in range(5):self.assertEqual(monitor.update(data),'')
        self.assertEqual(monitor.update(dict(data,sample_time_s=2)),'')
        self.assertIn('显存',monitor.update(dict(data,sample_time_s=3)))
        self.assertEqual(monitor.update(dict(data,sample_time_s=4,ue_vram_used_bytes=50,ue_fps=30)),'')
        monitor.reset();self.assertEqual(monitor.message,'')

    def test_loading_never_accumulates_low_fps_warning(self):
        monitor=PerformanceAdvice()
        for i in range(1,8):
            message=monitor.update(dict(sample_time_s=i,ue_fps=4,asset_compile_jobs=15))
            self.assertIn('准备',message);self.assertNotIn('持续偏低',message)
        for i in (8,9):self.assertEqual(monitor.update(dict(sample_time_s=i,ue_fps=4,asset_compile_jobs=0)),'')
        self.assertIn('持续偏低',monitor.update(dict(sample_time_s=10,ue_fps=4,asset_compile_jobs=0)))
        self.assertIn('准备',monitor.update(dict(sample_time_s=11,ue_fps=4),preparing=True))
