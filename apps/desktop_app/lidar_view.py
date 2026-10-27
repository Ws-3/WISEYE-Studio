"""Single-scan metric point-cloud viewer; no invented or accumulated points."""
import math
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget, QComboBox


def clean_points(points):
    result = []
    for p in points:
        if isinstance(p, (list, tuple)) and len(p) == 3:
            try:
                v = tuple(float(x) for x in p)
            except (TypeError, ValueError, OverflowError):
                continue
            if all(math.isfinite(x) for x in v):
                result.append(v)
    return result


def project_point(point, mode, yaw=-35, elevation=25):
    forward, right, up = point
    if mode == 'front': return right, up
    if mode == 'top': return right, forward
    a, b = math.radians(yaw), math.radians(elevation)
    horizontal = right * math.cos(a) - forward * math.sin(a)
    depth = forward * math.cos(a) + right * math.sin(a)
    return horizontal, up * math.cos(b) - depth * math.sin(b)


class LidarView(QWidget):
    def __init__(self):
        super().__init__()
        self.points = []
        self.total_count = 0
        self.rays = 0
        self.unavailable_message = '等待点云'
        self.yaw, self.elevation, self.zoom = -35, 25, 1.
        self.drag = None
        self.setMinimumSize(430, 260)
        self.mode = QComboBox(self)
        for label, value in [('三维点云', '3d'), ('正视 · Y/Z', 'front'), ('俯视 · Y/X', 'top')]:
            self.mode.addItem(label, value)
        self.mode.move(12, 10)
        self.mode.currentIndexChanged.connect(self.reset_view)
        self.setToolTip('单帧真实回波 · 米制等比例；三维模式拖动旋转，滚轮缩放，双击复位。颜色表示传感器距离。')

    def reset_view(self):
        self.yaw, self.elevation, self.zoom = -35, 25, 1.
        self.update()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.mode.setVisible(self.height()>=140 and self.width()>=200)

    def set_points(self, points, total_count, rays=0):
        self.points = clean_points(points)
        self.total_count, self.rays = total_count, rays
        self.unavailable_message = None
        self.update()

    def show_unavailable(self,message):
        self.set_points([],0,0)
        self.unavailable_message=message
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag = event.position()

    def mouseMoveEvent(self, event):
        if self.drag is not None and self.mode.currentData() == '3d':
            delta = event.position() - self.drag
            self.yaw += delta.x() * .4
            self.elevation = max(-85, min(85, self.elevation + delta.y() * .4))
            self.drag = event.position()
            self.update()

    def mouseReleaseEvent(self, event): self.drag = None
    def mouseDoubleClickEvent(self, event): self.reset_view()
    def wheelEvent(self, event):
        self.zoom = max(.2, min(20., self.zoom * 1.15 ** (event.angleDelta().y()/120)))
        self.update()
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#111317'))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        compact = self.width() < 440 or self.height() < 260
        top=45 if self.mode.isVisible() else 8
        area = self.rect().adjusted(12 if compact else 30, top if compact else 66, -12 if compact else -30, -8 if compact else -62)
        painter.setPen(QPen(QColor('#424954'), 1))
        painter.drawRect(area)
        if not self.points:
            painter.setPen(QColor('#9db2c8'))
            text=self.unavailable_message or ('本帧无回波' if compact else '本帧无回波\n朝向天空或目标在扫描间隙时可能没有命中')
            painter.drawText(area, Qt.AlignmentFlag.AlignCenter, text)
            return
        mode = self.mode.currentData()
        projected = [project_point(p, mode, self.yaw, self.elevation) for p in self.points]
        xs, ys = zip(*projected)
        center = ((min(xs)+max(xs))/2, (min(ys)+max(ys))/2)
        # One metric scale for both axes; never stretch a thin scan into a full screen.
        scale = min(area.width()/max(.5, max(xs)-min(xs)), area.height()/max(.5, max(ys)-min(ys))) * .85 * self.zoom
        def screen(p):
            return QPointF(area.center().x()+(p[0]-center[0])*scale,
                           area.center().y()-(p[1]-center[1])*scale)
        ranges = [math.sqrt(sum(v*v for v in p)) for p in self.points]
        lo, hi = min(ranges), max(ranges)
        painter.save()
        painter.setClipRect(area)
        for p, distance in zip(projected, ranges):
            t = (distance-lo)/max(.001, hi-lo)
            color = QColor.fromHsvF((.52*(1-t)), .8, 1)
            pen = QPen(color, 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawPoint(screen(p))
        # Unit triad uses the same projection as the measured points.
        painter.restore()
        if compact:
            painter.setPen(QColor('#b4bcc8'))
            painter.drawText(area.adjusted(6,2,-6,-2),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop,f'{self.total_count} 回波')
            return
        origin = QPointF(area.left()+42, area.bottom()-40)
        for label, p, color in [('X 前',(1,0,0),'#f87171'),('Y 右',(0,1,0),'#4ade80'),('Z 上',(0,0,1),'#60a5fa')]:
            x,y=project_point(p,mode,self.yaw,self.elevation)
            end=origin+QPointF(x*27,-y*27)
            painter.setPen(QPen(QColor(color),1.5));painter.drawLine(origin,end)
            painter.drawText(end+QPointF(3,-3),label)
        painter.setPen(QColor('#b3c6dc'))
        rays = f' / {self.rays} 射线' if self.rays else ''
        painter.drawText(190,32,f'{self.total_count} 回波{rays}')
        painter.drawText(12,self.height()-35,f'单帧 · 等比例 · 距离 {lo:.2f}–{hi:.2f} m · 近青 → 远红')
        painter.drawText(12,self.height()-14,'拖动旋转 / 滚轮缩放 / 双击复位' if mode=='3d' else '局部坐标投影；细线/平面也可能是真实回波')
        unit=10**math.floor(math.log10(max(.001,80/scale)))
        x,y=area.right()-95,area.bottom()-14
        painter.drawLine(QPointF(x,y),QPointF(x+unit*scale,y))
        painter.drawText(QPointF(x,y-5),f'{unit:g} m')
