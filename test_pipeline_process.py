import sys
from multiprocessing import Process

from gst_video_source_caps_query.video_mode_dialog import get_pipeline
from gstreamer_view import GStreamerVideoPipelineManager
import gst
import glib
import gtk
gtk.threads_init()


class PipelineWindowProcess(Process):
    def __init__(self, window_xid):
        super(PipelineWindowProcess, self).__init__()
        self.window_xid = window_xid

    def run(self):
        pm = GStreamerVideoPipelineManager()
        pm.window_xid = self.window_xid
        def init_pipeline(pm):
            gtk.threads_enter()
            pipeline = get_pipeline()
            gtk.threads_leave()
            pm.pipeline = pipeline
            pm.pipeline.set_state(gst.STATE_PLAYING)
            return False
        init_pipeline(pm)
        gtk.main()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print >> sys.stderr, 'usage: %s <window_xid>' % sys.argv[0]
    window_xid = int(sys.argv[1])
    p = PipelineWindowProcess(window_xid)
    p.start()
    p.join()
