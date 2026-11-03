"""Exercise an already-running owned preview. Explicitly closes that session."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from core.local_rpc import request
from core.process_job import close_windows


def processes():
    command='Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress'
    return json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],encoding='utf-8',errors='replace'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=['desktop_airborne','ue'],required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    deadline=time.monotonic()+180;state=None
    while time.monotonic()<deadline:
        try:
            state=request(50052,'sim.get_state')['payload']
            if state.get('flight_status')=='ready':break
        except (OSError,KeyError,ValueError):pass
        time.sleep(.5)
    assert state and state.get('flight_status')=='ready','Preview did not become ready'
    rows=processes();games=[r for r in rows if r['Name']=='UnrealEditor.exe' and '-game' in (r['CommandLine'] or '') and 'WISEYE-IR-Work' in r['CommandLine']]
    assert len(games)==1,'Requires exactly one known source preview'
    game=games[0];supervisor=game['ParentProcessId'];owned={supervisor}
    while True:
        newer=owned|{r['ProcessId'] for r in rows if r['ParentProcessId'] in owned}
        if newer==owned:break
        owned=newer
    desktops={r['ProcessId'] for r in rows if r['ProcessId'] in owned and 'apps.desktop_app.main' in (r['CommandLine'] or '')}
    assert desktops,'No owned desktop found'
    log=Path(r'E:\Projects\WISEYE-IR-Work\preview-data\logs\session.log');before=len(log.read_text(encoding='utf-8'))
    report=dict(case=args.case,run_id=state['run_id'],owned_pids=sorted(owned),passed=False)
    if args.case=='desktop_airborne':
        request(50051,'sim.resume')
        reply=request(50052,'flight.takeoff',{'device_id':state['drone_id']},timeout=8)
        assert reply['status']=='ok',reply
        time.sleep(5)
        report['airborne_before_close']=request(50052,'sim.get_state')['payload']['flight_status']=='active'
        assert report['airborne_before_close']
        close_windows(desktops)
    else:close_windows({game['ProcessId']})
    print('Close requested: '+args.case,flush=True)
    started=time.monotonic();deadline=started+75
    while time.monotonic()<deadline:
        try:request(50051,'sim.ping')
        except (OSError,ValueError):
            time.sleep(1)
            alive=owned&{r['ProcessId'] for r in processes()}
            if not alive:break
        time.sleep(.25)
    report['close_seconds']=time.monotonic()-started
    report['remaining_owned_pids']=sorted(owned&{r['ProcessId'] for r in processes()})
    report['shutdown_log']=log.read_text(encoding='utf-8')[before:]
    report['landing_confirmed']='无人机已降落' in report['shutdown_log']
    report['passed']=not report['remaining_owned_pids'] and (args.case=='ue' or report['landing_confirmed'])
    (args.output/(args.case+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    assert report['passed'],report


if __name__=='__main__':main()
