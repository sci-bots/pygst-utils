#!/usr/bin/env python
import socket
import os
import signal
import time
try:
    import cPickle as pickle
except ImportError:
    import pickle

from pygst_utils.bin.server import server_popen


override_methods = set()


def override(f):
    global override_methods
    override_methods.add(f.__name__)
    return f



class ConnectionError(Exception): pass


class WindowServiceProxy(object):
    def __init__(self, port=8080):
        from jsonrpclib import Server

        global override_methods

        self._override_methods = override_methods
        self._server_process = server_popen(port)
        self._server = Server('http://localhost:{}'.format(port))
        #time.sleep(3.0)
        self._initialized = True
        self._methods = None
        for i in range(10):
            try:
                self._methods = set(self._server.system.listMethods())
                break
            except socket.error, why:
                time.sleep(0.1 * (i + 1))
        if self._methods is None:
            self._initialized = False
            raise

        self._server.create_process(0)
        self._pids = [self._server.get_pid(),
                self._server.get_process_pid(0)]

    def __getattr__(self, attr):
        if attr in self._methods and attr not in self._override_methods:
            result = getattr(self._server, attr)
            time.sleep(0.2)
            return result
        else:
            return object.__getattribute__(self, attr)

    @property
    def pids(self):
        return tuple(self._pids)

    @override
    def set_draw_queue(self, window_xid, draw_queue):
        draw_queue_pickle = pickle.dumps(draw_queue)
        result = self._server.set_draw_queue(window_xid, draw_queue_pickle)
        return result

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
    def create_pipeline(self, window_xid, video_settings, output_path=None,
            bitrate=None, draw_queue=None):
        if draw_queue:
            draw_queue_pickle = pickle.dumps(draw_queue)
        else:
            draw_queue_pickle = None
        result = self._server.create_pipeline(window_xid, video_settings,
                output_path, bitrate, draw_queue_pickle)
        pid = self._server.get_process_pid(window_xid)
        self._pids.append(pid)
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
