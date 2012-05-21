import gst

from warp_perspective import warp_perspective
from cairo_draw import CairoDrawBase


class PlayBin(gst.Bin):
    def __init__(self, name, video_src):
        super(PlayBin, self).__init__(name)

        self.video_src = video_src
        # -- setup video_src --
        video_caps = gst.Caps('video/x-raw-yuv,width=640,height=480,framerate=15/1')
        video_caps_filter = gst.element_factory_make('capsfilter', 'caps_filter')
        video_caps_filter.set_property('caps', video_caps)
        video_tee = gst.element_factory_make('tee', 'video_tee')
        #Feed branch
        feed_queue = gst.element_factory_make('queue', 'feed_queue')
        warp_in_color = gst.element_factory_make('ffmpegcolorspace', 'warp_in_color')
        self.warper = warp_perspective()
        warp_out_color = gst.element_factory_make('ffmpegcolorspace', 'warp_out_color')
        cairo_color_in = gst.element_factory_make('ffmpegcolorspace', 'cairo_color_in')
        cairo_color_out = gst.element_factory_make('ffmpegcolorspace', 'cairo_color_out')
        cairo_draw = CairoDrawBase('cairo_draw')
        video_sink = gst.element_factory_make('autovideosink', 'video_sink')

        video_rate = gst.element_factory_make('videorate', 'video_rate')
        rate_caps = gst.Caps('video/x-raw-yuv,width=640,height=480,framerate=15/1')
        rate_caps_filter = gst.element_factory_make('capsfilter', 'rate_caps_filter')
        rate_caps_filter.set_property('caps', rate_caps)

        capture_queue = gst.element_factory_make('queue', 'capture_queue')

        self.add(video_src, video_caps_filter, video_rate,
                rate_caps_filter, video_tee,

                feed_queue,

                # Elements for drawing cairo overlay on video
                cairo_draw, cairo_color_out, cairo_color_in,

                # Elements for applying OpenCV warp-perspective transformation
                self.warper, warp_in_color, warp_out_color,
                video_sink, capture_queue)

        gst.element_link_many(video_src, video_caps_filter, feed_queue,
                warp_in_color, self.warper, warp_out_color,
                video_rate, rate_caps_filter,
                video_tee,
                cairo_color_in, cairo_draw, cairo_color_out, video_sink)

        video_tee.link(capture_queue)

        # Add ghost 'src' pad 
        self.play_bin_src_gp = gst.GhostPad("src", capture_queue.get_pad('src'))
        self.add_pad(self.play_bin_src_gp)
