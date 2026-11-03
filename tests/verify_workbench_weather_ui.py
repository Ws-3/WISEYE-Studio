import unittest
from types import SimpleNamespace
from unittest.mock import patch,Mock
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication,QPushButton
from PySide6.QtCore import QPoint,QPointF,Qt
from PySide6.QtGui import QImage,QColor,QWheelEvent
from PySide6.QtTest import QTest
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.image_view import ImageView
from apps.desktop_app.sensor_workspace import DragLabel
from core.config import AppConfig


class WorkbenchWeatherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_two_actions_stop_owned_session_and_disconnect_without_stopping(self):
        w=MainWindow(AppConfig.load())
        try:
            self.assertEqual(w.quick_connect.text(),'启动仿真')
            manager=SimpleNamespace(running=True,closing=False,stop=Mock())
            w.runtime_manager=manager;w.client.ready=True;w.air_client.ready=True;w.sync_session_buttons()
            self.assertEqual(w.quick_connect.text(),'关闭仿真');self.assertTrue(w.quick_connect.isEnabled())
            with patch.object(w,'disconnect_ue') as disconnect:w.badge.click();disconnect.assert_called_once()
            manager.stop.assert_not_called()
            w.quick_connect.click();manager.stop.assert_called_once();self.assertTrue(manager.closing)
            self.assertEqual(w.quick_connect.text(),'正在关闭…');self.assertFalse(w.quick_connect.isEnabled())
            with patch.object(w,'connect_ue') as connect:w.runtime_ready();connect.assert_not_called()
            manager.running=False;w.client.ready=False;w.air_client.ready=False;w.sync_session_buttons()
        finally:w.close()

    def test_view_click_does_not_open_parameters_and_popout_has_direct_button(self):
        w=MainWindow(AppConfig.load());w.show();w.pages.setCurrentIndex(1);self.app.processEvents()
        try:
            self.assertFalse(w.gallery.isAncestorOf(w.ownership))
            self.assertTrue(w.inspectors.parentWidget().isAncestorOf(w.input_mode))
            key=next(k for k in w.gallery.views if k.endswith('/visible'))
            view=w.gallery.views[key];QTest.mouseClick(view,Qt.MouseButton.LeftButton)
            for title in w.gallery.cards[key].findChildren(DragLabel):QTest.mouseClick(title,Qt.MouseButton.LeftButton)
            self.assertFalse(w.sensor_dock.isVisible())
            buttons=[b for b in w.gallery.cards[key].findChildren(QPushButton) if b.accessibleName()=='弹出画面']
            self.assertEqual(len(buttons),1);buttons[0].click();self.assertIn(key,w.gallery.popouts)
            w.gallery.popouts[key][0].close()
        finally:w.close()

    def test_zoom_is_local_persistent_and_bounded(self):
        view=ImageView();view.resize(800,500);view.show()
        image=QImage(640,512,QImage.Format.Format_RGB32);image.fill(QColor('#7489a0'));view.show_image(image)
        def wheel(delta):
            event=QWheelEvent(QPointF(400,250),QPointF(400,250),QPoint(0,0),QPoint(0,delta),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
            QApplication.sendEvent(view,event)
        try:
            wheel(120);self.assertGreater(view.zoom_factor,1);zoom=view.zoom_factor
            view.show_image(image);self.assertEqual(view.zoom_factor,zoom)
            self.assertEqual(view.source.size(),image.size())
            for _ in range(50):wheel(120)
            self.assertEqual(view.zoom_factor,16);view.grab()
            QTest.mouseDClick(view,Qt.MouseButton.LeftButton);self.assertEqual(view.zoom_factor,1)
            for _ in range(5):wheel(-120)
            self.assertEqual(view.zoom_factor,1)
        finally:view.close()


if __name__=='__main__':unittest.main()
