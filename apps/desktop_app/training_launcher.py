"""Open the independent training workbench without a console window."""
import os
from pathlib import Path
import subprocess
import sys
from core.runtime_paths import RESOURCE_ROOT, INSTALL_ROOT, IS_RELEASE


def activate_training_window():
    if sys.platform!='win32':return False
    import ctypes
    from ctypes import wintypes as W
    user=ctypes.windll.user32;found=[]
    user.ShowWindow.argtypes=[W.HWND,ctypes.c_int]
    user.SetForegroundWindow.argtypes=[W.HWND]
    @ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    def visit(hwnd,_):
        title=ctypes.create_unicode_buffer(512)
        user.GetWindowTextW(hwnd,title,512)
        if title.value.startswith('WISEYE Training ·'):
            found.append(hwnd);return False
        return True
    user.EnumWindows(visit,0)
    if not found:return False
    user.ShowWindow(found[0],9);user.SetForegroundWindow(found[0]);return True


def launch_training(window):
    if activate_training_window():
        window.log('已切换到训练工作台。');return
    previous=getattr(window,'_training_process',None)
    if previous is not None and previous.poll() is None:
        window.log('训练工作台正在启动，请稍候。');return
    try:
        if IS_RELEASE:
            executable=INSTALL_ROOT/'Training/WISEYE-Training.exe'
            if not executable.is_file():raise OSError('当前运行包尚未包含训练端，请使用含训练端的新运行包或源码入口。')
            command=[str(executable)]
        else:
            if not (RESOURCE_ROOT/'training_client/preview.py').is_file():raise OSError('缺少 training_client/preview.py。')
            candidates=[Path(sys.executable).with_name('pythonw.exe'),RESOURCE_ROOT/'builds/python-env/Scripts/pythonw.exe',RESOURCE_ROOT/'training_client/.venv/Scripts/pythonw.exe']
            executable=next((p for p in candidates if p.is_file()),None)
            if executable is None:raise OSError('找不到训练端 Python 环境，请先安装训练端依赖。')
            command=[str(executable),'-m','training_client.preview']
        command+=['--host',window.config.host,'--port','50100','--device',window.selected_gimbal]
        if window.client.ready:command.append('--connect')
        from core.process_job import ProcessJob
        old_job=getattr(window,'_training_job',None)
        if old_job:old_job.close()
        window._training_job=ProcessJob()
        window._training_process=window._training_job.spawn(command,cwd=str(RESOURCE_ROOT),
            env=dict(os.environ,PYTHONUTF8='1'),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        window.log('已启动独立训练工作台；数据服务默认端口50100，可在训练端修改。')
    except OSError as error:
        window.log('训练端启动失败：'+str(error))
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(window,'训练工作台',str(error))


def close_owned_training(window, timeout=14):
    """Graceful flush first; job handle kills only our descendants on timeout."""
    import time
    from core.process_job import close_windows
    job=getattr(window,'_training_job',None)
    if job is None:return
    try:
        close_windows(job.pids())
        deadline=time.monotonic()+timeout
        while job.pids() and time.monotonic()<deadline:time.sleep(.1)
    finally:
        job.close();window._training_job=None
