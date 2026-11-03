"""Frozen training UI shares the parent portable release and data directory."""
import os
import sys
from pathlib import Path

if getattr(sys,'frozen',False):
    os.environ['WISEYE_RELEASE_ROOT']=str(Path(sys.executable).resolve().parent.parent)

from training_client.preview import main

if __name__=='__main__':
    if '--smoke-ui' in sys.argv:
        destination=Path(sys.argv[sys.argv.index('--smoke-ui')+1])
        from argparse import Namespace
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer,QSettings
        from training_client.preview import Window,ensure_fonts
        from core.runtime_paths import DATA_ROOT,initialize_data
        initialize_data()
        app=QApplication([]);ensure_fonts()
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(DATA_ROOT/'QtSettings'))
        args=Namespace(host='127.0.0.1',port=50100,device='ptz-01',sensor='both',output=DATA_ROOT/'Training',count=0,connect=False)
        window=Window(args);window.show()
        def finish():
            window.grab().save(str(destination));window.close();app.quit()
        QTimer.singleShot(1800,finish);sys.exit(app.exec())
    else:main()
