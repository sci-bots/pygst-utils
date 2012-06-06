#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
#import pygst
#pygst.require("0.10")
import gst
import gobject
gobject.threads_init()
gtk.gdk.threads_init()

from warp_perspective import warp_perspective, WarpBin
from gstreamer_view import GStreamerVideoView, get_supported_dims
from rated_bin import RatedBin


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
        
        self.pipeline = gst.Pipeline('pipeline')

        camera_bin = gst.element_factory_make('camerabin', 'camera_bin')
        warp_bin = WarpBin('warp_bin')

        camera_bin.set_property('viewfinder-filter', warp_bin)

        # Disable audio
        flags = camera_bin.get_property('flags')
        camera_bin.set_property('flags', flags | 0x020)

        # Set mode to video (rather than image)
        camera_bin.set_property('mode', 1)

        # Set video source to test source
        camera_bin.set_property('video-source', self.get_test_src())
        self.record_enabled = False

        # Set recording format to mpeg4 avi
        avi_mux = gst.element_factory_make('avimux', 'avi_mux')
        ffenc_mpeg4 = gst.element_factory_make('ffenc_mpeg4', 'ffenc_mpeg40') 
        ffenc_mpeg4.set_property('bitrate', 1200000)

        camera_bin.set_property('video-muxer', avi_mux)
        camera_bin.set_property('video-encoder', ffenc_mpeg4)

        self.pipeline.add(camera_bin)

        self.movie_view = GStreamerVideoView(self.pipeline)
        self.movie_window = self.movie_view.widget
        self.movie_window.set_size_request(640, 480)
        self.aframe.add(self.movie_window)
        vbox.pack_start(self.aframe, False)
        window.show_all()
        self.window = window
        self.pipeline.set_state(gst.STATE_PLAYING)

    def get_auto_src(self):
        return RatedBin('video_src')

    def get_test_src(self):
        video_src = gst.element_factory_make('videotestsrc', 'video_src')
        video_src.set_property('pattern', 2)
        return RatedBin('video_src', video_src=video_src)

    def start_stop(self, w):
        if self.button.get_label() == "Start":
            camera_bin = self.pipeline.get_by_name('camera_bin')
            if not self.record_enabled:
                self.pipeline.set_state(gst.STATE_NULL)
                camera_bin.set_property('video-source', self.get_auto_src())
                self.pipeline.set_state(gst.STATE_PLAYING)
            transform_str = self.entry.get_text()
            if transform_str:
                warp_bin = camera_bin.get_by_name('warp_bin')
                warp_bin.warper.set_property('transform_matrix', transform_str)
            ready = False
            for i in range(5):
                if camera_bin.get_property('ready-for-capture'):
                    ready = True
                    break
                time.sleep(0.1)
            if not ready:
                raise RuntimeError, 'camerabin is not ready for capture'
            camera_bin.set_property('filename', 'test.avi')
            camera_bin.emit('capture-start')

            self.button.set_label("Stop")
        else:
            camera_bin = self.pipeline.get_by_name('camera_bin')
            camera_bin.emit('capture-stop')
            self.pipeline.set_state(gst.STATE_NULL)
            camera_bin.set_property('video-source', self.get_test_src())
            self.pipeline.set_state(gst.STATE_PLAYING)
            self.button.set_label("Start")

    def on_destroy(self, *args):
        self.pipeline.set_state(gst.STATE_NULL)
        gtk.main_quit()


if __name__ == '__main__':        
    GTK_Main()
    gtk.main()
