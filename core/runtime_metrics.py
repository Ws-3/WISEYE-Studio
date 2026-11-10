"""Advice uses fresh simulation-host samples; no inference from GPU brand alone."""
import math
import statistics
import time
from collections import deque


def number(data,key):
    value=data.get(key)
    return float(value) if type(value) in (int,float) and math.isfinite(value) and value>=0 else None


class PerformanceAdvice:
    def __init__(self):self.reset()
    def reset(self):self.last_sample=None;self.counts={};self.message=''
    def update(self,data,preparing=False):
        sample=number(data,'sample_time_s')
        if sample is None:self.reset();return ''
        if sample==self.last_sample:return self.message
        self.last_sample=sample
        used,budget=number(data,'ue_vram_used_bytes'),number(data,'ue_vram_budget_bytes')
        ram,total=number(data,'system_ram_used_bytes'),number(data,'system_ram_total_bytes')
        fps=number(data,'ue_fps')
        preparing=preparing or number(data,'asset_compile_jobs') not in (None,0) or number(data,'shader_compile_jobs') not in (None,0)
        conditions={
            '显存接近驱动预算，建议切换节能档或减少同时采集的画面':budget is not None and budget>0 and used is not None and used/budget>=.9,
            '系统内存占用较高，建议关闭其他大型程序':total is not None and total>0 and ram is not None and ram/total>=.9,
            'UE 帧率持续偏低，可降低人车密度或减少传感器采集，并检查性能档位':not preparing and fps is not None and fps<20}
        for key,condition in conditions.items():self.counts[key]=self.counts.get(key,0)+1 if condition else 0
        self.message='；'.join(key for key in conditions if self.counts[key]>=3)
        if preparing:
            self.message='场景资源正在准备，完成后再评估帧率'+('；'+self.message if self.message else '')
        return self.message


class PerformanceRating:
    """Rolling measured headroom relative to the selected FPS cap, not GPU brand."""
    def __init__(self):self.reset()
    def reset(self):
        self.samples=deque(maxlen=8);self.last=None;self.fresh=None;self.label='未评估';self.reason='等待实时运行数据'
    def current(self,now=None):
        if self.fresh is not None and (time.monotonic() if now is None else now)-self.fresh>5:
            return '数据过期','硬件统计超过5秒未更新，请检查仿真推进'
        return self.label,self.reason
    def update(self,data,profile='economy',preparing=False):
        stamp=number(data,'sample_time_s')
        if stamp is None:self.reset();return self.label,self.reason
        if stamp==self.last:return self.current()
        self.last=stamp;self.fresh=time.monotonic()
        if preparing or number(data,'asset_compile_jobs') not in (None,0) or number(data,'shader_compile_jobs') not in (None,0):
            self.samples.clear();self.label='准备中';self.reason='正在加载、编译场景或生成人车，完成后再评估';return self.label,self.reason
        fps=number(data,'ue_fps')
        if fps is None:self.label='未评估';self.reason='未提供实测帧率';return self.label,self.reason
        def ratio(used,total):
            a,b=number(data,used),number(data,total)
            return a/b if a is not None and b is not None and b>0 else 0.
        self.samples.append((fps,ratio('ue_vram_used_bytes','ue_vram_budget_bytes'),ratio('system_ram_used_bytes','system_ram_total_bytes')))
        if len(self.samples)<3:self.label='评估中';self.reason='等待至少3个新硬件样本';return self.label,self.reason
        fps,vram,ram=(statistics.median(x[i] for x in self.samples) for i in range(3))
        target=dict(economy=30,balanced=45,quality=60).get(profile,30)
        poor=fps<target*.5 or vram>=.97 or ram>=.97
        fair=fps<target*.8 or vram>=.85 or ram>=.90
        self.label='较差' if poor else '一般' if fair else '良好'
        reasons=[]
        if fps<target*.8:reasons.append(f'实测{fps:.1f} / 目标上限{target} FPS')
        if vram>=.85:reasons.append('显存预算余量较小')
        if ram>=.9:reasons.append('系统内存余量较小')
        self.reason='；'.join(reasons) or f'实测{fps:.1f} FPS，当前档位运行平稳'
        return self.label,self.reason
