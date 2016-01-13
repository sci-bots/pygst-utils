from datetime import datetime
import logging
import sys

from dmf_device_ui.options import DebugView
from pygtkhelpers.delegates import SlaveView
from pygtkhelpers.ui.views.cairo_view import GtkCairoView
from pygtkhelpers.utils import gsignal
import cairo
import cv2
import gtk
import numpy as np
import zmq

from . import np_to_cairo

logger = logging.getLogger(__name__)


class VideoInfo(SlaveView):
    def create_ui(self):
        super(VideoInfo, self).create_ui()
        self.widget.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        self.label_tag_fps = gtk.Label('Frames per second:')
        self.label_fps = gtk.Label()
        self.label_tag_dropped_frames = gtk.Label('  Dropped frames:')
        self.label_dropped_frames = gtk.Label()
        self.widget.pack_start(self.label_tag_fps, False, False)
        self.widget.pack_start(self.label_fps, False, False)
        self.widget.pack_start(self.label_tag_dropped_frames, False, False)
        self.widget.pack_start(self.label_dropped_frames, False, False)

        self.frames_per_second = 0
        self.dropped_frames = 0

    @property
    def frames_per_second(self):
        return float(self.label_fps.get_text())

    @frames_per_second.setter
    def frames_per_second(self, value):
        self.label_fps.set_text('%.1f' % float(value))

    @property
    def dropped_frames(self):
        return int(self.label_dropped_frames.get_text())

    @dropped_frames.setter
    def dropped_frames(self, value):
        self.label_dropped_frames.set_text('%d' % int(value))


class VideoSink(GtkCairoView):
    gsignal('frame-rate-update', float, int)
    gsignal('frame-update', )

    def __init__(self):
        self.status = {}
        super(VideoSink, self).__init__()
        self._shape = None
        self.surfaces = self.get_surfaces()

    @property
    def shape(self):
        if self._shape is not None:
            return self._shape
        elif 'np_warped_view' in self.status:
            return self.status['np_warped_view']

    def schedule_video_updates(self, transport, target_host, port=None,
                               log_level=None):
        if log_level is not None:
            logging.basicConfig(level=log_level)

        self.ctx = zmq.Context.instance()
        self.target_socket = zmq.Socket(self.ctx, zmq.PULL)
        base_uri = '%s://%s' % (transport, target_host)
        if port is None:
            port = self.target_socket.bind_to_random_port(base_uri)
            uri = '%s:%s' % (base_uri, port)
        else:
            uri = '%s:%s' % (base_uri, port)
            self.target_socket.bind(uri)
        logger.info('Listening on: %s', uri)

        status = {'frame_count': 0, 'dropped_count': 0, 'start_time':
                  datetime.now()}
        self.status = status
        self.video_timeout_id = gtk.timeout_add(10, self.update_status, status)

    def update_status(self, status):
        buf_str = None
        frame_count = 0
        while True:
            try:
                shape, buf_str = self.target_socket.recv_multipart(zmq.NOBLOCK)
                frame_count += 1
            except zmq.Again:
                break
        status['dropped_count'] += frame_count - 1 if frame_count > 0 else 0
        status['frame_count'] += frame_count
        status['buf_str'] = buf_str
        status['duration'] = (datetime.now() -
                              status['start_time']).total_seconds()

        if buf_str is not None:
            gtk.idle_add(self.render_base_surface, status, shape, buf_str)

        if status['duration'] > 2:
            status['fps'] = status['frame_count'] / status['duration']
            print '\r%5.1f frames/second (%2d dropped)' % (status['fps'],
                                                        status
                                                        ['dropped_count']),
            self.emit('frame-rate-update', status['fps'],
                      status['dropped_count'])
            status['frame_count'] = 0
            status['dropped_count'] = 0
            status['start_time'] = datetime.now()
        return True

    def render_base_surface(self, status, shape, buf_str):
        np_transform = np.identity(3, dtype='float32')
        height, width, channels = np.frombuffer(shape, count=3,
                                                dtype='uint32')
        im_buf = np.frombuffer(buf_str, dtype='uint8',
                               count=len(buf_str)).reshape(height, width, -1)

        x, y, canvas_width, canvas_height = self.widget.get_allocation()
        transform = np.identity(3, dtype='float32')
        transform[0, 0] = canvas_width / float(width)
        transform[1, 1] = canvas_height / float(height)
        np_transform *= transform

        np_bgr = cv2.cvtColor(im_buf, cv2.COLOR_RGB2BGR)
        np_warped = cv2.warpPerspective(np_bgr, np_transform, (canvas_width,
                                                               canvas_height))
        cr_warped, np_warped_view = np_to_cairo(np_warped)
        status['cr_warped'] = cr_warped
        status['np_warped_view'] = np_warped_view

        combined_surface = self.composite_surface([cr_warped] + self.surfaces)
        self.draw_surface(combined_surface)
        return False

    def draw_to_widget_surface(self, surface):
        x, y, width, height = self.widget.get_allocation()
        gtk_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        surface_context = cairo.Context(gtk_surface)
        surface_context.scale(float(width) / surface.get_width(),
                              float(height) / surface.get_height())
        surface_context.set_source_surface(surface)
        surface_context.rectangle(0, 0, surface.get_width(),
                                  surface.get_height())
        surface_context.fill()
        return gtk_surface

    def composite_surface(self, surfaces, op=cairo.OPERATOR_OVER):
        max_width = max([s.get_width() for s in surfaces])
        max_height = max([s.get_height() for s in surfaces])

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, max_width,
                                     max_height)
        surface_context = cairo.Context(surface)

        for surface_i in surfaces:
            surface_context.set_operator(op)
            surface_context.set_source_surface(surface_i)
            surface_context.rectangle(0, 0, surface_i.get_width(),
                                      surface_i.get_height())
            surface_context.fill()
        return surface

    def get_surfaces(self):
        surface1 = cairo.ImageSurface(cairo.FORMAT_ARGB32, 320, 240)
        surface1_context = cairo.Context(surface1)
        surface1_context.set_source_rgba(0, 0, 1, .5)
        surface1_context.rectangle(0, 0, surface1.get_width(), surface1.get_height())
        surface1_context.fill()

        surface2 = cairo.ImageSurface(cairo.FORMAT_ARGB32, 800, 600)
        surface2_context = cairo.Context(surface2)
        surface2_context.save()
        surface2_context.translate(100, 200)
        surface2_context.set_source_rgba(0, 1, .5, .5)
        surface2_context.rectangle(0, 0, surface1.get_width(), surface1.get_height())
        surface2_context.fill()
        surface2_context.restore()

        return [surface1, surface2]

    def draw_surface(self, surface, operator=cairo.OPERATOR_OVER):
        cairo_context = self.widget.window.cairo_create()
        cairo_context.set_operator(operator)
        cairo_context.set_source_surface(surface)
        x, y, width, height = self.widget.get_allocation()
        cairo_context.rectangle(x, y, width, height)
        cairo_context.fill()


