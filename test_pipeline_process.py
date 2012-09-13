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
    def __init__(self, window_xid, pipe):
        super(PipelineWindowProcess, self).__init__()
        self.pipe = pipe
        self.window_xid = window_xid
        self.pm = None

    def run(self):
        self.pm = GStreamerVideoPipelineManager()
        self.pm.window_xid = self.window_xid

        gtk.timeout_add(10, self._update_state)
        gtk.main()

    def create(self, device, caps_str, bitrate=None, record_path=None):
        from gst_video_source_caps_query.video_mode_dialog import create_video_source
        logging.debug('[PipelineWindowProcess] init_pipeline: %s' % self.window_xid)

        def init_pipeline(pm, device, caps_str, bitrate, record_path):
            logging.debug('[PipelineWindowProcess] init_pipeline: %s' % self.window_xid)
            video_source = create_video_source(device, caps_str)
            pipeline = get_pipeline(video_source, bitrate, record_path)
            pm.pipeline = pipeline
            pm.pipeline.set_state(gst.STATE_READY)
            return False
        init_pipeline(self.pm, device, caps_str, bitrate, record_path)

    def _update_state(self):
        gtk.threads_enter()
        try:
            logging.debug('[_update_state]')
            while self.pipe.poll():
                request = self.pipe.recv()
                logging.debug('  %s' % request)
                if request['command'] == 'start':
                    result = self.pm.pipeline.set_state(gst.STATE_PLAYING)
                    logging.debug('%s' % result)
                elif request['command'] == 'stop':
                    result = self.pm.pipeline.set_state(gst.STATE_NULL)
                    logging.debug('%s' % result)
                elif request['command'] == 'create':
                    print request
                    self.create(request['device'], request['caps_str'],
                            request.get('bitrate', None),
                                    request.get('output_path', None))
                elif request['command'] == 'join':
                    gtk.main_quit()
                    return False
            return True
        finally:
            gtk.threads_leave()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print >> sys.stderr, 'usage: %s <window_xid>' % sys.argv[0]
    window_xid = int(sys.argv[1])
    p = PipelineWindowProcess(window_xid)
    p.start()
    p.join()
