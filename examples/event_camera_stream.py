"""python -m examples.event_camera_stream --output events.jsonl --seconds 10

Enable the event sensor in the desktop first. Each JSONL row is a bounded packet;
inspect skipped_events/truncated_events: this is not a lossless hardware recorder.
"""
import argparse
import json
import time
from pathlib import Path
from core.local_rpc import request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',default='ptz-01');parser.add_argument('--port',type=int,default=50051)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seconds',type=float,default=10)
    args=parser.parse_args()
    if args.seconds<=0:parser.error('--seconds must be positive')
    cursor=0;run=None;total=skipped=0;deadline=time.monotonic()+args.seconds
    # Refuse accidental overwrites of previous recordings.
    with args.output.open('x',encoding='utf-8') as output:
        while time.monotonic()<deadline:
            payload=dict(device_id=args.device,after_sequence=cursor,max_events=20000,latest=False)
            if run:payload['run_id']=run
            reply=request(args.port,'sensor.event.get_packet',payload,timeout=2)
            if reply.get('status')!='ok':raise RuntimeError(reply.get('error'))
            packet=reply['payload'];run=packet['run_id'];cursor=packet['next_cursor']
            total+=len(packet['events']);skipped+=packet['skipped_events']
            output.write(json.dumps(packet,separators=(',',':'))+'\n')
            if cursor>=packet['latest_sequence']:time.sleep(.02)
    print(f'{total} events, {skipped} skipped; {args.output.resolve()}')


if __name__=='__main__':main()
