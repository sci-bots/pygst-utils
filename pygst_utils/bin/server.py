#!/usr/bin/env python
import logging
import sys
from subprocess import Popen

from path import path

# --- IMPORTS FOR DISCOVERY BY PYINSTALLER ---
import platform
import blinker
import decimal
import pygtk
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
    while p != path('/').abspath()\
            and not p.joinpath('pygst_utils').isdir():
        attempted_paths.append(p)
        p = p.parent
    if not p:
        raise RuntimeError, 'cannot find server.exe (attempted paths: %s)'\
                % attempted_paths
    return p.joinpath('pygst_utils')


package_root = base_path().parent.parent
sys.path.insert(0, package_root)

import pygst_utils
from pygst_utils.video_pipeline.window_service import WindowService


def server_popen(port):
    if hasattr(sys, 'frozen'):
        import pygst_utils_windows_server
        exe_path = path(pygst_utils_windows_server.__path__[0]).joinpath(
                'server.exe')
        print '[server_popen] exe_path=%s' % exe_path
        server_process = Popen([exe_path, str(port)], cwd=exe_path.parent)
    else:
        script_path = base_path().joinpath('bin', 'server.py')
        print '[server_popen] script_path=%s' % script_path
        server_process = Popen([sys.executable, script_path, str(port)])
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
