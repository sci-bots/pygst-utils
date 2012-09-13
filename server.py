import cgi
from multiprocessing import Pipe
import logging
import multiprocessing
multiprocessing.freeze_support()

import blinker
import decimal
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

from test_pipeline_process import PipelineWindowProcess


class GStreamerService(object):
    def __init__(self, hostname='localhost', port=8080):
        self.server = SimpleJSONRPCServer(('localhost', 8080))
        self.server.register_function(pow)
        self.server.register_function(self.run_pipeline)
        self.server.register_function(self.terminate_pipeline)
        self.server.register_function(self.stop_pipeline)
        self.processes = {}
        self.pipes = {}

    def run(self):
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            for process in self.processes.values():
                process.join()

    def terminate_pipeline(self, window_xid):
        print 'terminate_pipeline: %s' % window_xid
        process = self.processes[window_xid]
        process.terminate()
        del self.pipes[window_xid]
        del self.processes[window_xid]
        print '  (terminated)'

    def stop_pipeline(self, window_xid):
        print 'stop_pipeline: %s' % window_xid
        master_pipe, worker_pipe = self.pipes[window_xid]
        master_pipe.send({'command': 'stop'})
        master_pipe.send({'command': 'join'})
        print self.processes.keys()
        
    def start_pipeline(self, window_xid):
        print 'start_pipeline: %s' % window_xid
        master_pipe, worker_pipe = self.pipes[window_xid]
        master_pipe.send({'command': 'start'})

    def create_pipeline(self, window_xid, video_settings, output_path=None,
            bitrate=None):
        print 'create_pipeline: %s' % window_xid
        master_pipe, worker_pipe = self.pipes[window_xid] = Pipe()
        process = PipelineWindowProcess(window_xid, worker_pipe)
        device, caps_str = video_settings
        worker_pipe.send({'command': 'create', 'device': device, 'caps_str': caps_str,
                'output_path': output_path, 'bitrate': bitrate})
        self.processes[window_xid] = process
        print self.processes.keys()


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', loglevel=logging.DEBUG)

    service = GStreamerService()
    logging.info('Starting server')

    service.run()
