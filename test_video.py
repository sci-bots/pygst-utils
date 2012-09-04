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
from gst_video_source_caps_query.gst_video_source_caps_query import DeviceNotFound, GstVideoSourceManager, FilteredInput


video_modes = GstVideoSourceManager.get_available_video_modes(
        format_='YUY2')
device_key, devices = GstVideoSourceManager.get_video_source_configs()


def get_auto_src(name):
    video_source = GstVideoSourceManager.get_video_source()
    selected_mode = video_modes[0]
    video_source.set_property(device_key, selected_mode['device'])
    caps_str = GstVideoSourceManager.get_caps_string(selected_mode)
    filtered_input = FilteredInput(name, caps_str, video_source)
    return filtered_input




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

webcam_src = get_auto_src('webcam_src')
webcam_tee = gst.element_factory_make('tee', 'webcam_tee')
#Feed branch
feed_queue = gst.element_factory_make('queue', 'feed_queue')
video_sink = gst.element_factory_make('autovideosink', 'video_sink')

video_rate = gst.element_factory_make('videorate', 'video_rate')
rate_caps = gst.Caps('video/x-raw-yuv,framerate=15/1')
rate_caps_filter = gst.element_factory_make('capsfilter', 'rate_caps_filter')
rate_caps_filter.set_property('caps', rate_caps)

capture_queue = gst.element_factory_make('queue', 'capture_queue')
ffmpeg_color_space = gst.element_factory_make('ffmpegcolorspace', 'ffmpeg_color_space')
ffenc_mpeg4 = gst.element_factory_make('xvidenc', 'ffenc_mpeg40') 
ffenc_mpeg4.set_property('bitrate', 1200000)
avi_mux = gst.element_factory_make('avimux', 'avi_mux')
file_sink = gst.element_factory_make('filesink', 'file_sink')
file_sink.set_property('location', 'temp.avi')

# videorate ! video/x-raw-yuv,framerate=10/1 ! queue ! ffmpegcolorspace ! ffenc_mpeg4 bitrate=1200000 ! avimux ! filesink location=temp.avi
#video_sink = gst.element_factory_make('xvimagesink', 'sink')

pipeline.add(webcam_src, video_rate, rate_caps_filter,
        webcam_tee, feed_queue, video_sink, capture_queue, ffmpeg_color_space,
        ffenc_mpeg4, avi_mux, file_sink)
gst.element_link_many(webcam_src, video_rate, rate_caps_filter, webcam_tee)
gst.element_link_many(webcam_tee, feed_queue, video_sink)
gst.element_link_many(webcam_tee, capture_queue, ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink)

bus = pipeline.get_bus()
bus.add_signal_watch()
bus.connect('message', on_msg)

pipeline.set_state(gst.STATE_PLAYING)

src_pad = webcam_src.get_pad('src')
framerate = src_pad.get_caps()[0]['framerate']
framerate = {'num': framerate.num, 'denom': framerate.denom, }
print framerate

try:
    gtk.main()
except KeyboardInterrupt:
    pipeline.set_state(gst.STATE_NULL)
