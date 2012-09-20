import os
import signal
import cgi
import logging
import multiprocessing
multiprocessing.freeze_support()
try:
    import cPickle as pickle
except ImportError:
    import pickle

import blinker
import decimal
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
import gobject
gobject.threads_init()

from window_process import WindowProcess


methods = set()

def register(f):
    global methods

    methods.add(f.__name__)
    return f


class WindowService(object):
    def __init__(self, hostname='localhost', port=8080):
        global methods

        self._methods = methods
        self.server = SimpleJSONRPCServer((hostname, port))
        self.server.register_introspection_functions()
        for method in self._methods:
            self.server.register_function(eval('self.{}'.format(method)))
        self.processes = {}

    def run(self):
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            for process in self.processes.values():
                process.join()

    @register
    def get_available_methods(self):
        '''
        Return a dictionary mapping each available method name to the
        doc-string for method.
        '''
        return dict([(method, eval('self.{}.__doc__'.format(method)))
                for method in self._methods])

    @register
    def dump_args(self, args):
        print 'args={}'.format(args)

    @register
    def select_video_mode(self, window_xid):
        '''
        Launch a GTK prompt to select a video mode.
        '''
        process = self.processes[window_xid]
        return pickle.dumps(process(command='select_video_mode',
                ack=True)['response'])

    @register
    def select_video_caps(self, window_xid):
        '''
        Launch a GTK prompt to select a video device and caps string.
        '''
        process = self.processes[window_xid]
        return process(command='select_video_caps', ack=True)['response']

    @register
    def terminate_process(self, window_xid):
        '''
        Terminate the GStreamer process.
        '''
        process = self.processes[window_xid]
        result = process(command='join', ack=True)
        process.terminate()
        del self.processes[window_xid]
        return True

    @register
    def stop_pipeline(self, window_xid):
        '''
        Stop the GStreamer pipeline.
        '''
        process = self.processes[window_xid]
        process(command='stop')

    @register
    def start_pipeline(self, window_xid):
        '''
        Start the GStreamer pipeline.
        '''
        process = self.processes[window_xid]
        process(command='start')

    @register
    def get_video_mode_map(self, window_xid):
        '''
        Return a dictionary mapping video mode strings to video settings
        dictionaries.
        '''
        process = self.processes[window_xid]
        result = process(command='get_video_mode_map', ack=True)
        return pickle.dumps(result['response'])

    @register
    def get_video_mode_enum(self, window_xid):
        process = self.processes[window_xid]
        result = process(command='get_video_mode_enum', ack=True)
        return pickle.dumps(result['response'])

    @register
    def get_process_pid(self, window_xid):
        '''
        Return the ID of the GStreamer process.
        '''
        process = self.processes[window_xid]
        result = process(command='get_pid', ack=True)
        return result['response']

    @register
    def get_pid(self):
        '''
        Return the ID of this server process.
        '''
        return os.getpid()

    @register
    def create_process(self, window_xid, force_aspect_ratio=True):
        '''
        Create a new GStreamer process for the specified window xid.
        '''
        process = WindowProcess(window_xid,
                force_aspect_ratio=force_aspect_ratio)
        process.start()
        self.processes[window_xid] = process
        return None

    @register
    def create_pipeline(self, window_xid, video_settings, output_path=None, bitrate=None):
        '''
        Create a new GStreamer pipeline with the specified video settings.
        '''
        process = self.processes[window_xid]
        device, caps_str = video_settings
        process(command='create', device=str(device), caps_str=str(caps_str),
                    output_path=output_path, bitrate=bitrate, ack=True)