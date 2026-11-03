"""Native widget geometry checks; screenshots are offline layout evidence."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.workbench_v3 import show_properties
from core.config import AppConfig
from training_client.workbench import Window


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    app=QApplication([])
    stores=[QSettings('WISEYE',name) for name in ('Studio','Training')]
    saved=[{k:s.value(k) for k in s.allKeys()} for s in stores]
    w=MainWindow(AppConfig.load())
    t=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-01',output=Path('unused')))
    reports=[]
    try:
        scale=w.devicePixelRatioF()
        for physical in ((1920,1080),(1440,900)):
            size=(max(960,round(physical[0]/scale)-24),max(640,round(physical[1]/scale)-60))
            w.sensor_dock.hide();w.pages.setCurrentIndex(1);w.resize(*size);w.show();QTest.qWait(150)
            show_properties(w,'sensor','ptz-01/infrared');QTest.qWait(150)
            report={'scale':scale,'physical':physical,'requested':size,'simulation':[w.width(),w.height()],
                    'minimum_clamped':physical[0]/scale-24<960 or physical[1]/scale-60<640,
                    'note':'Clamped cases verify the minimum logical window, not fit on the named physical screen.'}
            assert w.width()<=size[0] and w.height()<=size[1],report
            assert w.sensor_dock.width()>=300 and w.gallery.width()>=200,report
            w.grab().save(str(args.output/f'simulation-{physical[0]}.png'))
            w.sensor_dock.hide();w.pages.setCurrentIndex(1);QTest.qWait(100)
            w.grab().save(str(args.output/f'workbench-{physical[0]}.png'))
            w.sensor_dock.hide();w.pages.setCurrentIndex(0);QTest.qWait(150)
            assert w.arrangement.scene_view.width()>=240
            w.grab().save(str(args.output/f'arrangement-{physical[0]}.png'))
            w.pages.setCurrentIndex(4);QTest.qWait(100)
            w.grab().save(str(args.output/f'devices-{physical[0]}.png'))
            for index,name in ((2,'interfaces'),(3,'settings')):
                w.pages.setCurrentIndex(index);QTest.qWait(100)
                w.grab().save(str(args.output/f'{name}-{physical[0]}.png'))
            t.resize(*size);t.show();QTest.qWait(150)
            report['training']=[t.width(),t.height()]
            assert t.width()<=size[0] and t.height()<=size[1],report
            assert t.save_action.isVisible() and t.tiles['infrared'].width()>=200,report
            t.grab().save(str(args.output/f'training-{physical[0]}.png'));reports.append(report)
        (args.output/'report.json').write_text(json.dumps(reports,indent=2),encoding='utf8')
        print(json.dumps(reports),flush=True)
    finally:
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
        t.close();app.processEvents()
        for store,values in zip(stores,saved):
            store.clear()
            for key,value in values.items():store.setValue(key,value)


if __name__=='__main__':main()
