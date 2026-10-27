"""Spring-return proportional yaw/pitch stick; no network work in painting."""
import math
from PySide6.QtCore import Qt,QPointF,Signal,QEvent
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import QWidget,QSizePolicy

class GimbalJoystick(QWidget):
    moved=Signal(float,float)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.vector=(0.,0.);self.dragging=False
        self.setMinimumSize(150,150);self.setMaximumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip('按住拖动：左右偏航，上下俯仰；离中心越远越快；松手或失焦回中停止。')

    def geometry_values(self):return QPointF(self.width()/2,self.height()/2),max(1,min(self.width(),self.height())/2-23)

    def set_position(self,point):
        center,radius=self.geometry_values();delta=point-center
        x,y=delta.x()/radius,-delta.y()/radius
        length=math.hypot(x,y)
        if length>1:x,y=x/length,y/length
        if length<.08:x=y=0.
        self.vector=(x,y);self.moved.emit(x,y);self.update()

    def reset(self):
        self.dragging=False;self.vector=(0.,0.);self.moved.emit(0.,0.);self.update()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.isEnabled():
            self.setFocus();self.dragging=True;self.set_position(event.position());event.accept()

    def mouseMoveEvent(self,event):
        if self.dragging:self.set_position(event.position());event.accept()

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.reset();event.accept()

    def focusOutEvent(self,event):self.reset();super().focusOutEvent(event)
    def hideEvent(self,event):self.reset();super().hideEvent(event)
    def changeEvent(self,event):
        if event.type()==QEvent.Type.EnabledChange and not self.isEnabled():self.reset()
        super().changeEvent(event)

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center,radius=self.geometry_values();color=QColor('#78b1ff') if self.isEnabled() else QColor('#949daa')
        painter.setPen(QPen(QColor('#424954'),1));painter.setBrush(QColor('#17191d'));painter.drawEllipse(center,radius,radius)
        painter.drawLine(center+QPointF(-radius,0),center+QPointF(radius,0));painter.drawLine(center+QPointF(0,-radius),center+QPointF(0,radius))
        knob=center+QPointF(self.vector[0]*radius,-self.vector[1]*radius)
        painter.setPen(QPen(color,2));painter.drawLine(center,knob);painter.setBrush(QColor('#245dc0'));painter.drawEllipse(knob,16,16)
        painter.setPen(color);painter.drawText(4,16,'俯仰 ↑');painter.drawText(4,self.height()-5,'偏航 ← →     松手停止')
