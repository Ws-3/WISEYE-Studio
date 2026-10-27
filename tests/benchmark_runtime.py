"""Short Windows GPU and fresh-frame samples; not a long-run or latency test."""
import json
import base64
import shutil
import os
import statistics
import subprocess
import time
from pathlib import Path
import socket

ROOT=Path(__file__).resolve().parents[1]


def rpc(command,payload=None):
    with socket.create_connection(('127.0.0.1',50051),5) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id=str(time.time_ns()),command=command,payload=payload or {}))+'\n').encode())
        reply=json.loads(peer.makefile('rb').readline(16*1024*1024))
    assert reply['status']=='ok',reply
    return reply['payload']


def main():
    original=rpc('sim.get_state')
    results=dict(scene_id=original['scene_id'],devices=[d['id'] for d in original['devices']],
                 gpu='Intel Arc B580',samples=[],limitations='8 x 1s counters per profile after 4s warmup; editor/viewport dependent; not end-to-end latency or long-run stability')
    try:
        for profile in ('quality','balanced','economy'):
            rpc('sim.set_performance_profile',dict(profile=profile));time.sleep(4)
            before=rpc('sim.get_state');started=time.monotonic()
            script=r"""
$ueProcess=Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object {$_.CommandLine -like '*WISEYE-Studio*test.uproject*'} | Select-Object -First 1
if (-not $ueProcess) {throw 'No WISEYE editor'}
$pattern='pid_'+$ueProcess.ProcessId+'_*engtype_3d'
Get-Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval 1 -MaxSamples 8 | ForEach-Object {
  $reading=$_
  $_.CounterSamples | Where-Object {$_.InstanceName -like $pattern} | ForEach-Object {
    [pscustomobject]@{utc=$reading.Timestamp.ToUniversalTime().ToString('o');ue_3d_percent=$_.CookedValue}
  }
} | ConvertTo-Json -Compress
"""
            counter_env=dict(os.environ);counter_env.pop('PSModulePath',None)
            process=subprocess.run([shutil.which('pwsh') or 'powershell.exe','-NoProfile','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode('ascii')],capture_output=True,env=counter_env,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=False,timeout=45)
            if process.returncode:raise RuntimeError(process.stderr.decode('utf-8',errors='replace'))
            counters=json.loads(process.stdout.decode('utf-8-sig'))
            after=rpc('sim.get_state');elapsed=time.monotonic()-started
            values=[r['ue_3d_percent'] for r in counters]
            result=dict(profile=profile,gpu_samples=counters,gpu_3d_median=statistics.median(values),
                        gpu_3d_min=min(values),gpu_3d_max=max(values),
                        ue_tick_hz=(after['tick_seq']-before['tick_seq'])/elapsed,
                        fresh_frame_hz={key:(value['completed_frames']-before['streams'][key]['completed_frames'])/elapsed for key,value in after['streams'].items()})
            results['samples'].append(result)
            print(json.dumps({k:v for k,v in result.items() if k!='gpu_samples'}),flush=True)
    finally:
        rpc('sim.set_performance_profile',dict(profile=original['performance_profile']))
        (ROOT/'docs/evidence/runtime_performance_20261021.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
