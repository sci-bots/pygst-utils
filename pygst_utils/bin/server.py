#!/usr/bin/env python
import logging
import sys
from subprocess import Popen, PIPE

from path import path
import pygst_utils
from pygst_utils.video_pipeline.window_service import WindowService


def base_path():
    return path(pygst_utils.__file__).parent.joinpath('bin')


def server_popen():
    if hasattr(sys, 'frozen'):
        server_process = Popen([base_path().joinpath('server.exe')], stdout=PIPE, stderr=PIPE)
    else:
        server_process = Popen([sys.executable, base_path().joinpath('server.py')], stdout=PIPE, stderr=PIPE)
    return server_process


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', loglevel=logging.DEBUG)

    service = WindowService()
    logging.info('Starting server')

    service.run()
