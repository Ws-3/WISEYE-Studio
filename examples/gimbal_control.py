"""Run from repository root: python -m examples.gimbal_control --device ptz-02."""
import argparse
import time
from integrations.gimbal_client import GimbalClient


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',default='ptz-01')
    args=parser.parse_args()
    gimbal=GimbalClient(args.device)
    print(gimbal.capabilities())
    gimbal.take_control()
    gimbal.hold()
    try:
        for _ in range(10):
            gimbal.set_velocity(yaw_deg_s=10)
            time.sleep(.1)
    finally:
        gimbal.stop()
    print(gimbal.state()['yaw_deg'])


if __name__=='__main__':main()
