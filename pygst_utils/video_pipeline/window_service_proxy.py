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

import zmq
from serialsocket import SerializingSocket

override_methods = set()


def override(f):
    global override_methods
    override_methods.add(f.__name__)
    return f



class ConnectionError(Exception): pass


class DeferredCommand(object):
    def __init__(self, command, sock):
        self.command = command
        self.sock = sock

    def __call__(self, *args, **kwargs):
        command_args = kwargs.copy()
        command_args.update({'command': self.command, 'args': args or [],
                             'kwargs': kwargs or {}})
        self.sock.send_zipped_pickle(command_args)
        return self.sock.recv_zipped_pickle()


class WindowServiceProxy(object):
    def __init__(self, port=8080, force_aspect_ratio=False):
        global override_methods

        print '[WindowServiceProxy] force_aspect_ratio={}'.format(force_aspect_ratio)
        self._force_aspect_ratio = force_aspect_ratio
        self._port = port
        self._override_methods = override_methods
        self._server_process = server_popen(port,
                force_aspect_ratio=force_aspect_ratio)
        self._ctx = zmq.Context.instance()
        self._sock = SerializingSocket(self._ctx, zmq.REQ)
        self._sock.connect('tcp://localhost:%d' % port)
        self._initialized = True
        self._methods = set(['get_available_commands'])
        self._methods = self._methods.union(set(self.get_available_commands()))

    def __getattr__(self, attr):
        if attr in self._methods and attr not in self._override_methods:
            return DeferredCommand(attr, self._sock)
        else:
            return object.__getattribute__(self, attr)

    @property
    def port(self):
        return self._port

    @property
    def pids(self):
        return tuple(self._pids)

    def add_pid(self, pid):
        if pid not in self.pids:
            self._pids.append(pid)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self._initialized:
            try:
                child_joined = False
                self._sock.send_zipped_pickle({'command': 'join'})
                for i in range(5):
                    if self._sock.poll(50):
                        self._sock.recv_zipped_pickle()
                        child_joined = True
            finally:
                if not child_joined:
                    self._server_process.terminate()
                self._initialized = False
