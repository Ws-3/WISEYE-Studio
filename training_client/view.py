from .localization import tr
"""Live image zoom/pan and independent enlarged views."""
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy


class Canvas(QWidget):
    imageChanged=Signal(object)
    zoomChanged=Signal(float)
    activated=Signal()

    def __init__(self):
        super().__init__();self._image=QImage();self.message='等待数据';self.zoom=1.;self.offset=QPointF();self.drag=None
        self.setMinimumSize(200,130)
        self.setToolTip('滚轮缩放 · 拖动平移 · 双击放大窗口')

    @property
    def image(self):return self._image

    @image.setter
    def image(self,value):
        self._image=value;self.update();self.imageChanged.emit(value);self.zoomChanged.emit(self.scale()*self.zoom)

    def scale(self):
        return min(self.width()/self.image.width(),self.height()/self.image.height()) if not self.image.isNull() else 1

    def set_zoom(self,value):
        self.zoom=max(.1,min(32.,value));self._clamp();self.zoomChanged.emit(self.scale()*self.zoom);self.update()

    def fit(self):
        self.offset=QPointF();self.set_zoom(1)

    def native(self):
        self.offset=QPointF();self.set_zoom(1/self.scale())

    def _clamp(self):
        if self.image.isNull():self.offset=QPointF();return
        sx,sy=self.image.width()*self.scale()*self.zoom,self.image.height()*self.scale()*self.zoom
        x,y=max(0,(sx-self.width())/2),max(0,(sy-self.height())/2)
        self.offset=QPointF(max(-x,min(x,self.offset.x())),max(-y,min(y,self.offset.y())))

    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),QColor('#0c1016'))
        if self.image.isNull():
            painter.setPen(QColor('#9ba9bd'));painter.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,tr(self.message))
        else:
            self._clamp();s=self.scale()*self.zoom;w,h=self.image.width()*s,self.image.height()*s
            painter.drawImage(QRectF((self.width()-w)/2+self.offset.x(),(self.height()-h)/2+self.offset.y(),w,h),self.image)
        painter.end()

    def wheelEvent(self,event):
        if self.image.isNull():return
        old=self.zoom;new=max(.1,min(32.,old*1.25**(event.angleDelta().y()/120)))
        relative=event.position()-QPointF(self.width()/2,self.height()/2)
        self.offset=relative-(relative-self.offset)*(new/old);self.set_zoom(new);event.accept()

    def mousePressEvent(self,event):
        if event.button() in (Qt.MouseButton.LeftButton,Qt.MouseButton.MiddleButton):
            self.drag=event.position();self.setCursor(Qt.CursorShape.ClosedHandCursor);event.accept()

    def mouseMoveEvent(self,event):
        if self.drag is not None:
            self.offset+=event.position()-self.drag;self.drag=event.position();self._clamp();self.update()

    def mouseReleaseEvent(self,event):self.drag=None;self.unsetCursor()
    def mouseDoubleClickEvent(self,event):self.activated.emit()
    def resizeEvent(self,event):
        super().resizeEvent(event);self.zoomChanged.emit(self.scale()*self.zoom)


def controls(canvas):
    row=QHBoxLayout();row.setSpacing(4)
    for text,action in [('−',lambda:canvas.set_zoom(canvas.zoom/1.25)),('+',lambda:canvas.set_zoom(canvas.zoom*1.25)),('适应',canvas.fit),('1:1',canvas.native)]:
        button=QPushButton(text);button.setObjectName('imageTool');button.setSizePolicy(QSizePolicy.Policy.Maximum,QSizePolicy.Policy.Fixed);button.clicked.connect(action);row.addWidget(button)
    value=QLabel('100%');canvas.zoomChanged.connect(lambda factor:value.setText(f'{factor*100:.0f}%'));row.addWidget(value)
    return row


class EnlargedView(QDialog):
    def __init__(self,title,source,parent):
        super().__init__(parent);self.setWindowTitle(title+' · 放大预览');self.resize(1280,850)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        layout=QVBoxLayout(self);self.canvas=Canvas();layout.addLayout(controls(self.canvas));layout.addWidget(self.canvas,1)
        self.canvas.image=source.image;self.canvas.message=source.message
        source.imageChanged.connect(self.update_image)

    def update_image(self,image):
        self.canvas.image=image
        if image.isNull():self.canvas.message='等待有效新数据'
