import logging
import time
from multiprocessing import Pipe
import gtk
import traceback

import gst

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
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)

    args = parse_args()

    p = PipelineWindowProcess(args.window_xid)
    try:
        p.start()
        response = p(command='select_video_caps', ack=True)['response']
        logging.info('[response] %s' % response)
        device, caps_str = response['device'], response['caps_str']

        for i in range(2):
            response = p(command='create', device=device,
                    caps_str=caps_str, bitrate=150000,
                            output_path='test_output.avi', ack=True)
            logging.info('[response] %s' % response)

            response = p(command='start', ack=True)
            logging.info('[response] %s' % response)
            time.sleep(5)

            p(command='stop')
            response = p(command='create', device=None, ack=True,
                    caps_str='video/x-raw-yuv,width=640,height=480,fourcc=YUY2'\
                            ',framerate=30/1')
            logging.info('[response] %s' % response)
            p(command='start')
            logging.info('[response] %s' % response)

            time.sleep(3)
            p(command='stop')
        p(command='join')
    except (Exception, ), why:
        traceback.print_stack()
        traceback.print_exc()
        p.terminate()
    else:
        p.join()
