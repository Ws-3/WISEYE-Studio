"""Own a source-preview session, including launcher descendants and training."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from core.process_job import ProcessJob, close_windows
from core.local_rpc import request
from .session_shutdown import land_owned_fleet


def run(args):
    root = Path(__file__).resolve().parents[2]
    data = Path(args.data)
    scene = json.loads((data / f'ue5/WISEYE/Config/WISEYE/Scenes/{args.scene}.json').read_text(encoding='utf-8-sig'))
    job = ProcessJob(); game = desktop = None; run_id = None
    environment = dict(os.environ, WISEYE_DATA_DIR=str(data), WISEYE_RESOURCES_DIR=str(root), PYTHONUTF8='1')
    status_file=data/'logs'/('startup-'+uuid.uuid4().hex+'.json')
    environment['WISEYE_SESSION_STATUS']=str(status_file)
    with (data/'logs/session.log').open('a', encoding='utf-8', buffering=1) as log:
        def report(message):log.write(time.strftime('%Y-%m-%d %H:%M:%S ') + message + '\n')
        def status(stage,message):
            temporary=status_file.with_suffix('.tmp')
            temporary.write_text(json.dumps(dict(stage=stage,message=message,run_id=run_id,scene_id=args.scene)),encoding='utf8')
            temporary.replace(status_file)
            report(message)
        def spawn(command, name):
            startup=None
            if os.name=='nt' and name=='ue-launch':
                startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
            with (data/f'logs/{name}.log').open('ab') as output:
                return job.spawn(command, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                                 stdout=output, stderr=output,startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            status('loading','正在启动 UE，加载场景和着色器…')
            game = spawn([args.editor, args.project, scene['map']+'?game=/Script/test.WiseEyeGameMode?wiseeye_scene='+args.scene,
                          '-game','-windowed','-ResX=1280','-ResY=720','-nosplash','-WiseEyeHiddenWindow','-WinX=-32000','-WinY=-32000','-ExecCmds=t.IdleWhenNotForeground 0',
                          '-WiseEyeDataDir='+str(data), '-UserDir='+str(data/'UE'), '-simlogdir='+str(data/'logs')], 'ue-launch')
            flight = spawn([sys.executable,'-m','integrations.ProjectAirSim.run_wiseye_flight','--scene',args.scene,'--loops','0'], 'flight')
            pythonw = str(Path(sys.executable).with_name('pythonw.exe'))
            desktop = spawn([pythonw,'-m','apps.desktop_app.main'], 'desktop-launch')
            report(f'Session started; game={game.pid}, flight={flight.pid}, desktop={desktop.pid}')
            started=time.monotonic();stage='loading'
            while game.poll() is None and desktop.poll() is None and flight.poll() is None:
                if run_id is None:
                    try:
                        snapshot=request(50051,'sim.get_state')['payload']
                        if snapshot.get('scene_id')==args.scene and snapshot.get('devices') and snapshot.get('initial_drone_position_cm'):
                            run_id=snapshot.get('run_id')
                            if run_id:
                                stage='flight';status(stage,'UE 场景已加载，正在初始化飞控…')
                    except (OSError, ValueError, KeyError):pass
                elif stage!='ready':
                    try:
                        snapshot=request(50052,'sim.get_state')['payload']
                        if snapshot.get('run_id')==run_id and snapshot.get('flight_status')=='ready':
                            assets_ready=True
                            if args.scene=='city_large':
                                native=request(50051,'sim.get_state')['payload']
                                assets_ready=native.get('runtime_hardware',{}).get('asset_compile_jobs')==0
                            if assets_ready:
                                stage='ready';status(stage,'UE 和飞控已就绪，正在自动连接…')
                            elif stage!='assets':
                                stage='assets';status(stage,'正在准备大城市材质缓存…首次运行可能较久。')
                    except (OSError,ValueError,KeyError):pass
                limit=900 if args.scene=='city_large' else 300
                if stage!='ready' and time.monotonic()-started>limit:
                    stage='failed';status(stage,f'UE 启动超过 {limit} 秒，请检查 logs 中的 UE / 飞控日志。')
                    break
                time.sleep(.3)
            if stage not in ('ready','failed'):
                stage='failed';status(stage,'UE 或飞控提前退出，请检查 logs 中的启动日志。')
            if stage=='failed':
                # Keep the failure and logs visible until the user closes the
                # desktop. The supervisor still owns and later cleans children.
                while desktop.poll() is None:time.sleep(.3)
            report('A session window/critical worker exited; stopping owned resources.')
        finally:
            # Stop receivers/writers first. Closing the GUI also closes training
            # that it owns. Standalone/manual training processes are outside job.
            owned = job.pids()
            close_windows(owned - ({game.pid} if game else set()))
            if desktop and desktop.poll() is None:
                try:desktop.wait(timeout=16)
                except subprocess.TimeoutExpired:report('Desktop close timed out.')
            if game and game.poll() is None:
                if run_id:land_owned_fleet(run_id, report)
                close_windows({game.pid})
                try:game.wait(timeout=12)
                except subprocess.TimeoutExpired:report('UE close timed out.')
            job.close()
            report('Owned job closed; session cleanup complete.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('editor','project','data'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--scene',default='city')
    run(parser.parse_args())


if __name__=='__main__':main()
