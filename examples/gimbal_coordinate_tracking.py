"""Feed ordered JSONL positions to the coordinate-aim SDK; holds on EOF."""
import argparse
import json
from pathlib import Path
import sys
from core.georeference import GeoReference
from integrations.gimbal_client import GimbalClient,GimbalError


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',default='ptz-01');parser.add_argument('--sensor',choices=['visible','infrared'],default='visible')
    parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=50051)
    parser.add_argument('--reference',type=Path,help='Explicit simulation WGS84 reference JSON; omit for UE world cm')
    args=parser.parse_args();client=GimbalClient(args.device,args.host,args.port)
    reference=GeoReference.from_dict(json.loads(args.reference.read_text(encoding='utf-8-sig'))) if args.reference else None
    initial=client.state();last_sequence=-1
    if reference and reference.scene_id!=initial['scene_id']:raise GimbalError('Reference scene mismatch')
    if not initial.get('coordinate_pointing_supported'):raise GimbalError('Requires new UE coordinate-pointing support')
    try:
        for raw in iter(lambda:sys.stdin.readline(4097),''):
            if len(raw)>4096:raise ValueError('Position message too large')
            value=json.loads(raw);sequence=value.get('sequence')
            if type(sequence) is not int or sequence<=last_sequence:raise ValueError('sequence must strictly increase')
            if reference:
                reply=client.point_at_geodetic(reference,value['latitude_deg'],value['longitude_deg'],value['ellipsoid_height_m'],args.sensor,run_id=initial['run_id'])
            else:reply=client.point_at_world(value['position_cm'],args.sensor,scene_id=initial['scene_id'],run_id=initial['run_id'])
            last_sequence=sequence
            print(json.dumps(dict(sequence=sequence,yaw_deg=reply['yaw_deg'],pitch_deg=reply['pitch_deg'],pointing=reply['coordinate_pointing'])),flush=True)
    finally:
        # Do not issue a stop to a replacement simulator session.
        try:
            if client.state().get('run_id')==initial['run_id']:client.hold()
        except (OSError,GimbalError) as error:print('Stop unconfirmed: '+str(error),file=sys.stderr)


if __name__=='__main__':main()
