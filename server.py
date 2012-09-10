import cgi
from multiprocessing import Pipe
import multiprocessing
multiprocessing.freeze_support()

import blinker
import decimal
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

from test_pipeline_process import PipelineWindowProcess


processes = {}
pipes = {}


def terminate_pipeline(window_xid):
    print 'terminate_pipeline: %s' % window_xid
    process = processes[window_xid]
    process.terminate()
    del pipes[window_xid]
    del processes[window_xid]
    print '  (terminated)'


def stop_pipeline(window_xid):
    print 'stop_pipeline: %s' % window_xid
    master_pipe, worker_pipe = pipes[window_xid]
    master_pipe.send({'command': 'stop'})
    master_pipe.send({'command': 'join'})
    print processes.keys()
    

def run_pipeline(window_xid, video_settings, output_path, bitrate):
    print 'run_pipeline: %s' % window_xid
    master_pipe, worker_pipe = pipes[window_xid] = Pipe()
    process = PipelineWindowProcess(window_xid, video_settings, output_path, bitrate, worker_pipe)
    process.start()
    processes[window_xid] = process
    print processes.keys()


if __name__ == '__main__':
    import logging
    logging.basicConfig(format='[%(levelname)s] %(message)s', loglevel=logging.DEBUG)
    logging.info('Starting server')

    server = SimpleJSONRPCServer(('localhost', 8080))
    server.register_function(pow)
    server.register_function(run_pipeline)
    server.register_function(terminate_pipeline)
    server.register_function(stop_pipeline)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes.values():
            process.join()
