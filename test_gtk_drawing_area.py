#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
#import pygst
#pygst.require("0.10")
import gst
import gobject
gobject.threads_init()
gtk.gdk.threads_init()

from gstreamer_view import GStreamerVideoView, get_supported_dims
from play_bin import PlayBin
from record_bin import RecordBin


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
        
        self.pipeline = gst.Pipeline('pipeline')

        if os.name == 'nt':
            webcam_src = gst.element_factory_make('dshowvideosrc', 'webcam_src')
            webcam_src.set_property('device-name', 'Microsoft LifeCam Studio')
        else:
            webcam_src = gst.element_factory_make('v4l2src', 'webcam_src')
            webcam_src.set_property('device', '/dev/video1')
        self.supported_dims = get_supported_dims(webcam_src)
        print self.supported_dims

        self.play_bin = PlayBin('play_bin', webcam_src, width=800, height=600,
                fps=15)
        self.record_bin = RecordBin('record_bin', width=640, height=480)

        self.pipeline.add(self.play_bin)

        self.movie_view = GStreamerVideoView(self.pipeline)
        self.movie_window = self.movie_view.widget
        self.movie_window.set_size_request(640, 480)
        self.aframe.add(self.movie_window)
        vbox.pack_start(self.aframe, False)
        window.show_all()
        self.window = window

    def start_stop(self, w):
        if self.button.get_label() == "Start":
            self.button.set_label("Stop")
            transform_str = self.entry.get_text()
            if transform_str:
                self.play_bin.warper.set_property('transform_matrix', transform_str)
            self.pipeline.add(self.record_bin)
            self.play_bin.link(self.record_bin)
            self.pipeline.set_state(gst.STATE_PLAYING)
        else:
            self.pipeline.set_state(gst.STATE_NULL)
            self.play_bin.unlink(self.record_bin)
            self.pipeline.remove(self.record_bin)
            self.button.set_label("Start")

    def on_destroy(self, *args):
        self.pipeline.set_state(gst.STATE_NULL)
        gtk.main_quit()


if __name__ == '__main__':        
    GTK_Main()
    gtk.main()
