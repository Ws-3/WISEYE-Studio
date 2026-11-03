"""Small antialiased vector icons; no font glyph or external asset dependency."""
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor

PATHS = {
    'popout': [(3,8,3,21),(3,21,16,21),(16,21,16,14),(3,8,10,8),(14,3,21,3),(21,3,21,10),(21,3,10,14)],
    'expand': [(3,9,3,3),(3,3,9,3),(15,3,21,3),(21,3,21,9),(21,15,21,21),(21,21,15,21),(3,15,3,21),(3,21,9,21)],
    'scene': [(3,20,3,8),(3,8,10,8),(10,8,10,20),(10,20,10,3),(10,3,20,3),(20,3,20,20),(2,20,22,20)],
    'screen': [(3,4,21,4),(21,4,21,17),(21,17,3,17),(3,17,3,4),(12,17,12,21),(7,21,17,21)],
    'data': [(3,7,20,7),(20,7,16,3),(20,7,16,11),(21,17,4,17),(4,17,8,13),(4,17,8,21)],
    'devices': [(3,3,10,3),(10,3,10,10),(10,10,3,10),(3,10,3,3),(14,3,21,3),(21,3,21,10),(21,10,14,10),(14,10,14,3),(3,14,10,14),(10,14,10,21),(10,21,3,21),(3,21,3,14),(14,14,21,14),(21,14,21,21),(21,21,14,21),(14,21,14,14)],
    'settings': [(5,5,19,5),(5,12,19,12),(5,19,19,19),(9,2,9,8),(16,9,16,15),(11,16,11,22)],
    'up': [(12,20,12,4),(12,4,6,10),(12,4,18,10)],
    'down': [(12,4,12,20),(12,20,6,14),(12,20,18,14)],
    'pause': [(8,5,8,19),(16,5,16,19)],
    'route': [(4,18,9,6),(9,6,16,16),(16,16,21,5)],
    'connect': [(8,3,8,8),(16,3,16,8),(5,8,19,8),(5,8,8,15),(19,8,16,15),(8,15,16,15),(12,15,12,22)],
}

def icon(name, color='#9dbce5'):
    pix=QPixmap(48,48);pix.fill(Qt.GlobalColor.transparent);pix.setDevicePixelRatio(2)
    painter=QPainter(pix);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color),1.6,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
    for x1,y1,x2,y2 in PATHS[name]:painter.drawLine(x1,y1,x2,y2)
    painter.end();return QIcon(pix)

def decorate(w):
    for index,name in enumerate(('scene','screen','data','settings')):w.pages.setTabIcon(index,icon(name))
    w.pages.setIconSize(QSize(18,18))
    for attr,name in [('takeoff_button','up'),('land_button','down'),('hover_button','pause'),('quick_connect','connect')]:
        getattr(w,attr).setIcon(icon(name))
