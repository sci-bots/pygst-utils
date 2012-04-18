import logging

#import pygst
#pygst.require('0.10')
import gst
from path import path
import gtk
gtk.gdk.threads_init()

# this is very important, without this, callbacks from gstreamer thread
# will messed our program up
import gobject
gobject.threads_init()


def on_msg(bus, msg):
    if msg.type == gst.MESSAGE_ERROR:
        error, debug = msg.parse_error()
        print error, debug
    elif msg.type == gst.MESSAGE_EOS:
        duration = pipeline.query_duration(gst.FORMAT_TIME)
        print 'Duration', duration
        return True
    elif msg.type == gst.MESSAGE_STATE_CHANGED:
        oldstate, newstate, pending = gst.Message.parse_state_changed(msg)
        print oldstate, newstate, pending
        if newstate == gst.STATE_PAUSED and oldstate == gst.STATE_READY:
            print 'set state to playing'
            pipeline.set_state(gst.STATE_PLAYING)


pipeline = gst.Pipeline('pipeline')

#webcam_src = gst.element_factory_make('v4l2src', 'src')
webcam_src = gst.element_factory_make('dshowvideosrc', 'src')

# -- setup webcam_src --
webcam_src.set_property('device-name', 'Microsoft LifeCam Studio')
webcam_caps = gst.Caps('video/x-raw-yuv,width=640,height=480,framerate=30/1')
webcam_caps_filter = gst.element_factory_make('capsfilter', 'caps_filter')
webcam_caps_filter.set_property('caps', webcam_caps)
webcam_tee = gst.element_factory_make('tee', 'webcam_tee')
#Feed branch
feed_queue = gst.element_factory_make('queue', 'feed_queue')
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

# videorate ! video/x-raw-yuv,framerate=10/1 ! queue ! ffmpegcolorspace ! ffenc_mpeg4 bitrate=1200000 ! avimux ! filesink location=temp.avi
#video_sink = gst.element_factory_make('xvimagesink', 'sink')

pipeline.add(webcam_src, webcam_caps_filter, video_rate, rate_caps_filter,
        webcam_tee, feed_queue, video_sink, capture_queue, ffmpeg_color_space,
        ffenc_mpeg4, avi_mux, file_sink)
gst.element_link_many(webcam_src, webcam_caps_filter, video_rate, rate_caps_filter, webcam_tee)
gst.element_link_many(webcam_tee, feed_queue, video_sink)
gst.element_link_many(webcam_tee, capture_queue, ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink)

bus = pipeline.get_bus()
bus.add_signal_watch()
bus.connect('message', on_msg)

pipeline.set_state(gst.STATE_PLAYING)

try:
    gtk.main()
except KeyboardInterrupt:
    pipeline.set_state(gst.STATE_NULL)
