#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
#import pygst
#pygst.require("0.10")
import gst
import gobject
gobject.threads_init()
gtk.gdk.threads_init()

from warp_perspective import warp_perspective
from cairo_draw import CairoDrawBase
from gstreamer_view import GStreamerVideoView


class GTK_Main:
    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title("Mpeg2-Player")
        window.set_default_size(640, 500)
        window.connect("destroy", gtk.main_quit, "WM destroy")
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
            webcam_src = gst.element_factory_make('dshowvideosrc', 'src')
            webcam_src.set_property('device-name', 'Microsoft LifeCam Studio')
        else:
            webcam_src = gst.element_factory_make('v4l2src', 'src')
            webcam_src.set_property('device', '/dev/video0')

        # -- setup webcam_src --
        webcam_caps = gst.Caps('video/x-raw-yuv,width=640,height=480,framerate=15/1')
        webcam_caps_filter = gst.element_factory_make('capsfilter', 'caps_filter')
        webcam_caps_filter.set_property('caps', webcam_caps)
        webcam_tee = gst.element_factory_make('tee', 'webcam_tee')
        #Feed branch
        feed_queue = gst.element_factory_make('queue', 'feed_queue')
        warp_in_color = gst.element_factory_make('ffmpegcolorspace', 'warp_in_color')
        self.warper = warp_perspective()
        warp_out_color = gst.element_factory_make('ffmpegcolorspace', 'warp_out_color')
        cairo_color_in = gst.element_factory_make('ffmpegcolorspace', 'cairo_color_in')
        cairo_color_out = gst.element_factory_make('ffmpegcolorspace', 'cairo_color_out')
        cairo_draw = CairoDrawBase('cairo_draw')
        video_sink = gst.element_factory_make('autovideosink', 'video_sink')
        #video_sink = gst.element_factory_make('dshowvideosink', 'video_sink')
        #video_sink = gst.element_factory_make('directdrawsink', 'video_sink')
        #video_sink = gst.element_factory_make('gdkpixbufsink', 'video_sink')
        

        video_rate = gst.element_factory_make('videorate', 'video_rate')
        rate_caps = gst.Caps('video/x-raw-yuv,width=640,height=480,framerate=15/1')
        rate_caps_filter = gst.element_factory_make('capsfilter', 'rate_caps_filter')
        rate_caps_filter.set_property('caps', rate_caps)

        capture_queue = gst.element_factory_make('queue', 'capture_queue')
        ffmpeg_color_space = gst.element_factory_make('ffmpegcolorspace', 'ffmpeg_color_space')
        ffenc_mpeg4 = gst.element_factory_make('ffenc_mpeg4', 'ffenc_mpeg40') 
        ffenc_mpeg4.set_property('bitrate', 1200000)
        avi_mux = gst.element_factory_make('avimux', 'avi_mux')
        file_sink = gst.element_factory_make('filesink', 'file_sink')
        file_sink.set_property('location', 'temp.avi')

        self.pipeline.add(webcam_src, webcam_caps_filter, video_rate, rate_caps_filter,
                feed_queue, video_sink,

                # Elements for drawing cairo overlay on video
                cairo_draw, cairo_color_out, cairo_color_in,

                # Elements for applying OpenCV warp-perspective transformation
                self.warper, warp_in_color, warp_out_color,

                webcam_tee, 
                # Elements for writing video to file
                capture_queue, ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink,
                )

        record_warped = False
        if record_warped:
            gst.element_link_many(webcam_src, webcam_caps_filter, warp_in_color, self.warper, warp_out_color, video_rate, rate_caps_filter, webcam_tee)
            gst.element_link_many(webcam_tee, feed_queue, cairo_draw, video_sink)
            gst.element_link_many(webcam_tee, capture_queue, ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink)
        else:
            #gst.element_link_many(webcam_src, webcam_caps_filter, video_rate, rate_caps_filter, feed_queue, cairo_color_in, cairo_draw, cairo_color_out, video_sink)
            gst.element_link_many(webcam_src, webcam_caps_filter, video_rate, rate_caps_filter, webcam_tee)
            gst.element_link_many(webcam_tee, feed_queue, warp_in_color, self.warper, warp_out_color, cairo_draw, cairo_color_out, video_sink)
            #gst.element_link_many(webcam_tee, feed_queue, cairo_color_in, cairo_draw, cairo_color_out, video_sink)
            gst.element_link_many(webcam_tee, capture_queue, ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink)

        self.movie_view = GStreamerVideoView(self.pipeline)
        self.movie_window = self.movie_view.widget
        self.movie_window.set_size_request(640, 480)
        self.aframe.add(self.movie_window)
        vbox.pack_start(self.aframe, False)
        window.show_all()
        self.movie_view.run()
        self.window = window

    def start_stop(self, w):
        if self.button.get_label() == "Start":
            self.button.set_label("Stop")
            transform_str = self.entry.get_text()
            if transform_str:
                self.warper.set_property('transform_matrix', transform_str)
            self.pipeline.set_state(gst.STATE_PLAYING)
        else:
            self.pipeline.set_state(gst.STATE_NULL)
            self.button.set_label("Start")
                        

if __name__ == '__main__':        
    GTK_Main()
    gtk.main()
