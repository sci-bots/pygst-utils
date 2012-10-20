import platform
try:
    import cPickle as pickle
except ImportError:
    import pickle

import gst
import gtk
gtk.gdk.threads_init()

# this is very important, without this, callbacks from gstreamer thread
# will messed our program up
import gobject
gobject.threads_init()

from pygst_utils.elements.cairo_draw import CairoDrawBase, CairoDrawQueue
from pygst_utils.elements.draw_queue import DrawQueue
from pygst_utils.elements.warp_perspective import WarpBin, grab_frame


def get_pipeline(video_source, bitrate=None, output_path=None, draw_queue=None,
            with_scale=False, with_warp=False, on_frame_grabbed=None):
    pipeline = gst.Pipeline('pipeline')

    pipeline.add(video_source)
    video_source.set_state(gst.STATE_READY)

    video_rate = gst.element_factory_make('videorate', 'video_rate')

    video_tee = gst.element_factory_make('tee', 'video_tee')
    pipeline.add(video_rate, video_tee)
    gst.element_link_many(video_source, video_rate, video_tee)

    display_queue = gst.element_factory_make('queue', 'display_queue')
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    pipeline.add(display_queue, video_sink)

    gst.element_link_many(video_tee, display_queue)
    display_pre_sink = display_queue

    if on_frame_grabbed:
        grab_frame_color_in = gst.element_factory_make('ffmpegcolorspace',
                'grab_frame_color_in')
        grab_frame_ = grab_frame('grab_frame', on_frame_grabbed)
        grab_frame_color_out= gst.element_factory_make('ffmpegcolorspace',
                'grab_frame_color_out')
        pipeline.add(grab_frame_color_in, grab_frame_, grab_frame_color_out)
        gst.element_link_many(display_pre_sink, grab_frame_color_in,
                grab_frame_, grab_frame_color_out)
        display_pre_sink = grab_frame_color_out

    if with_scale:
        video_scale = gst.element_factory_make('videoscale', 'video_scale')
        caps_filter = gst.element_factory_make('capsfilter', 'video_scale_caps_filter')
        pipeline.add(video_scale, caps_filter)
        gst.element_link_many(display_pre_sink, video_scale, caps_filter)
        display_pre_sink = caps_filter

    if with_warp:
        warp_bin = WarpBin('warp_bin')
        pipeline.add(warp_bin)
        gst.element_link_many(display_pre_sink, warp_bin)
        display_pre_sink = warp_bin

    if draw_queue:
        cairo_color_in = gst.element_factory_make('ffmpegcolorspace',
                'cairo_color_in')
        cairo_draw = CairoDrawQueue('cairo_draw')
        cairo_draw.set_property('draw-queue', pickle.dumps(draw_queue))
        cairo_color_out = gst.element_factory_make('ffmpegcolorspace',
                'cairo_color_out')
        pipeline.add(cairo_color_in, cairo_draw, cairo_color_out)
        gst.element_link_many(display_pre_sink, cairo_color_in, cairo_draw,
                cairo_color_out)
        display_pre_sink = cairo_color_out

    gst.element_link_many(display_pre_sink, video_sink)

    if bitrate and output_path:
        capture_queue = gst.element_factory_make('queue', 'capture_queue')
        capture_color_in = gst.element_factory_make('ffmpegcolorspace', 'ffmpeg_color_space')
        if platform.system() == 'Linux':
            ffenc_mpeg4 = gst.element_factory_make('ffenc_mpeg4', 'ffenc_mpeg40')
        else:
            ffenc_mpeg4 = gst.element_factory_make('xvidenc', 'ffenc_mpeg40')
        ffenc_mpeg4.set_property('bitrate', bitrate)
        avi_mux = gst.element_factory_make('avimux', 'avi_mux')
        file_sink = gst.element_factory_make('filesink', 'file_sink')
        file_sink.set_property('location', output_path)
        pipeline.add(capture_queue, capture_color_in, ffenc_mpeg4, avi_mux,
                file_sink)
        gst.element_link_many(video_tee, capture_queue, capture_color_in,
                ffenc_mpeg4, avi_mux, file_sink)
    return pipeline


def get_framerate(video_src):
    src_pad = video_src.get_pad('src')
    framerate = src_pad.get_caps()[0]['framerate']
    framerate = {'num': framerate.num, 'denom': framerate.denom, }
    return framerate
