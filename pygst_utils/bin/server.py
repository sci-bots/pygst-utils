#!/usr/bin/env python
import logging
import sys
from subprocess import Popen

from path import path


def base_path():
    return path(__file__).parent.parent.joinpath('bin')

package_root = base_path().parent.parent
sys.path.insert(0, package_root)

import pygst_utils
from pygst_utils.video_pipeline.window_service import WindowService


def server_popen(port):
    if hasattr(sys, 'frozen'):
        server_process = Popen([base_path().joinpath('server.exe'), str(port)]) #, stdout=PIPE, stderr=PIPE)
    else:
        server_process = Popen([sys.executable,
                base_path().joinpath('server.py'), str(port)])
        # stdout=PIPE, stderr=PIPE, env={'GST_DEBUG_DUMP_DOT_DIR': '/tmp'})
    return server_process


def parse_args():
    """Parses arguments, returns (options, args)."""
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Run GStreamer WindowService server')
    parser.add_argument('port', default=8080, type=int, nargs='?')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s',
            loglevel=logging.CRITICAL)

    args = parse_args()
    service = WindowService(port=args.port)
    logging.info('Starting server')

    service.run()
