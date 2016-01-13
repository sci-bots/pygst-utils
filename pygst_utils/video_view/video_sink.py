from datetime import datetime
import logging
import sys

from dmf_device_ui.options import DebugView
from pygtkhelpers.delegates import SlaveView
from pygtkhelpers.ui.views.cairo_view import GtkCairoView
from pygtkhelpers.utils import gsignal
import cairo
import cv2
import gobject
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


class VideoSink(SlaveView):
    gsignal('frame-rate-update', float, int)
    gsignal('frame-update', object)

    def __init__(self, transport, target_host, port=None):
        self.status = {}
        super(VideoSink, self).__init__()
        self.socket_info = {'host': target_host,
                            'port': port,
                            'transport': transport}
        self.video_timeout_id = None
        self._transform = np.identity(3, dtype='float32')
        self._shape = None
        self.frame_shape = None

    @property
    def transform(self):
        return self._transform

    @transform.setter
    def transform(self, value):
        self._transform = value

    @property
    def shape(self):
        if self._shape is not None:
            return self._shape
        elif 'np_warped_view' in self.status:
            return self.status['np_warped_view'].shape[:2]

    @shape.setter
    def shape(self, value):
        logging.info('[VideoSink] shape=%s', value)
        self._shape = value
        self.frame_shape = None

    def reset(self):
        if self.video_timeout_id is not None:
            gobject.remove_source(self.video_timeout_id)
        self.ctx = zmq.Context.instance()
        self.target_socket = zmq.Socket(self.ctx, zmq.PULL)
        base_uri = '%s://%s' % (self.socket_info['transport'],
                                self.socket_info['host'])
        port = self.socket_info['port']
        if port is None:
            port = self.target_socket.bind_to_random_port(base_uri)
            uri = '%s:%s' % (base_uri, port)
        else:
            uri = '%s:%s' % (base_uri, port)
            self.target_socket.bind(uri)
        self.socket_info['port'] = port
        logger.info('Listening on: %s', uri)

        status = {'frame_count': 0, 'dropped_count': 0, 'start_time':
                  datetime.now()}
        self.status = status
        self.video_timeout_id = gtk.timeout_add(20, self.check_sockets, status)

    def check_sockets(self, status):
        buf_str = None
        frame_count = 0
        while True:
            try:
                shape_str, buf_str = (self.target_socket
                                      .recv_multipart(zmq.NOBLOCK))
                frame_count += 1
            except zmq.Again:
                break
        status['dropped_count'] += frame_count - 1 if frame_count > 0 else 0
        status['frame_count'] += frame_count
        status['buf_str'] = buf_str
        status['duration'] = (datetime.now() -
                              status['start_time']).total_seconds()

        if buf_str is not None:
            self.prepare_np_frame(shape_str, buf_str)

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

    def prepare_np_frame(self, shape_str, buf_str):
        '''
        Convert raw frame buffer to numpy array and apply warp perspective
        transformation.

        Emits:

            frame-update : New numpy video frame available with perspective
                transform applied.
        '''
        height, width, channels = np.frombuffer(shape_str, count=3,
                                                dtype='uint32')
        im_buf = np.frombuffer(buf_str, dtype='uint8',
                               count=len(buf_str)).reshape(height, width, -1)

        # Cairo surface seems to use BGR ordering, so convert frame color.
        np_bgr = cv2.cvtColor(im_buf, cv2.COLOR_RGB2BGR)

        # Warp and scale
        if self.frame_shape != (width, height):
            # Frame shape has changed.
            self.frame_shape = width, height
            if self.shape is None:
                # No target shape has been set.  Use frame size.
                self.scaled_transform = self.transform
                self.shape = self.frame_shape
                print self.scaled_transform
            else:
                # Update transform to scale to target shape.
                self.scaled_transform = self.transform.copy()
                scale = np.array(self.shape, dtype=float) / self.frame_shape
                for i in xrange(2):
                    self.scaled_transform[i, i] *= scale[i]
                print self.scaled_transform
        np_warped = cv2.warpPerspective(np_bgr, self.scaled_transform,
                                        self.shape)
        self.emit('frame-update', np_warped)


class VideoView(GtkCairoView):
    def __init__(self, transport, target_host, port=None):
        self.socket_info = {'transport': transport,
                            'host': target_host,
                            'port': port}
        super(VideoView, self).__init__()

    def on_widget__configure_event(self, widget, event):
        self.video_sink.shape = event.width, event.height

    def create_ui(self):
        self.video_sink = VideoSink(*[self.socket_info[k]
                                      for k in ['transport', 'host', 'port']])
        self.video_sink.reset()
        self.video_sink.connect('frame-update', self.on_frame_update)
        self.surfaces = self.get_surfaces()
        super(VideoView, self).create_ui()

    def on_frame_update(self, slave, np_frame):
        if self.widget.window is None:
            return
        cr_warped, np_warped_view = np_to_cairo(np_frame)

        combined_surface = self.composite_surface([cr_warped] + self.surfaces)
        self.draw_surface(combined_surface)

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
        x, y, width, height = self.widget.get_allocation()
        if width <= 0 and height <= 0:
            return
        cairo_context = self.widget.window.cairo_create()
        cairo_context.set_operator(operator)
        cairo_context.set_source_surface(surface)
        cairo_context.rectangle(x, y, width, height)
        cairo_context.fill()


class View(SlaveView):
    def __init__(self, transport, target_host, port=None):
        self.socket_info = {'transport': transport,
                            'host': target_host,
                            'port': port}
        super(View, self).__init__()

    def create_ui(self):
        super(View, self).create_ui()
        self.debug_slave = self.add_slave(DebugView(), 'widget')
        self.info_slave = self.add_slave(VideoInfo(), 'widget')
        video_view = VideoView(*[self.socket_info[k]
                                 for k in ['transport', 'host', 'port']])
        self.video_slave = self.add_slave(video_view, 'widget')

        for widget in (self.debug_slave.widget, self.info_slave.widget):
            self.widget.set_child_packing(widget, False, False, 0,
                                          gtk.PACK_START)

        self.widget.set_child_packing(self.video_slave.widget, True, True, 0,
                                      gtk.PACK_START)
        self.video_slave.video_sink.connect('frame-rate-update',
                                            self.on_frame_rate_update)

    def on_frame_rate_update(self, slave, frame_rate, dropped_frames):
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

    view = View(args.transport, args.host, args.port)

    #gtk.timeout_add(1000, view.debug)
    view.widget.connect('destroy', gtk.main_quit)
    view.show_and_run()
