import os
import subprocess
import sys
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows Job objects')
class JobTests(unittest.TestCase):
    def test_job_cleanup_only_terminates_owned_process(self):
        import apps.desktop_app.main  # preload Windows ICU before Qt
        from apps.desktop_app.runtime_manager import ProcessJob
        owned = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], creationflags=subprocess.CREATE_NO_WINDOW)
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], creationflags=subprocess.CREATE_NO_WINDOW)
        job = ProcessJob()
        try:
            job.assign(owned)
            job.close()
            owned.wait(timeout=5)
            self.assertIsNone(unrelated.poll())
        finally:
            job.close()
            for process in (owned, unrelated):
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
