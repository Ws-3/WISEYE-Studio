"""Explicit adapters for generic sensor data; no claim of vendor RAW/UDP emulation."""
import math
import struct


def pointcloud2(packet):
    """ROS sensor_msgs/PointCloud2 constructor fields, with binary `data` bytes.

    Converts UE sensor-local (forward,right,up) to ROS (forward,left,up).
    The caller supplies ROS transport and the corresponding world transform.
    """
    if packet.get('lidar_downsampled') is not False:
        raise ValueError('Use sensor.lidar.get_scan; this packet is only a decimated preview')
    if packet.get('lidar_coordinate_frame')!='sensor_local_x_forward_y_right_z_up' or packet.get('lidar_units')!='meters':
        raise ValueError('Unsupported coordinate frame/units')
    t=packet.get('lidar_capture_time_s')
    if not isinstance(t,(int,float)) or not math.isfinite(t) or t<0:raise ValueError('Missing scan acquisition time')
    data=bytearray()
    for row in packet['lidar_points_m']:
        if len(row)!=3 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in row):raise ValueError('Invalid point')
        data.extend(struct.pack('<fff',row[0],-row[1],row[2]))
    ns=round(t*1_000_000_000);sec,nanosec=divmod(ns,1_000_000_000)
    frame=packet.get('lidar_sensor_id','lidar').replace('/','_').replace('-','_')+'_ros'
    return dict(header=dict(stamp=dict(sec=sec,nanosec=nanosec),frame_id=frame),height=1,width=len(data)//12,
        fields=[dict(name=n,offset=i*4,datatype=7,count=1) for i,n in enumerate(['x','y','z'])],
        is_bigendian=False,point_step=12,row_step=len(data),data=bytes(data),is_dense=True)


def metavision_events(packet):
    """Metavision-compatible EventCD NumPy layout, not EVT2/EVT3 or a RAW file."""
    import numpy as np
    if packet.get('columns')!='x,y,t_us,p':raise ValueError('Explicit x,y,t_us,p layout required')
    rows=packet.get('events',[]);last=-1
    dtype=np.dtype({'names':['x','y','p','t'],'formats':['<u2','<u2','<i2','<i8'],'offsets':[0,2,4,8],'itemsize':16})
    result=np.zeros(len(rows),dtype=dtype)
    for i,row in enumerate(rows):
        if len(row)!=4:raise ValueError('Invalid event')
        x,y,t,p=row
        if not all(isinstance(v,(int,float)) and math.isfinite(v) and int(v)==v for v in row):raise ValueError('Events require integral finite fields')
        if not (0<=x<packet['width'] and 0<=y<packet['height'] and t>=last and p in [-1,1]):raise ValueError('Invalid coordinate, polarity or time order')
        if not (x<=65535 and y<=65535 and 0<=t<2**63):raise ValueError('EventCD field overflow')
        last=t;result[i]=(x,y,1 if p==1 else 0,t)
    return result
