"""One executable, explicit roles; workers do not initialize Qt."""
import os
from pathlib import Path
import sys

if getattr(sys, 'frozen', False):
    os.environ['WISEYE_RELEASE_ROOT'] = str(Path(sys.executable).parent)

from core.runtime_paths import DATA_ROOT, initialize_data
initialize_data()

def record_crash(kind, error, trace):
    import traceback
    with (DATA_ROOT / 'logs' / 'crash.log').open('a', encoding='utf-8') as output:
        traceback.print_exception(kind, error, trace, file=output)

sys.excepthook = record_crash

if '--worker' in sys.argv:
    index = sys.argv.index('--worker')
    role = sys.argv[index + 1]
    del sys.argv[index:index + 2]
    # Windowed executables have no inherited Python stdout/stderr objects.
    log = (DATA_ROOT / 'logs' / f'{role}-worker.log').open('a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log
    if role == 'flight':
        from integrations.ProjectAirSim.run_wiseye_flight import main
    elif role == 'rtsp':
        from integrations.rtsp.rtsp_gateway import main
    else:
        raise SystemExit('Unknown worker role')
    main()
elif '--diagnose' in sys.argv:
    import json
    import projectairsim, pynng
    from apps.desktop_app import main as desktop
    from PySide6.QtCore import qVersion
    from core.scenes import SceneStore
    result = {'python': sys.version, 'qt': qVersion(), 'data_root': str(DATA_ROOT),
              'scenes': SceneStore(DATA_ROOT).list(), 'airsim': projectairsim.__version__}
    destination = Path(sys.argv[sys.argv.index('--diagnose') + 1])
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
elif '--smoke-ui' in sys.argv:
    from apps.desktop_app import main as desktop
    from PySide6.QtCore import QTimer, QSettings
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    from core.config import AppConfig
    app = QApplication(sys.argv[:1])
    app.setFont(QFont('Microsoft YaHei UI', 10))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(DATA_ROOT / 'QtSettings'))
    window = desktop.MainWindow(AppConfig.load())
    window.resize(1600, 950)
    window.show()
    destination = sys.argv[sys.argv.index('--smoke-ui') + 1]
    def capture():
        window.grab().save(destination)
        window.close()
        app.quit()
    QTimer.singleShot(1500, capture)
    raise SystemExit(app.exec())
else:
    from apps.desktop_app.main import main
    raise SystemExit(main())
