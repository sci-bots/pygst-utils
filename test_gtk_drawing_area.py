#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
try:
    import pygst
    pygst.require("0.10")
except ImportError:
    pass
finally:
    import gst
import gobject
gobject.threads_init()
gtk.gdk.threads_init()

from warp_perspective import warp_perspective, WarpBin
from gstreamer_view import GStreamerVideoView, get_supported_dims
from rated_bin import RatedBin
from gst_video_source_caps_query.gst_video_source_caps_query import DeviceNotFound, GstVideoSourceManager, FilteredInput


video_modes = GstVideoSourceManager.get_available_video_modes(
        format_='YUY2')
device_key, devices = GstVideoSourceManager.get_video_source_configs()

#gst.debug_set_active(True)
#gst.debug_set_default_threshold(3)

class GTK_Main:
    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title("Mpeg2-Player")
        window.set_default_size(640, 500)
        window.connect("destroy", self.on_destroy)
        vbox = gtk.VBox()
        window.add(vbox)
        hbox = gtk.HBox()
        vbox.pack_start(hbox, False)
        self.entry = gtk.Entry()
        # Set default transform to identity
        self.entry.set_text('1,0,0,0,1,0,0,0,1')
        hbox.add(self.entry)
        self.button = gtk.Button("Start")
        hbox.pack_start(self.button, False)
        self.button.connect("clicked", self.start_stop)
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=1.0, ratio=4.0 / 3.0,
                obey_child=False)
        
        from test_video import get_pipeline, get_auto_src
        self.pipeline = get_pipeline()

        self.movie_view = GStreamerVideoView(self.pipeline)
        self.movie_window = self.movie_view.widget
        self.movie_window.set_size_request(640, 480)
        self.aframe.add(self.movie_window)
        vbox.pack_start(self.aframe, False)
        window.show_all()
        self.window = window

    def start_stop(self, w):
        if self.button.get_label() == "Start":
            self.pipeline.set_state(gst.STATE_PLAYING)

            self.button.set_label("Stop")
        else:
            self.pipeline.set_state(gst.STATE_NULL)
            self.button.set_label("Start")

    def on_destroy(self, *args):
        self.pipeline.set_state(gst.STATE_NULL)
        gtk.main_quit()


if __name__ == '__main__':        
    GTK_Main()
    gtk.main()
