import unittest
from core.runtime_metrics import PerformanceRating


class RatingTests(unittest.TestCase):
    def test_caps_headroom_and_distinct_samples(self):
        model=PerformanceRating()
        data=dict(sample_time_s=1,ue_fps=30,ue_gpu_engine_peak_pct=100)
        for _ in range(10):model.update(data)
        self.assertEqual(model.label,'评估中')
        for i in (2,3):model.update(dict(data,sample_time_s=i))
        self.assertEqual(model.label,'良好')
        self.assertEqual(model.current(now=model.fresh+6)[0],'数据过期')
        for i in range(4,12):model.update(dict(data,sample_time_s=i,ue_fps=10))
        self.assertEqual(model.label,'较差')
        for i in range(12,20):model.update(dict(data,sample_time_s=i,ue_fps=30),'quality')
        self.assertEqual(model.label,'一般')

    def test_preparation_and_memory_budget(self):
        model=PerformanceRating()
        model.update(dict(sample_time_s=1,ue_fps=1,asset_compile_jobs=50))
        self.assertEqual(model.label,'准备中')
        for i in range(2,5):model.update(dict(sample_time_s=i,ue_fps=30,ue_vram_used_bytes=99,ue_vram_budget_bytes=100))
        self.assertEqual(model.label,'较差')
        model.reset();self.assertEqual(model.label,'未评估')
