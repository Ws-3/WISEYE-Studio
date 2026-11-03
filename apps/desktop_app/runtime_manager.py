"""Own only the subprocesses started by this desktop session."""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import sys
from PySide6.QtCore import QObject, Signal
from core.runtime_paths import INSTALL_ROOT, RESOURCE_ROOT, DATA_ROOT, IS_RELEASE


from core.process_job import ProcessJob


from core.local_rpc import request


class RuntimeManager(QObject):
    message = Signal(str)
    ready = Signal()
    stopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processes = []
        self.cancel = threading.Event()
        self.running = False
        self.closing = False
        self.guard = threading.Lock()
        self.job = None

    def launch(self, scene):
        with self.guard:
            if self.running:
                self.message.emit('仿真已启动或正在加载，请等待。')
                return
            self.running = True
            self.closing = False
            self.cancel.clear()
        threading.Thread(target=self._run, args=(scene,), daemon=True).start()

    def _spawn(self, arguments, name):
        environment = dict(os.environ, WISEYE_DATA_DIR=str(DATA_ROOT),
                           WISEYE_RESOURCES_DIR=str(RESOURCE_ROOT), PYTHONUTF8='1')
        (DATA_ROOT / 'logs').mkdir(parents=True, exist_ok=True)
        with (DATA_ROOT / 'logs' / f'{name}.log').open('ab') as output:
            process = self.job.spawn(arguments, cwd=(DATA_ROOT / 'logs' if IS_RELEASE else RESOURCE_ROOT), env=environment,
                                       stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.processes.append(process)
        return process

    def _wait(self, port, command, predicate, timeout=300):
        deadline = time.monotonic() + timeout
        while not self.cancel.is_set() and time.monotonic() < deadline:
            if any(p.poll() is not None for p in self.processes):
                raise RuntimeError('后台进程提前退出，请查看用户目录 logs。')
            try:
                reply = request(port, command)
                if reply.get('status') == 'ok' and predicate(reply.get('payload', {})):
                    return reply['payload']
            except (OSError, ValueError):
                pass
            self.cancel.wait(.5)
        raise RuntimeError('仿真启动已取消或加载超时，请查看 logs。')

    def _run(self, scene):
        snapshot = None
        try:
            self.job = ProcessJob()
            from core.config import AppConfig
            config = AppConfig.load()
            if config.host not in ('127.0.0.1', 'localhost') or (config.port, config.airsim_port) != (50051, 50052):
                raise RuntimeError('内置仿真使用本机 50051 / 50052；远程连接请使用连接 UE。请在接口设置中调整。')
            if IS_RELEASE:
                release = json.loads((INSTALL_ROOT / 'release.json').read_text(encoding='utf-8'))
                if scene['id'] not in release['scenes']:
                    raise RuntimeError('当前版本未安装所选场景。')
                executable = INSTALL_ROOT / release['simulation_executable']
                prefix = [str(executable)]
                flight_command = [str(INSTALL_ROOT / 'WISEYE.exe'), '--worker', 'flight']
            else:
                project = Path(os.environ.get('WISEYE_PREVIEW_PROJECT', str(RESOURCE_ROOT/'ue5/WISEYE/test.uproject')))
                executable = Path(os.environ.get('WISEYE_UE_EDITOR', str(RESOURCE_ROOT/'Tools/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')))
                if not project.is_file():raise RuntimeError('找不到源码预览构建工程；请使用根目录启动入口或设置WISEYE_PREVIEW_PROJECT。')
                prefix = [str(executable), str(project)]
                flight_command = [sys.executable, '-m', 'integrations.ProjectAirSim.run_wiseye_flight']
            for port in (50051, 50052):
                with socket.socket() as probe:
                    if probe.connect_ex(('127.0.0.1', port)) == 0:
                        raise RuntimeError(f'端口 {port} 已被占用，请先退出原仿真。')
            if not executable.is_file():
                raise RuntimeError('缺少 UE 独立程序，请修复安装。')
            self.message.emit('正在加载场景…首次运行需要准备着色器缓存。')
            self._spawn(prefix + [scene['map'] + '?game=/Script/test.WiseEyeGameMode?wiseeye_scene=' + scene['id'],
                         '-game', '-windowed', '-ResX=1280', '-ResY=720', '-nosplash',
                         f'-WiseEyeScene={scene["id"]}', f'-simlogdir={DATA_ROOT / "logs"}',
                         f'-WiseEyeDataDir={DATA_ROOT}', f'-UserDir={DATA_ROOT / "UE"}',
                         f'-abslog={DATA_ROOT / "logs/ue-game.log"}'], 'ue-launch')
            snapshot = self._wait(50051, 'sim.get_state', lambda p: p.get('scene_id') == scene['id'] and p.get('run_id')
                       and p.get('devices') and p.get('initial_drone_position_cm'),
                       timeout=900 if scene['id']=='city_large' else 300)
            self.message.emit('场景已加载，正在初始化飞控…')
            self._spawn(flight_command + ['--scene', scene['id'], '--loops', '0'], 'flight-launch')
            self._wait(50052, 'sim.get_state', lambda p: p.get('flight_status') == 'ready' and p.get('run_id') == snapshot['run_id'])
            if not IS_RELEASE and scene['id']=='city_large':
                self.message.emit('大城市已加载，正在准备材质缓存…首次运行可能较久。')
                self._wait(50051,'sim.get_state',lambda p:p.get('run_id')==snapshot['run_id'] and
                           p.get('runtime_hardware',{}).get('asset_compile_jobs')==0,timeout=900)
            tools = INSTALL_ROOT / 'Tools'
            with socket.socket() as probe:
                video_available = probe.connect_ex(('127.0.0.1', config.rtsp_port)) != 0
            local_video = config.rtsp_host in ('127.0.0.1', 'localhost')
            if IS_RELEASE and (not local_video or (video_available and (tools / 'mediamtx.exe').is_file())):
                if local_video:
                    video_config = config.write_mediamtx(DATA_ROOT / 'logs/mediamtx-runtime.yml')
                    self._spawn([str(tools / 'mediamtx.exe'), str(video_config)], 'mediamtx')
                self._spawn([str(INSTALL_ROOT / 'WISEYE.exe'), '--worker', 'rtsp', '--ffmpeg', str(tools / 'ffmpeg.exe')], 'rtsp-launch')
            elif not video_available:
                self.message.emit(f'{config.rtsp_port} 已被其他视频服务占用，本次未启动外部 RTSP；桌面预览仍可使用。')
            self.message.emit('场景和飞控已就绪。')
            self.ready.emit()
            reported = set()
            while not self.cancel.wait(1):
                if any(p.poll() is not None for p in self.processes[:2]):
                    raise RuntimeError('仿真进程已退出。')
                for process in self.processes[2:]:
                    if process.poll() is not None and process.pid not in reported:
                        reported.add(process.pid)
                        self.message.emit('外部 RTSP 服务退出，请查看视频日志；仿真与桌面预览继续运行。')
        except Exception as error:
            self.message.emit(str(error))
        finally:
            if snapshot and self.processes and self.processes[0].poll() is None:
                from apps.desktop_app.session_shutdown import land_owned_fleet
                # Map travel replaces run_id; close the current owned world,
                # rather than trying to land the launch-time session.
                try:
                    current=request(50051,'sim.get_state')
                    if current.get('status')=='ok' and current['payload'].get('run_id'):snapshot=current['payload']
                except (OSError,ValueError):pass
                land_owned_fleet(snapshot['run_id'], self.message.emit)
            # Ask the owned game window to exit before terminating other workers.
            if self.processes and self.processes[0].poll() is None:
                import ctypes
                from ctypes import wintypes
                game = self.processes[0]
                user = ctypes.WinDLL('user32')
                user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
                user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
                callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                def visit(window, _):
                    pid = wintypes.DWORD()
                    user.GetWindowThreadProcessId(window, ctypes.byref(pid))
                    if pid.value == game.pid:
                        user.PostMessageW(window, 0x0010, 0, 0)
                    return True
                user.EnumWindows(callback_type(visit), 0)
                try:
                    game.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    pass
            for process in reversed(self.processes):
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
            self.processes.clear()
            if self.job:
                self.job.close()
                self.job = None
            self.running = False
            self.stopped.emit()

    def stop(self):
        self.closing=True
        self.cancel.set()
