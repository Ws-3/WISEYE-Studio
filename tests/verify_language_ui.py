"""Qt state stays intact across live language changes and dynamic updates."""
import tempfile
import unittest
from pathlib import Path
import apps.desktop_app.main  # System ICU before Qt on Windows.
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton
from apps.desktop_app.language import manager


class LanguageUITests(unittest.TestCase):
    def test_live_switch_keeps_item_identity_and_user_input(self):
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            QSettings.setDefaultFormat(QSettings.Format.IniFormat)
            QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,folder)
            control = manager()
            control.settings = QSettings('WISEYE','Language')
            control.select('zh_CN')
            root = QWidget(); layout = QVBoxLayout(root)
            label = QLabel('未连接'); button = QPushButton('启动仿真')
            model = QComboBox(); model.addItem('固定翼（80 cm）','fixedwing');model.addItem('Avata','avata')
            entry = QLineEdit('我的云台');entry.setPlaceholderText('名称')
            for widget in (label,button,model,entry):layout.addWidget(widget)
            control.register(root)
            events=[];model.currentIndexChanged.connect(events.append)
            control.select('en_US')
            self.assertEqual(button.text(),'Start simulation')
            self.assertEqual(model.currentData(),'fixedwing')
            self.assertEqual(entry.text(),'我的云台')
            self.assertEqual(entry.placeholderText(),'Name')
            self.assertEqual(events,[])
            label.setText('已连接')
            self.assertEqual(label.text(),'Connected')
            control.select('zh_CN')
            self.assertEqual(label.text(),'已连接')
            self.assertEqual(model.itemText(0),'固定翼（80 cm）')
            self.assertEqual(control.settings.value('language'),'zh_CN')
            root.close();control.roots.discard(root);control.cache.clear()


if __name__ == '__main__':unittest.main()
