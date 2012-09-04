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
from gst_video_source_caps_query.gst_video_source_caps_query import \
        DeviceNotFound, GstVideoSourceManager, FilteredInput
from gstreamer_view import GStreamerVideoView


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


def get_pipeline():
    pipeline = gst.Pipeline('pipeline')

    webcam_src = get_auto_src('webcam_src')
    webcam_tee = gst.element_factory_make('tee', 'webcam_tee')

    #Feed branch
    feed_queue = gst.element_factory_make('queue', 'feed_queue')
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')

    video_rate = gst.element_factory_make('videorate', 'video_rate')
    rate_caps = gst.Caps('video/x-raw-yuv,framerate=%(num)d/%(denom)s'\
            % get_framerate(webcam_src))
    rate_caps_filter = gst.element_factory_make('capsfilter',
            'rate_caps_filter')
    rate_caps_filter.set_property('caps', rate_caps)

    capture_queue = gst.element_factory_make('queue', 'capture_queue')
    ffmpeg_color_space = gst.element_factory_make('ffmpegcolorspace', 'ffmpeg_color_space')
    ffenc_mpeg4 = gst.element_factory_make('xvidenc', 'ffenc_mpeg40') 
    ffenc_mpeg4.set_property('bitrate', 1200000)
    avi_mux = gst.element_factory_make('avimux', 'avi_mux')
    file_sink = gst.element_factory_make('filesink', 'file_sink')
    file_sink.set_property('location', 'temp.avi')

    pipeline.add(webcam_src, video_rate, rate_caps_filter,
            webcam_tee, feed_queue, video_sink, capture_queue,
            ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink)
    gst.element_link_many(webcam_src, video_rate, rate_caps_filter, webcam_tee)
    gst.element_link_many(webcam_tee, feed_queue, video_sink)
    gst.element_link_many(webcam_tee, capture_queue, ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink)

    return pipeline


def get_framerate(video_src):
    src_pad = video_src.get_pad('src')
    framerate = src_pad.get_caps()[0]['framerate']
    framerate = {'num': framerate.num, 'denom': framerate.denom, }
    return framerate


if __name__ == '__main__':
    pipeline = get_pipeline()
    view = GStreamerVideoView(pipeline)
    window = gtk.Window()
    window.set_size_request(320, 240)
    def on_destroy(widget):
        pipeline.set_state(gst.STATE_NULL)
        gtk.main_quit()
    window.connect('destroy', on_destroy)
    window.add(view.widget)
    window.show_all()
    pipeline.set_state(gst.STATE_PLAYING)

    try:
        gtk.main()
    except KeyboardInterrupt:
        pipeline.set_state(gst.STATE_NULL)
