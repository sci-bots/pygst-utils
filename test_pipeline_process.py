from pprint import pformat
import sys
import logging
from multiprocessing import Process, Pipe
import multiprocessing
multiprocessing.freeze_support()

from test_video import get_pipeline
from gstreamer_view import GStreamerVideoPipelineManager
import gst
import glib
import gtk
gtk.threads_init()


class PipelineWindowProcess(Process):
    def __init__(self, window_xid):
        super(PipelineWindowProcess, self).__init__()
        self.parent_pipe, self.child_pipe = Pipe()
        self.window_xid = window_xid
        self.pm = None

    def run(self):
        '''
        Method to be run in the child process.
        '''
        self.pm = GStreamerVideoPipelineManager()
        self.pm.window_xid = self.window_xid

        gtk.timeout_add(100, self._update_state)
        gtk.main()

    def _update_state(self):
        '''
        This method will be called at regular intervals to handle any
        pending requests in the pipe.
        '''
        while self.child_pipe.poll():
            request = self.child_pipe.recv()
            try:
                threads_entered = False
                gtk.threads_enter()
                threads_entered = True
                response = self._process_request(request)
                if request.get('ack', False):
                    self.child_pipe.send({'response': response})
            finally:
                if threads_entered:
                    gtk.threads_leave()
        return True

    def _process_request(self, request):
        '''
        Execute the specified command by looking up the corresponding
        member function.
        '''
        response = None
        command_attr = '_%s' % request.get('command', None)
        if hasattr(self, command_attr):
            return getattr(self, command_attr)(**request)
        else:
            logging.warning('Invalid command: %s' % request.get('command',
                    None))
            return None

    ### command-processing methods ####################################################

    def _start(self, **kwargs):
        response = self.pm.pipeline.set_state(gst.STATE_PLAYING)
        return response

    def _get_state(self, **kwargs):
        response = self.pm.pipeline.get_state(gst.STATE_NULL)
        return response

    def _select_video_caps(self, **kwargs):
        from gst_video_source_caps_query.video_mode_dialog import select_video_caps

        device, caps_str = select_video_caps()
        return {'device': device, 'caps_str': caps_str}

    def _stop(self, **kwargs):
        response = self.pm.pipeline.set_state(gst.STATE_NULL)
        return response

    def _create(self, **kwargs):
        response = self.create(kwargs['device'], kwargs['caps_str'],
                kwargs.get('bitrate', None),
                        kwargs.get('output_path', None))
        return response

    def _join(self, **kwargs):
        gtk.main_quit()
        return False

    ### utility methods ####################################################

    def create(self, device, caps_str, bitrate=None, record_path=None):
        from gst_video_source_caps_query.video_mode_dialog import create_video_source

        def init_pipeline(pm, device, caps_str, bitrate, record_path):
            video_source = create_video_source(device, caps_str)
            pipeline = get_pipeline(video_source, bitrate, record_path)
            pm.pipeline = pipeline
            return pm.pipeline.set_state(gst.STATE_READY)
        return init_pipeline(self.pm, device, caps_str, bitrate, record_path)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print >> sys.stderr, 'usage: %s <window_xid>' % sys.argv[0]
    window_xid = int(sys.argv[1])
    p = PipelineWindowProcess(window_xid)
    p.start()
    p.join()
