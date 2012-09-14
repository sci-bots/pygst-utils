import cgi
from multiprocessing import Pipe
import logging
import traceback
import multiprocessing
multiprocessing.freeze_support()

import blinker
import decimal
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
import gobject
gobject.threads_init()

from window_process import WindowProcess


class WindowService(object):
    def __init__(self, hostname='localhost', port=8080):
        self.server = SimpleJSONRPCServer(('localhost', 8080))
        self.server.register_function(pow)
        self.server.register_function(self.dump_args)
        self.server.register_function(self.create_process)
        self.server.register_function(self.create_pipeline)
        self.server.register_function(self.select_video_caps)
        self.server.register_function(self.terminate_process)
        self.server.register_function(self.stop_pipeline)
        self.server.register_function(self.start_pipeline)
        self.processes = {}

    def run(self):
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            for process in self.processes.values():
                process.join()

    def dump_args(self, args):
        print 'args={}'.format(args)

    def select_video_caps(self, window_xid):
        process = self.processes[window_xid]
        return process(command='select_video_caps', ack=True)['response']

    def terminate_process(self, window_xid):
        process = self.processes[window_xid]
        result = process(command='join', ack=True)
        process.terminate()
        del self.processes[window_xid]

    def stop_pipeline(self, window_xid):
        process = self.processes[window_xid]
        process(command='stop')

    def start_pipeline(self, window_xid):
        process = self.processes[window_xid]
        process(command='start')

    def create_process(self, window_xid):
        process = WindowProcess(window_xid)
        process.start()
        self.processes[window_xid] = process
        return None

    def create_pipeline(self, window_xid, video_settings, output_path=None, bitrate=None):
        process = self.processes[window_xid]
        device, caps_str = video_settings
        process(command='create', device=str(device), caps_str=str(caps_str),
                    output_path=output_path, bitrate=bitrate, ack=True)
