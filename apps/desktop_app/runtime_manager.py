"""Own only the subprocesses started by this desktop session."""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from PySide6.QtCore import QObject, Signal
from core.runtime_paths import INSTALL_ROOT, RESOURCE_ROOT, DATA_ROOT


class ProcessJob:
    """Windows closes all owned descendants if the desktop crashes or exits."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', w.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                        ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class Counters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', Counters), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.api.CreateJobObjectW.restype = w.HANDLE
        self.api.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.api.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, process):
        import ctypes
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            process.terminate()
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def request(port, command, payload=None):
    with socket.create_connection(('127.0.0.1', port), timeout=1) as peer:
        peer.settimeout(2)
        request_id = f'launcher-{time.time_ns()}'
        peer.sendall(json.dumps({'version': 1, 'request_id': request_id,
                                'command': command, 'payload': payload or {}}).encode() + b'\n')
        data = b''
        while b'\n' not in data:
            part = peer.recv(65536)
            if not part:
                raise ConnectionError('Connection closed during startup')
            data += part
            if len(data) > 4 * 1024**2:
                raise ValueError('Startup response exceeded limit')
        reply = json.loads(data.split(b'\n', 1)[0])
        if not isinstance(reply, dict) or reply.get('request_id') != request_id or reply.get('version') != 1:
            raise ValueError('Invalid startup response identity')
        return reply


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
        with (DATA_ROOT / 'logs' / f'{name}.log').open('ab') as output:
            process = subprocess.Popen(arguments, cwd=DATA_ROOT / 'logs', env=environment,
                                       stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.processes.append(process)
        self.job.assign(process)
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
        try:
            self.job = ProcessJob()
            from core.config import AppConfig
            config = AppConfig.load()
            if config.host not in ('127.0.0.1', 'localhost') or (config.port, config.airsim_port) != (50051, 50052):
                raise RuntimeError('内置仿真使用本机 50051 / 50052；远程连接请使用连接 UE。请在接口设置中调整。')
            release = json.loads((INSTALL_ROOT / 'release.json').read_text(encoding='utf-8'))
            if scene['id'] not in release['scenes']:
                raise RuntimeError('当前版本未安装所选场景。')
            for port in (50051, 50052):
                with socket.socket() as probe:
                    if probe.connect_ex(('127.0.0.1', port)) == 0:
                        raise RuntimeError(f'端口 {port} 已被占用，请先退出原仿真。')
            executable = INSTALL_ROOT / release['simulation_executable']
            if not executable.is_file():
                raise RuntimeError('缺少 UE 独立程序，请修复安装。')
            self.message.emit('正在加载场景…首次运行需要准备着色器缓存。')
            self._spawn([str(executable), scene['map'] + '?game=/Script/test.WiseEyeGameMode?wiseeye_scene=' + scene['id'],
                         '-windowed', '-ResX=1280', '-ResY=720', '-nosplash',
                         f'-WiseEyeScene={scene["id"]}', f'-simlogdir={DATA_ROOT / "logs"}',
                         f'-WiseEyeDataDir={DATA_ROOT}', f'-UserDir={DATA_ROOT / "UE"}',
                         f'-abslog={DATA_ROOT / "logs/ue-game.log"}'], 'ue-launch')
            snapshot = self._wait(50051, 'sim.get_state', lambda p: p.get('scene_id') == scene['id'] and p.get('run_id')
                       and p.get('devices') and p.get('initial_drone_position_cm'))
            self.message.emit('场景已加载，正在初始化飞控…')
            self._spawn([str(INSTALL_ROOT / 'WISEYE.exe'), '--worker', 'flight', '--scene', scene['id'], '--loops', '0'], 'flight-launch')
            self._wait(50052, 'sim.get_state', lambda p: p.get('flight_status') == 'ready' and p.get('run_id') == snapshot['run_id'])
            tools = INSTALL_ROOT / 'Tools'
            with socket.socket() as probe:
                video_available = probe.connect_ex(('127.0.0.1', config.rtsp_port)) != 0
            local_video = config.rtsp_host in ('127.0.0.1', 'localhost')
            if not local_video or (video_available and (tools / 'mediamtx.exe').is_file()):
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
        self.cancel.set()
