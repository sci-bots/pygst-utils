import logging
import time
from multiprocessing import Pipe

from gst_video_source_caps_query.video_mode_dialog import select_video_caps

from test_pipeline_process import PipelineWindowProcess


def parse_args():
    """Parses arguments, returns ``(options, args)``."""
    from argparse import ArgumentParser

    parser = ArgumentParser(description="""\
Start a pipeline window process.""",
                            epilog="""\
(C) 2011 Christian Fobel.""",
                           )
    parser.add_argument('-x', '--window_xid',
                    dest='window_xid', type=int,
                    required=True,
                    help='GTK DrawingArea window xid')
    args = parser.parse_args()
    
    return args


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)

    args = parse_args()

    device, caps_str = select_video_caps()

    master_pipe, worker_pipe = Pipe()
    p = PipelineWindowProcess(args.window_xid, worker_pipe)
    try:
        p.start()

        master_pipe.send({'command': 'create',
                'device': None,
                'caps_str': 'video/x-raw-yuv,width=640,height=480,fourcc=YUY2,framerate=30/1',
                'bitrate': 150000, 'output_path': 'test_output.avi'})

        time.sleep(1)
        master_pipe.send({'command': 'start'})

        time.sleep(3)
        master_pipe.send({'command': 'stop'})
        time.sleep(1)
        master_pipe.send({'command': 'create',
                'device': device, 'caps_str': caps_str,
                'bitrate': 150000, 'output_path': 'test_output.avi'})
        master_pipe.send({'command': 'start'})
        time.sleep(3)
        master_pipe.send({'command': 'stop'})
        master_pipe.send({'command': 'join'})
    except:
        p.terminate()
    else:
        p.join()
