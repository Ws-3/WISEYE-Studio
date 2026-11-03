"""Optically aligned image blending on the IR grid, independent of GT boxes."""
import math
from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QImage, QPainter, QTransform, QPolygonF, QPainterPath
from .client import validate_pair, validate_packet


def decode(packet):
    image = QImage.fromData(validate_packet(packet), 'JPEG')
    if image.isNull() or (image.width(), image.height()) != (packet['width'], packet['height']):
        raise ValueError('Decoded image dimensions do not match GT')
    return image.convertToFormat(QImage.Format.Format_RGB32)


def registration(pair, mode='strict'):
    samples = validate_pair(pair)
    visible, ir = samples['visible'], samples['infrared']
    for field, tolerance in [('camera_position_cm', .01), ('camera_rotation_pitch_yaw_roll_deg', .01)]:
        a, b = visible[field], ir[field]
        if not isinstance(a,list) or not isinstance(b,list) or len(a) != 3 or len(b) != 3 or not all(type(v) in (int,float) and math.isfinite(v) for v in a+b):
            raise ValueError('Invalid camera pose')
        difference = [abs((x-y+180)%360-180) if 'rotation' in field else abs(x-y) for x,y in zip(a,b)]
        if mode=='strict' and max(difference) > tolerance:
            raise ValueError('双相机有基线或视轴差；需深度/标定配准，原始双路仍可采集')
    def intrinsics(packet):
        fov = packet['horizontal_fov_deg']
        if not math.isfinite(fov) or not 0 < fov < 180:
            raise ValueError('Invalid camera FOV')
        focal = packet['width']/(2*math.tan(math.radians(fov/2)))
        return focal, packet['width']/2, packet['height']/2
    fv, xv, yv = intrinsics(visible)
    fi, xi, yi = intrinsics(ir)
    scale = fi/fv
    return QRectF(xi-xv*scale, yi-yv*scale, visible['width']*scale, visible['height']*scale)


def _axes(rotation):
    pitch,yaw,roll=map(math.radians,rotation)
    sp,cp,sy,cy,sr,cr=math.sin(pitch),math.cos(pitch),math.sin(yaw),math.cos(yaw),math.sin(roll),math.cos(roll)
    # UE FRotationTranslationMatrix rows: optical forward, right, up.
    return ((cp*cy,cp*sy,sp),(sr*sp*cy-cr*sy,sr*sp*sy+cr*cy,-sr*cp),
            (-(cr*sp*cy+sr*sy),cy*sr-cr*sp*sy,cr*cp))


def fusion_transform(pair, mode='raw'):
    if mode not in ('raw','rotation','strict'):raise ValueError('Unknown fusion mode')
    rect=registration(pair,mode)
    visible,ir=pair['samples']['visible'],pair['samples']['infrared']
    if mode!='rotation':
        transform=QTransform();transform.translate(rect.x(),rect.y());transform.scale(rect.width()/visible['width'],rect.height()/visible['height'])
        return transform
    va,ia=_axes(visible['camera_rotation_pitch_yaw_roll_deg']),_axes(ir['camera_rotation_pitch_yaw_roll_deg'])
    fv=visible['width']/(2*math.tan(math.radians(visible['horizontal_fov_deg']/2)))
    fi=ir['width']/(2*math.tan(math.radians(ir['horizontal_fov_deg']/2)))
    source=QPolygonF([QPointF(0,0),QPointF(visible['width'],0),QPointF(visible['width'],visible['height']),QPointF(0,visible['height'])])
    target=QPolygonF()
    for point in source:
        ray=(1,(point.x()-visible['width']/2)/fv,-(point.y()-visible['height']/2)/fv)
        world=[sum(ray[j]*va[j][k] for j in range(3)) for k in range(3)]
        local=[sum(world[k]*ia[j][k] for k in range(3)) for j in range(3)]
        if local[0]<=1e-6:raise ValueError('视场相差过大，无法进行视轴叠加')
        target.append(QPointF(ir['width']/2+fi*local[1]/local[0],ir['height']/2-fi*local[2]/local[0]))
    transform=QTransform()
    if not QTransform.quadToQuad(source,target,transform):raise ValueError('视轴投影退化')
    return transform


def comparison(pair,mode='raw'):
    samples=validate_pair(pair);visible,ir=samples['visible'],samples['infrared']
    transform=fusion_transform(pair,mode)
    vis={o['target_id']:o for o in visible['objects']}
    differences=[]
    for obj in ir['objects']:
        if obj['target_id'] not in vis:continue
        a,b=vis[obj['target_id']]['bbox_xyxy'],obj['bbox_xyxy']
        mapped=transform.map(QPointF((a[0]+a[2])/2,(a[1]+a[3])/2))
        dx,dy=mapped.x()-(b[0]+b[2])/2,mapped.y()-(b[1]+b[3])/2
        differences.append(dict(target_id=obj['target_id'],dx_px=dx,dy_px=dy,distance_px=math.hypot(dx,dy)))
    baseline=math.sqrt(sum((a-b)**2 for a,b in zip(visible['camera_position_cm'],ir['camera_position_cm'])))
    return dict(capture_delta_ms=1000*(visible['simulation_time_s']-ir['simulation_time_s']),
                request_round_trip_ms=pair.get('request_round_trip_ms'),baseline_cm=baseline,gt_center_differences=differences)


def blend_pair(pair, infrared_weight=.5, mode='raw',images=None):
    if not math.isfinite(infrared_weight) or not 0 <= infrared_weight <= 1:
        raise ValueError('Fusion weight must be 0..1')
    samples = validate_pair(pair)
    transform = fusion_transform(pair,mode)
    visible, infrared = (images['visible'],images['infrared']) if images is not None else (decode(samples['visible']), decode(samples['infrared']))
    result = infrared.copy()
    painter = QPainter(result)
    try:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path=QPainterPath();path.addPolygon(transform.map(QPolygonF(QRectF(0,0,visible.width(),visible.height()))));path.closeSubpath()
        painter.setClipPath(path)
        painter.setTransform(transform);painter.drawImage(0,0,visible);painter.resetTransform()
        painter.setOpacity(infrared_weight)
        painter.drawImage(0, 0, infrared)
    finally:
        painter.end()
    return result
