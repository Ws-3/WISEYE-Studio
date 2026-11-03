"""Bounded display zoom: source pixels and camera FOV are never modified."""
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QImage,QPixmap,QPainter,QColor
from PySide6.QtWidgets import QLabel


class ImageView(QLabel):
    def __init__(self):
        super().__init__('等待实时画面')
        self.setAlignment(Qt.AlignmentFlag.AlignCenter);self.setMinimumSize(100,60)
        self.setStyleSheet('background:#111317;color:#b4bcc8;border:0;')
        self.native_pixels=False;self.source=QPixmap();self.zoom_factor=1.
        self.zoom_center=QPointF(.5,.5);self._zoom_drag=None
        self.setToolTip('滚轮缩放 · 放大后按住左键平移 · 双击复位；只改变显示，不改变相机视场或保存的数据。')

    def show_image(self,image):
        pix=QPixmap.fromImage(image) if isinstance(image,QImage) else image
        if self.source.size()!=pix.size():self.reset_zoom()
        self.source=pix;self._fit()

    def _scale(self):
        if self.source.isNull():return 1.
        return (1. if self.native_pixels else min(self.width()/self.source.width(),self.height()/self.source.height()))*self.zoom_factor

    def _clamp_center(self):
        if self.source.isNull():return
        scale=self._scale()
        for axis,length,pixels in [('x',self.width(),self.source.width()),('y',self.height(),self.source.height())]:
            half=min(.5,length/max(.001,2*pixels*scale))
            value=max(half,min(1-half,getattr(self.zoom_center,axis)()))
            getattr(self.zoom_center,'set'+axis.upper())(value)

    def _fit(self):self._clamp_center();self.update()
    def reset_zoom(self):self.zoom_factor=1.;self.zoom_center=QPointF(.5,.5);self.update()
    def resizeEvent(self,event):super().resizeEvent(event);self._fit()

    def wheelEvent(self,event):
        if self.source.isNull():event.ignore();return
        old=self._scale();cursor=event.position()-QPointF(self.width()/2,self.height()/2)
        point=QPointF(self.zoom_center.x()+cursor.x()/(old*self.source.width()),self.zoom_center.y()+cursor.y()/(old*self.source.height()))
        self.zoom_factor=max(1.,min(16.,self.zoom_factor*1.2**(event.angleDelta().y()/120)))
        new=self._scale()
        self.zoom_center=QPointF(point.x()-cursor.x()/(new*self.source.width()),point.y()-cursor.y()/(new*self.source.height()))
        self._fit();event.accept()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.zoom_factor>1:self._zoom_drag=event.position();event.accept();return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self._zoom_drag is not None:
            delta=event.position()-self._zoom_drag;self._zoom_drag=event.position();scale=self._scale()
            self.zoom_center-=QPointF(delta.x()/(scale*self.source.width()),delta.y()/(scale*self.source.height()))
            self._fit();event.accept();return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):self._zoom_drag=None;super().mouseReleaseEvent(event)
    def mouseDoubleClickEvent(self,event):self.reset_zoom();event.accept()

    def paintEvent(self,event):
        if self.source.isNull():super().paintEvent(event);return
        painter=QPainter(self);painter.fillRect(self.rect(),QColor('#111317'))
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scale=self._scale();width,height=self.source.width()*scale,self.source.height()*scale
        dest=QRectF(self.width()/2-self.zoom_center.x()*width,self.height()/2-self.zoom_center.y()*height,width,height)
        # Qt clips painting to the widget; never allocate a 16x enlarged frame.
        painter.drawPixmap(dest,self.source,QRectF(self.source.rect()))
        if self.zoom_factor>1.001:
            painter.fillRect(QRectF(8,8,66,24),QColor(10,14,20,210));painter.setPen(QColor('#dbe7f5'))
            painter.drawText(QRectF(8,8,66,24),Qt.AlignmentFlag.AlignCenter,f'{self.zoom_factor:.1f}×')