class View(SlaveView):
    def create_ui(self):
        super(View, self).create_ui()
        self.debug_slave = self.add_slave(DebugView(), 'widget')
        self.info_slave = self.add_slave(VideoInfo(), 'widget')
        self.video_slave = self.add_slave(VideoSink(), 'widget')

        for widget in (self.debug_slave.widget, self.info_slave.widget):
            self.widget.set_child_packing(widget, False, False, 0,
                                          gtk.PACK_START)

        self.widget.set_child_packing(self.video_slave.widget, True, True, 0,
                                      gtk.PACK_START)

    def on_video_slave__frame_rate_update(self, slave, frame_rate,
                                          dropped_frames):
        self.info_slave.frames_per_second = frame_rate
        self.info_slave.dropped_frames += dropped_frames



def parse_args(args=None):
    """Parses arguments, returns (options, args)."""
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='GStreamer to ZeroMQ socket.')
    log_levels = ('critical', 'error', 'warning', 'info', 'debug', 'notset')
    parser.add_argument('-l', '--log-level', type=str, choices=log_levels,
                        default='info')
    parser.add_argument('transport')
    parser.add_argument('host')
    parser.add_argument('-p', '--port', default=None)

    args = parser.parse_args()
    args.log_level = getattr(logging, args.log_level.upper())
    return args


if __name__ == '__main__':
    args = parse_args()

    logging.basicConfig(level=args.log_level)
    #run_video_sink(args.transport, args.host, port=args.port,
                   #log_level=args.log_level)

    view = View()
    view.video_slave.schedule_video_updates(args.transport, args.host,
                                            args.port, args.log_level)

    #gtk.timeout_add(1000, view.debug)
    view.widget.connect('destroy', gtk.main_quit)
    view.show_and_run()
