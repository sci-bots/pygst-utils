from pprint import pformat
import sys
import logging
from multiprocessing import Process, Pipe
import multiprocessing
multiprocessing.freeze_support()

from test_video import get_pipeline
#from gst_video_source_caps_query.video_mode_dialog import get_pipeline
from gstreamer_view import GStreamerVideoPipelineManager
import gst
import glib
import gtk
gtk.threads_init()


class PipelineWindowProcess(Process):
    def __init__(self, window_xid, video_settings, output_path, bitrate, pipe):
        super(PipelineWindowProcess, self).__init__()
        self.pipe = pipe
        self.window_xid = window_xid
        self.device, self.caps_str = video_settings
        self.caps_str = str(self.caps_str)
        self.output_path = output_path
        self.bitrate = bitrate

    def get_video_source(self):
        from gst_video_source_caps_query.video_mode_dialog import create_video_source

        video_source = create_video_source(self.device, self.caps_str)
        return video_source

    def run(self):
        self.pm = GStreamerVideoPipelineManager()
        self.pm.window_xid = self.window_xid
        def init_pipeline(pm):
            logging.debug('[PipelineWindowProcess] init_pipeline: %s' % self.window_xid)
            pipeline = get_pipeline(self.get_video_source(), self.bitrate, self.output_path)
            #pipeline = get_pipeline()
            pm.pipeline = pipeline
            pm.pipeline.set_state(gst.STATE_PLAYING)
            return False
        gtk.threads_enter()
        init_pipeline(self.pm)
        gtk.threads_leave()
        gtk.timeout_add(500, self._update_state)
        gtk.main()

    def _update_state(self):
        gtk.threads_enter()
        try:
            logging.debug('[_update_state]')
            while self.pipe.poll():
                request = self.pipe.recv()
                logging.debug('  %s' % request)
                if request['command'] == 'stop':
                    gtk.threads_enter()
                    result = self.pm.pipeline.set_state(gst.STATE_NULL)
                    gtk.threads_leave()
                    logging.debug('%s' % result)
                    self.pm.pipeline = None
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
