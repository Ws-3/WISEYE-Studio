"""Windows process ownership; never enumerate/kill by executable name."""
import subprocess

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


    def spawn(self, arguments, **kwargs):
        # Assign before executable code runs (venv launchers otherwise race
        # creation of their real Python child).
        import ctypes
        kwargs['creationflags'] = kwargs.get('creationflags', 0) | 0x4
        process = subprocess.Popen(arguments, **kwargs)
        try:
            self.assign(process)
            resume = ctypes.WinDLL('ntdll').NtResumeProcess
            resume.argtypes = [ctypes.c_void_p]
            resume.restype = ctypes.c_long
            if resume(int(process._handle)) < 0:
                raise OSError('Cannot resume owned process')
        except BaseException:
            process.kill(); process.wait(timeout=5)
            raise
        return process

    def pids(self):
        import ctypes
        from ctypes import wintypes as W
        if not self.handle:return set()
        query=self.api.QueryInformationJobObject
        query.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD,ctypes.c_void_p]
        size=1024
        while size <= 1024*1024:
            data=ctypes.create_string_buffer(size)
            if query(self.handle,3,data,size,None):
                count=ctypes.c_uint32.from_buffer(data,4).value
                return set((ctypes.c_size_t*count).from_buffer(data,8))
            if ctypes.get_last_error()!=234:raise ctypes.WinError(ctypes.get_last_error())
            size*=2
        raise OSError('Owned job process list exceeded bound')


def close_windows(pids):
    import ctypes
    from ctypes import wintypes as W
    user=ctypes.WinDLL('user32')
    user.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
    user.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM]
    @ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    def visit(hwnd,_):
        pid=W.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value in pids:user.PostMessageW(hwnd,0x10,0,0)
        return True
    user.EnumWindows(visit,0)
