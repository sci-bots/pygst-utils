from datetime import datetime
import logging
import os
import sys

from zmq.eventloop import ioloop
import zmq

logger = logging.getLogger(__name__)


def main(pipeline_command, transport, host, port=None):
    import pygst
    pygst.require("0.10")
    import gst

    uri = '%s://%s:%s' % (transport, host, port)
    ctx = zmq.Context.instance()
    socket = zmq.Socket(ctx, zmq.PUSH)
    socket.connect(uri)

    pipeline = gst.parse_launch(pipeline_command)
    app = pipeline.get_by_name('app-video')
    status = {'frame_count': 0}

    def on_new_buffer(appsink):
        import numpy as np

        buf = appsink.emit('pull-buffer')
        caps = buf.caps[0]
        width, height = caps['height'], caps['width']
        status['frame_count'] += 1
        status['buf'] = buf
        channels = buf.size / (width * height)
        socket.send_multipart([np.array([caps['height'], caps['width'],
                                         channels], dtype='uint32').tostring(),
                               buf.data])

    app.connect('new-buffer', on_new_buffer)

    pipeline.set_state(gst.STATE_PAUSED)
    pipeline.set_state(gst.STATE_PLAYING)
    return pipeline, status


def update_status(status):
    status['stop'] = datetime.now()
    status['duration_s'] = (status['stop'] -
                            status['start']).total_seconds()
    status['fps'] = status['frame_count'] / status['duration_s']


def parse_args(args=None):
    """Parses arguments, returns (options, args)."""
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='GStreamer to ZeroMQ socket.')
    log_levels = ('critical', 'error', 'warning', 'info', 'debug', 'notset')
    parser.add_argument('-i', '--interactive', action='store_true', help='Do '
                        'not start main loop.')
    parser.add_argument('-l', '--log-level', type=str, choices=log_levels,
                        default='info')
    parser.add_argument('transport')
    parser.add_argument('host')

    default_pipeline = [
        'autovideosrc', '!',
        'ffmpegcolorspace', '!',
        'video/x-raw-rgb,format=RGB,framerate=30/1,width=640,height=480', '!',
        #'video/x-raw-rgb,framerate=30/1,width=320,height=240', '!',
        'videorate', '!',
        'appsink',
            'name=app-video',
            #'enable-last-buffer=true',
            'emit-signals=true',
            #'sync=true',
    ]
    default_pipeline_command = " ".join(default_pipeline)
    parser.add_argument('pipeline', nargs='?',
                        default=default_pipeline_command,
                        help='Default: %(default)s')
    parser.add_argument('-p', '--port', default=None)

    args = parser.parse_args()
    args.log_level = getattr(logging, args.log_level.upper())
    return args


if __name__ == "__main__":
    args = parse_args()
    pipeline, status = main(args.pipeline, args.transport, args.host,
                            args.port)

    if not args.interactive:
        ioloop.install()
        logger.info('Starting run loop.')
        ioloop.IOLoop.instance().start()
