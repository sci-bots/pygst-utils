from argparse import ArgumentParser
from datetime import datetime
import json
import logging
import sys

from zmq.eventloop import ioloop
import zmq
from .. import pipeline_command_from_json

logger = logging.getLogger(__name__)


def main(pipeline_command, transport, host, port=None):
    import gst

    uri = '%s://%s:%s' % (transport, host, port)
    ctx = zmq.Context.instance()
    socket = zmq.Socket(ctx, zmq.PUSH)
    socket.connect(uri)
    pipeline = gst.parse_launch(unicode(pipeline_command).encode('utf-8'))
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

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='GStreamer to ZeroMQ socket.')
    log_levels = ('critical', 'error', 'warning', 'info', 'debug', 'notset')

    parser_pipeline = ArgumentParser(add_help=False)
    parser_pipeline.add_argument('-i', '--interactive', action='store_true',
                                 help='Do not start main loop.')
    parser_pipeline.add_argument('-l', '--log-level', type=str, choices=log_levels,
                        default='info')
    parser_pipeline.add_argument('transport')
    parser_pipeline.add_argument('host')
    parser_pipeline.add_argument('-p', '--port', default=None)

    default_pipeline = [
        'autovideosrc name=video-source', '!',
        'ffmpegcolorspace', '!',
        'video/x-raw-rgb,format=(fourcc)I420,framerate=30/1,'
        'width=640,height=480', '!',
        'videorate', '!',
        'appsink',
            'name=app-video',
            #'enable-last-buffer=true',
            'emit-signals=true',
            #'sync=true',
    ]
    default_pipeline_command = " ".join(default_pipeline)

    subparsers = parser.add_subparsers(help='sub-command help', dest='command')

    parser_launch = subparsers.add_parser('launch', help='Configure pipeline '
                                          'using `gst-launch` syntax.',
                                          parents=[parser_pipeline])
    parser_launch.add_argument('pipeline', nargs='?',
                               default=default_pipeline_command,
                               help='Default: %(default)s')

    parser_json = subparsers.add_parser('fromjson', help='Configure pipeline'
                                        'from json object including: '
                                        'device_name, width, height, '
                                        'framerate_num, framerate_denom',
                                        parents=[parser_pipeline])
    parser_json.add_argument('json', help='JSON object including: '
                             'device_name, width, height, framerate_num, '
                             'framerate_denom')

    subparsers.add_parser('device_list', help='List available device names')

    parser_device_caps = subparsers.add_parser('device_caps', help='List '
                                               'JSON serialized capabilities '
                                               'for device (compatible with '
                                               '`fromjson` subcommand).')
    parser_device_caps.add_argument('device_name')

    args = parser.parse_args()
    if hasattr(args, 'log_level'):
        args.log_level = getattr(logging, args.log_level.upper())
    return args


if __name__ == "__main__":
    args = parse_args()
    if args.command == 'launch':
        pipeline_command = args.pipeline
    elif args.command == 'fromjson':
        json_config = json.loads(args.json)
        pipeline_command = pipeline_command_from_json(json_config)
    elif args.command == 'device_list':
        from ..video_source import get_video_source_names
        print '\n'.join(get_video_source_names())
        raise SystemExit
    elif args.command == 'device_caps':
        from ..video_source import (expand_allowed_capabilities,
                                    get_allowed_capabilities)
        df_allowed_caps = get_allowed_capabilities(args.device_name)
        df_source_caps = expand_allowed_capabilities(df_allowed_caps)
        print '\n'.join([c.to_json() for i, c in df_source_caps.iterrows()])
        raise SystemExit
    pipeline, status = main(pipeline_command, args.transport, args.host,
                            args.port)

    if not args.interactive:
        ioloop.install()
        logger.info('Starting run loop.')
        ioloop.IOLoop.instance().start()
