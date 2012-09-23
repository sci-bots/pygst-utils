#!/usr/bin/env python
import logging
import sys
from subprocess import Popen, PIPE
import os
import signal
import time
try:
    import cPickle as pickle
except ImportError:
    import pickle

from path import path
import pygst_utils
from pygst_utils.video_pipeline.window_service import WindowService
from jsonrpclib import Server


def base_path():
    return path(pygst_utils.__file__).parent.joinpath('bin')


def server_popen(port):
    if hasattr(sys, 'frozen'):
        server_process = Popen([base_path().joinpath('server.exe'), str(port)], stdout=PIPE, stderr=PIPE)
    else:
        server_process = Popen([sys.executable, base_path().joinpath('server.py'), str(port)], stdout=PIPE, stderr=PIPE)
    return server_process


override_methods = set()


def override(f):
    global override_methods
    override_methods.add(f.__name__)
    return f


class ConnectionError(Exception): pass


class WindowServiceProxy(object):
    def __init__(self, port=8080):
        global override_methods

        self._override_methods = override_methods
        self._initialized = False
        while not self._initialized:
            server_process = server_popen(port)
            time.sleep(0.25)
            if server_process.poll() and server_process.returncode != 0:
                raise ConnectionError, 'Error starting server on port {}'\
                        .format(port)
            self._server_process = server_process
            self._initialized = True
        self._server = Server('http://localhost:{}'.format(port))
        self._methods = set(self._server.system.listMethods())
        self._server.create_process(0)
        self._pids = [self._server.get_pid(),
                self._server.get_process_pid(0)]

    def __getattr__(self, attr):
        if attr in self._methods and attr not in self._override_methods:
            return getattr(self._server, attr)
        else:
            return object.__getattribute__(self, attr)

    @property
    def pids(self):
        return tuple(self._pids)

    @override
    def get_video_mode_map(self, window_xid=None):
        if window_xid is None:
            window_xid = 0
        result = self._server.get_video_mode_map(window_xid)
        return pickle.loads(str(result))

    @override
    def get_video_source_configs(self, window_xid=None):
        if window_xid is None:
            window_xid = 0
        result = self._server.get_video_source_configs(window_xid)
        time.sleep(0.2)
        return pickle.loads(str(result))

    @override
    def select_video_mode(self, window_xid=None):
        if window_xid is None:
            window_xid = 0
        result = self._server.select_video_mode(window_xid)
        time.sleep(0.2)
        return pickle.loads(str(result))

    @override
    def select_video_caps(self, window_xid=None):
        if window_xid is None:
            window_xid = 0
        result = self._server.select_video_caps(window_xid)
        time.sleep(0.2)
        return result

    @override
    def create_process(self, window_xid, force_aspect_ratio=True):
        result = self._server.create_process(window_xid, force_aspect_ratio)
        pid = self._server.get_process_pid(window_xid)
        self._pids.append(pid)
        return result

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self._initialized:
            for pid in self._pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except:
                    continue
            self._initialized = False


def parse_args():
    """Parses arguments, returns (options, args)."""
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Run GStreamer WindowService server')
    parser.add_argument('port', default=8080, type=int, nargs='?')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s',
            loglevel=logging.DEBUG)

    args = parse_args()
    service = WindowService(port=args.port)
    logging.info('Starting server')

    service.run()
