#!/usr/bin/env python
import logging
import sys
from subprocess import Popen

from path import path

# --- IMPORTS FOR DISCOVERY BY PYINSTALLER ---
import platform
import blinker
import decimal
import gtk
import gst
import cgi
import jsonrpclib
import jsonrpclib.SimpleJSONRPCServer
import numpy
# ############################################


def base_path():
    p = path(__file__).parent.abspath()
    attempted_paths = []
    while p and not p.joinpath('pygst_utils_windows_server').isdir():
        attempted_paths.append(p)
        p = p.parent
    if not p:
        raise RuntimeError, 'cannot find server.exe (attempted paths: %s)'\
                % attempted_paths
    return p.joinpath('pygst_utils_windows_server')


package_root = base_path().parent.parent
sys.path.insert(0, package_root)

import pygst_utils
from pygst_utils.video_pipeline.window_service import WindowService


def server_popen(port):
    if hasattr(sys, 'frozen'):
        exe_path = base_path().joinpath('server.exe')
        server_process = Popen([exe_path, str(port)]) #, stdout=PIPE, stderr=PIPE)
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
