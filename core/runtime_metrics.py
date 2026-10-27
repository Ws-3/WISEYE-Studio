"""Advice uses fresh simulation-host samples; no inference from GPU brand alone."""
import math


def number(data,key):
    value=data.get(key)
    return float(value) if type(value) in (int,float) and math.isfinite(value) and value>=0 else None


class PerformanceAdvice:
    def __init__(self):self.reset()
    def reset(self):self.last_sample=None;self.counts={};self.message=''
    def update(self,data):
        sample=number(data,'sample_time_s')
        if sample is None:self.reset();return ''
        if sample==self.last_sample:return self.message
        self.last_sample=sample
        used,budget=number(data,'ue_vram_used_bytes'),number(data,'ue_vram_budget_bytes')
        ram,total=number(data,'system_ram_used_bytes'),number(data,'system_ram_total_bytes')
        fps=number(data,'ue_fps')
        conditions={
            '显存接近驱动预算，建议切换节能档或减少同时采集的画面':budget is not None and budget>0 and used is not None and used/budget>=.9,
            '系统内存占用较高，建议关闭其他大型程序':total is not None and total>0 and ram is not None and ram/total>=.9,
            'UE 帧率持续偏低，加载完成后可切换节能档或减少传感器采集':fps is not None and fps<20}
        for key,condition in conditions.items():self.counts[key]=self.counts.get(key,0)+1 if condition else 0
        self.message='；'.join(key for key in conditions if self.counts[key]>=3)
        return self.message
