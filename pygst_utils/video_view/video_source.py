from datetime import datetime
import json
import logging
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


def pipeline_command_from_json(json_source):
    from ..video_source.caps import VIDEO_SOURCE_PLUGIN, DEVICE_KEY

    # Set `(red|green|blue)_mask` to ensure RGB channel order for both YUY2
    # and I420 video sources.  If this is not done, red and blue channels
    # might be swapped.
    #
    # See [here][1] for default mask values.
    #
    # [1]: https://www.freedesktop.org/software/gstreamer-sdk/data/docs/latest/gst-plugins-bad-plugins-0.10/gst-plugins-bad-plugins-videoparse.html#GstVideoParse--blue-mask
    caps_str = ('video/x-raw-rgb,width={width:d},height={height:d},'
                'red_mask=(int)255,green_mask=(int)65280,'
                'blue_mask=(int)16711680,'
                'framerate={framerate_num:d}/{framerate_denom:d}'
                .format(**json_source))
    device_str = '{} {}="{}"'.format(VIDEO_SOURCE_PLUGIN, DEVICE_KEY,
                                     json_source['device_name'])
    logging.info('[View] video config device string: %s', device_str)
    logging.info('[View] video config caps string: %s', caps_str)

    video_command = ''.join([device_str, ' ! ffmpegcolorspace ! ', caps_str,
                             ' ! appsink name=app-video emit-signals=true'])
    return video_command


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
    parser.add_argument('-p', '--port', default=None)

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
                                          'using `gst-launch` syntax.')
    parser_launch.add_argument('pipeline', nargs='?',
                               default=default_pipeline_command,
                               help='Default: %(default)s')

    parser_json = subparsers.add_parser('fromjson', help='Configure pipeline'
                                        'from json object including: '
                                        'device_name, width, height, '
                                        'framerate_num, framerate_denom')
    parser_json.add_argument('json', help='JSON object including: '
                             'device_name, width, height, framerate_num, '
                             'framerate_denom')

    args = parser.parse_args()
    args.log_level = getattr(logging, args.log_level.upper())
    return args


if __name__ == "__main__":
    args = parse_args()
    if args.command == 'launch':
        pipeline_command = args.pipeline
    elif args.command == 'fromjson':
        pipeline_command = pipeline_command_from_json(json.loads(args.json))
    pipeline, status = main(pipeline_command, args.transport, args.host,
                            args.port)

    if not args.interactive:
        ioloop.install()
        logger.info('Starting run loop.')
        ioloop.IOLoop.instance().start()
