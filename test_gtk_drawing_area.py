#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gst
import gobject
gobject.threads_init()
gtk.gdk.threads_init()

from warp_perspective import warp_perspective
from cairo_draw import CairoDrawBase

class GTK_Main:
    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title("Mpeg2-Player")
        window.set_default_size(640, 480)
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
        self.movie_window = gtk.DrawingArea()
        vbox.add(self.movie_window)
        window.show_all()
        
        self.pipeline = gst.Pipeline('pipeline')

        if os.name == 'nt':
            webcam_src = gst.element_factory_make('dshowvideosrc', 'src')
            webcam_src.set_property('device-name', 'Microsoft LifeCam Studio')
        else:
            webcam_src = gst.element_factory_make('v4l2src', 'src')
            webcam_src.set_property('device', '/dev/video0')

        # -- setup webcam_src --
        webcam_caps = gst.Caps('video/x-raw-yuv,width=640,height=480,framerate=30/1')
        webcam_caps_filter = gst.element_factory_make('capsfilter', 'caps_filter')
        webcam_caps_filter.set_property('caps', webcam_caps)
        webcam_tee = gst.element_factory_make('tee', 'webcam_tee')
        #Feed branch
        feed_queue = gst.element_factory_make('queue', 'feed_queue')
        warp_in_color = gst.element_factory_make('ffmpegcolorspace', 'warp_in_color')
        self.warper = warp_perspective()
        warp_out_color = gst.element_factory_make('ffmpegcolorspace', 'warp_out_color')
        cairo_color_out = gst.element_factory_make('ffmpegcolorspace', 'cairo_color_out')
        cairo_draw = CairoDrawBase('cairo_draw')
        video_sink = gst.element_factory_make('autovideosink', 'video_sink')

        video_rate = gst.element_factory_make('videorate', 'video_rate')
        rate_caps = gst.Caps('video/x-raw-yuv,width=640,height=480,framerate=30/1')
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
                webcam_tee, feed_queue, video_sink, capture_queue, ffmpeg_color_space,
                ffenc_mpeg4, avi_mux, file_sink, self.warper, warp_in_color, warp_out_color, cairo_draw, cairo_color_out)

        record_warped = False
        if record_warped:
            gst.element_link_many(webcam_src, webcam_caps_filter, warp_in_color, self.warper, warp_out_color, video_rate, rate_caps_filter, webcam_tee)
            gst.element_link_many(webcam_tee, feed_queue, cairo_draw, video_sink)
            gst.element_link_many(webcam_tee, capture_queue, ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink)
        else:
            gst.element_link_many(webcam_src, webcam_caps_filter, video_rate, rate_caps_filter, webcam_tee)
            gst.element_link_many(webcam_tee, feed_queue, warp_in_color, self.warper, warp_out_color, cairo_draw, cairo_color_out, video_sink)
            gst.element_link_many(webcam_tee, capture_queue, ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
        
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
                        
    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.pipeline.set_state(gst.STATE_NULL)
            self.button.set_label("Start")
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.pipeline.set_state(gst.STATE_NULL)
            self.button.set_label("Start")
    
    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            gtk.gdk.threads_enter()
            imagesink.set_xwindow_id(self.movie_window.window.xid)
            gtk.gdk.threads_leave()
    
    def demuxer_callback(self, demuxer, pad):
        if pad.get_property("template").name_template == "video_%02d":
            qv_pad = self.queuev.get_pad("sink")
            pad.link(qv_pad)
        elif pad.get_property("template").name_template == "audio_%02d":
            qa_pad = self.queuea.get_pad("sink")
            pad.link(qa_pad)
        
GTK_Main()
gtk.main()
