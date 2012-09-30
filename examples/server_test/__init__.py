try:
    import cPickle as pickle
except ImportError:
    import pickle
import time
import sys

from path import path
package_path = path(__file__).abspath().parent.parent.parent
sys.path.insert(0, package_path)
import yaml
import numpy as np
from pygst_utils.elements.draw_queue import get_example_draw_queue
from jsonrpclib import Server


def stop(s, xid):
    s.stop_pipeline(xid)
    s.terminate_process(xid)


def parse_args():
    """Parses arguments, returns (options, args)."""
    from argparse import ArgumentParser

    parser = ArgumentParser(description="""Test gstreamer server for window xid""")
    parser.add_argument('window_xid', type=int, nargs=1)
    parser.add_argument('server_url', type=str, nargs='?',
            default='http://localhost:59000')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    args = parse_args()

    s = Server(args.server_url)
    xid = args.window_xid[0]
    s.create_process(xid, False)
    s.create_pipeline(xid,
            ('/dev/v4l/by-id/usb-Vimicro_Vimicro_USB_Camera__Altair_-video-index0',
            'video/x-raw-yuv,width=320,height=240,fourcc=YUY2,framerate=30/1'),
            'test.avi', 150000, pickle.dumps(get_example_draw_queue(500,
            #None, None, pickle.dumps(get_example_draw_queue(500,
            600)), True, True)
    s.scale(xid, 500, 600)
    s.start_pipeline(xid)

    transform_matrix = np.array(yaml.load('''\
    - [2.329641819000244, 0.15357783436775208, -264.1610107421875]
    - [0.25795140862464905, 2.25241756439209, -309.17999267578125]
    - [0.0013796498533338308, 0.0004429532855283469, 1.0]'''))
    transform_str = ','.join([str(v) for v in transform_matrix.flatten()])

    s.set_warp_transform(xid, transform_str)

    try:
        for i in range(3):
            # ---------------------------------------------------------
            s.request_frame(xid)
            frame = None
            while frame is None:
                time.sleep(0.1)
                frame = pickle.loads(str(s.get_frame(xid)))
            # =========================================================
        time.sleep(8)
    finally:
        stop(s, xid)
