"""Native Qt V4 regressions; never writes scene/device configuration."""
import argparse
from pathlib import Path
import unittest
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QImage, QColor
from PySide6.QtTest import QTest
from core.config import AppConfig
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.workbench_v3 import show_properties
from training_client.workbench import Window
from tests.verify_training_fusion import fixture


class V4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_large_city_switch_allows_cold_load_without_changing_small_timeout(self):
        import time
        w=MainWindow(AppConfig.load())
        try:
            for target,timeout in [('city_large',900),('city',90)]:
                before=time.monotonic()
                w.completed('sim.load_scene',dict(pending_scene=target,run_id='old'))
                self.assertEqual(w.switch_timeout_seconds,timeout)
                self.assertGreaterEqual(w.switch_deadline,before+timeout)
                w.reconnect_timer.stop()
            w.switch_target=None
        finally:w.close()

    def test_large_city_does_not_replace_small_city_default(self):
        import json
        city=json.loads((Path(__file__).resolve().parents[1]/'ue5/WISEYE/Config/WISEYE/Scenes/city.json').read_text(encoding='utf-8-sig'))
        city['installed']=True
        large=dict(city,id='city_large',name='大城市试验',map='/Game/WISEYE/Scenes/city_large/BigCity')
        w=MainWindow(AppConfig.load())
        try:
            w.scenes.clear()
            with patch('apps.desktop_app.main_window.SceneStore') as store:
                store.return_value.list.return_value=([large,city],[])
                w.refresh_scenes()
                self.assertEqual(w.scenes.currentData()['id'],'city')
                w.scenes.setCurrentIndex(0)
                w.refresh_scenes()
                self.assertEqual(w.scenes.currentData()['id'],'city_large')
            self.assertFalse(getattr(getattr(w,'runtime_manager',None),'running',False))
        finally:w.close()

    def test_navigation_preserves_indices_and_control_identity(self):
        from apps.desktop_app.ui.theme import STYLE
        from training_client._theme import STYLE as standalone
        self.assertEqual(STYLE,standalone)
        w=MainWindow(AppConfig.load())
        try:
            identity=w.selected_drone,w.selected_gimbal
            self.assertEqual(w.pages.count(),5)
            self.assertEqual(w.settings_navigation.count(),5)
            w.nav_buttons[0].click();self.assertEqual(w.pages.currentIndex(),0)
            w.nav_buttons[1].click();self.assertEqual(w.pages.currentIndex(),1)
            self.assertEqual((w.selected_drone,w.selected_gimbal),identity)
            show_properties(w,'sensor',w.selected_gimbal+'/infrared')
            self.assertFalse(w.sensor_dock.isHidden());self.assertEqual(w.sensor_settings.currentIndex(),1)
            self.assertTrue(w.context_group.button(1).isChecked())
            self.assertEqual((w.selected_drone,w.selected_gimbal),identity)
        finally:w.close()

    def test_arrangement_reuses_observer_frame_without_a_second_client(self):
        w=MainWindow(AppConfig.load())
        try:
            w.pages.setCurrentIndex(0)
            self.assertEqual(w.gallery.displayed(),{'scene/observer'})
            image=QImage(960,540,QImage.Format.Format_RGB32);image.fill(QColor('gray'))
            w.gallery.frame('scene/observer',image)
            self.assertFalse(w.arrangement.scene_view.source.isNull())
            self.assertIn(w.arrangement.scene_view,w.gallery.targets('scene/observer'))
            self.assertEqual(len(w.gallery.clients),0)
            w.gallery.unavailable('scene/observer','过期')
            self.assertTrue(w.arrangement.scene_view.source.isNull())
        finally:w.close()

    def test_selected_placement_fields_match_each_device_and_remain_editable(self):
        w=MainWindow(AppConfig.load());page=w.arrangement
        try:
            for i in range(page.tools.device.count()):
                page.v4_device_list.setCurrentRow(i)
                key=page.tools.device.currentData()[1]
                self.assertTrue(all(not x.isHidden() for x in page.v4_field_groups[key]))
                self.assertIn(key,page.coordinates)
        finally:w.close()

    def test_training_pair_and_overlay_survive_relayout(self):
        w=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-01',output=Path('unused')))
        try:
            self.assertFalse(w.save_action.isEnabled())
            w.show_frame(fixture());worker=w.worker;identity=w.latest['pair_id']
            self.assertTrue(all(not tile.canvas.image.isNull() for tile in w.tiles.values()))
            w.show_gt.setChecked(False)
            self.assertIs(w.worker,worker);self.assertEqual(w.latest['pair_id'],identity)
            self.assertEqual(w.tiles['infrared'].canvas.image,w.decoded['infrared'])
            self.assertTrue(w.tiles['fusion'].tools_widget.isHidden())
            w.tiles['fusion'].enlarge();self.app.processEvents()
            self.assertFalse(w.tiles['fusion'].popup.canvas.image.isNull())
            w.show_error('断连');self.assertTrue(w.tiles['fusion'].popup.canvas.image.isNull())
        finally:w.close();self.app.processEvents()

    def test_device_reload_and_exit_do_not_silently_discard_drafts(self):
        w=MainWindow(AppConfig.load());w.show();w.pages.setCurrentIndex(4);self.app.processEvents()
        try:
            page=w.device_page;editor=page.editor
            self.assertFalse(page.has_draft())
            editor.table.item(0,3).setText('unsaved test name')
            self.assertTrue(page.has_draft())
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel):
                page.load();self.assertIs(page.editor,editor)
                w.close();self.assertTrue(w.isVisible())
        finally:
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()

    def test_device_details_edit_original_draft_and_keep_precise_position(self):
        w=MainWindow(AppConfig.load());w.show();w.pages.setCurrentIndex(4);self.app.processEvents()
        try:
            catalog=w.device_page.catalog;editor=w.device_page.editor
            before=editor.collect()['devices'][0]['position_cm'][:]
            catalog.name.selectAll();QTest.keyClicks(catalog.name,'Roof test unit')
            self.assertEqual(editor.collect()['devices'][0]['name'],'Roof test unit')
            self.assertEqual(editor.collect()['devices'][0]['position_cm'],before)
            catalog.actions['新增无人机'].click()
            self.assertEqual(catalog.table.rowCount(),3)
            self.assertEqual(catalog.selected()['id'],'uav-02')
            catalog.actions['删除选中实例'].click()
            self.assertEqual(catalog.table.rowCount(),2)
            self.assertEqual([d['id'] for d in editor.collect()['devices']],['uav-01','ptz-01'])
        finally:
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()

    def test_desktop_opens_without_launching_unreal_until_user_clicks(self):
        with patch.dict('os.environ',{'WISEYE_SESSION_STATUS':''}),patch('apps.desktop_app.runtime_manager.RuntimeManager') as factory:
            factory.return_value.running=False
            w=MainWindow(AppConfig.load());w.show();QTest.qWait(200)
            try:
                factory.assert_not_called();self.assertFalse(w.client.ready)
                self.assertEqual(w.quick_connect.text(),'启动仿真')
                w.quick_connect.click();factory.return_value.launch.assert_called_once()
            finally:w.close()

    def test_safety_actions_are_pinned_and_diagnostics_closes_with_main(self):
        w=MainWindow(AppConfig.load());w.show();self.app.processEvents()
        try:
            self.assertIs(w.takeoff_button.parentWidget(),w.drone_safety)
            self.assertFalse(w.drone_safety.isHidden())
            show_properties(w,'sensor',w.selected_gimbal+'/infrared')
            self.assertTrue(w.drone_safety.isHidden())
            self.assertIn(w.selected_gimbal,w.ownership.text())
            w.machine_summary.open();self.assertTrue(w.machine_summary.dialog.isVisible())
            from apps.desktop_app.workbench_polish import AdvancedControl
            section=w.findChildren(AdvancedControl)[0];section.open()
            with patch.object(w,'stop_manual_input') as stop:
                section.dialog.close();stop.assert_called_once()
        finally:w.close();self.app.processEvents()
        self.assertFalse(w.machine_summary.dialog.isVisible())


if __name__=='__main__':unittest.main()
