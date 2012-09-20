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


def server_popen():
    if hasattr(sys, 'frozen'):
        server_process = Popen([base_path().joinpath('server.exe')], stdout=PIPE, stderr=PIPE)
    else:
        server_process = Popen([sys.executable, base_path().joinpath('server.py')], stdout=PIPE, stderr=PIPE)
    return server_process


override_methods = set()


def override(f):
    global override_methods
    override_methods.add(f.__name__)
    return f


class WindowServiceProxy(object):
    def __init__(self):
        global override_methods

        self._override_methods = override_methods
        self._server_process = server_popen()
        time.sleep(1)
        self._server = Server('http://localhost:8080')
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
    def select_video_mode(self, window_xid=None):
        if window_xid is None:
            window_xid = 0
        result = self._server.select_video_mode(window_xid)
        return pickle.loads(str(result))

    @override
    def create_process(self, window_xid):
        result = self._server.create_process(window_xid)
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
        for pid in self._pids:
            os.kill(pid, signal.SIGKILL)


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', loglevel=logging.DEBUG)

    service = WindowService()
    logging.info('Starting server')

    service.run()
