"""Right-button input ownership for the independent scene observer."""
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QCheckBox,QComboBox,QDialog,QScrollArea,QSizePolicy
from apps.desktop_app.lidar_view import LidarView

class ObserverInput:
    """Attached to an image widget; right mouse owns observer movement only."""
    def init_observer(self,window):
        self.window=window;self.keys=set();self.drag=None;self.look=[0.,0.]
        self.setProperty('observerInput',True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.timer=QTimer(self);self.timer.setInterval(100);self.timer.timeout.connect(self.send)
        self.setToolTip('先点击“自由观察”；按住右键拖动转向，WASD 移动，Q/E 下降/上升；松开右键停止。')

    def send(self):
        w=self.window
        if not w.client.ready or w.state.get('input_mode')!='observer' or w.state.get('observer_mode')!='free':return
        if not w.simulation_healthy:self.keys.clear();self.look=[0.,0.]
        self.look=[max(-90.,min(90.,v)) for v in self.look]
        w.client.request('observer.set_input',dict(forward=float((Qt.Key.Key_W in self.keys)-(Qt.Key.Key_S in self.keys)),right=float((Qt.Key.Key_D in self.keys)-(Qt.Key.Key_A in self.keys)),up=float((Qt.Key.Key_E in self.keys)-(Qt.Key.Key_Q in self.keys)),yaw_deg=self.look[0],pitch_deg=self.look[1]))
        self.look=[0.,0.]

    def stop(self):
        self.keys.clear();self.drag=None;self.look=[0.,0.];self.timer.stop();self.send()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.RightButton:
            self.setFocus();self.drag=event.position();self.timer.start();event.accept();return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self.drag is not None:
            delta=event.position()-self.drag;self.drag=event.position();self.look[0]+=delta.x()*.18;self.look[1]-=delta.y()*.18;event.accept();return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.RightButton:self.stop();event.accept();return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self,event):
        if self.drag is not None and event.key() in (Qt.Key.Key_W,Qt.Key.Key_S,Qt.Key.Key_A,Qt.Key.Key_D,Qt.Key.Key_Q,Qt.Key.Key_E):
            self.keys.add(event.key());self.send();event.accept();return
        super().keyPressEvent(event)

    def keyReleaseEvent(self,event):
        if event.key() in self.keys:
            if not event.isAutoRepeat():self.keys.discard(event.key());self.send()
            event.accept();return
        super().keyReleaseEvent(event)

    def focusOutEvent(self,event):self.stop();super().focusOutEvent(event)
    def hideEvent(self,event):self.stop();super().hideEvent(event)
