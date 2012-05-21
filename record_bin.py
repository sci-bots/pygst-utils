import gst


class RecordBin(gst.Bin):
    def __init__(self, name, width=None, height=None):
        super(RecordBin, self).__init__(name)

        ffmpeg_color_space = gst.element_factory_make('ffmpegcolorspace', 'ffmpeg_color_space')
        if width or height:
            # Add videoscale element
            video_scale = gst.element_factory_make('videoscale', 'video_scale')
            video_scale_caps_filter = gst.element_factory_make('capsfilter', 'video_scale_cap')
            if width:
                width_text = ', width=%s' % width
            else:
                width_text = ''
            if height:
                height_text = ', height=%s' % height
            else:
                height_text = ''
            caps_string = 'video/x-raw-yuv%s%s' % (width_text, height_text)
            video_scale_caps_filter.set_property('caps', gst.caps_from_string(
                caps_string))
            
        ffenc_mpeg4 = gst.element_factory_make('ffenc_mpeg4', 'ffenc_mpeg40') 
        ffenc_mpeg4.set_property('bitrate', 1200000)
        avi_mux = gst.element_factory_make('avimux', 'avi_mux')
        file_sink = gst.element_factory_make('filesink', 'file_sink')
        file_sink.set_property('location', 'temp.avi')

        if width or height:
            self.add(ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink,
                    video_scale, video_scale_caps_filter)
            gst.element_link_many(ffmpeg_color_space, video_scale,
                    video_scale_caps_filter, ffenc_mpeg4, avi_mux, file_sink)
        else:
            self.add(ffmpeg_color_space, ffenc_mpeg4, avi_mux, file_sink)
            gst.element_link_many(ffmpeg_color_space, ffenc_mpeg4, avi_mux,
                    file_sink)
        self.sink_gp = gst.GhostPad('sink', ffmpeg_color_space.get_pad('sink'))
        self.add_pad(self.sink_gp)
