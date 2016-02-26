from subprocess import Popen
from datetime import datetime
import logging
import sys

from cairo_helpers.surface import composite_surface
from dmf_device_ui.options import DebugView
from pygtkhelpers.delegates import SlaveView
from pygtkhelpers.ui.views.cairo_view import GtkCairoView
from pygtkhelpers.utils import gsignal, refresh_gui
import cairo
import cv2
import gobject
import gtk
import numpy as np
import pandas as pd
import zmq

from .mode import VideoModeSelector
from . import np_to_cairo

logger = logging.getLogger(__name__)


class Transform(SlaveView):
    gsignal('transform-reset')
    gsignal('transform-rotate-left')
    gsignal('transform-rotate-right')
    gsignal('transform-modify-toggled', bool)

    def __init__(self, transform=None):
        self.transform = (np.eye(3, dtype=float) if transform is None
                          else transform)
        super(Transform, self).__init__()

    def create_ui(self):
        super(Transform, self).create_ui()
        self.widget.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        self.label_tag_transform = gtk.Label('Transform: ')
        self.button_rotate_left = gtk.Button('Rotate left')
        self.button_rotate_right = gtk.Button('Rotate right')
        self.button_reset = gtk.Button('Reset')
        self.button_modify = gtk.CheckButton('Modify')

        for widget in (self.label_tag_transform, self.button_rotate_left,
                       self.button_rotate_right, self.button_reset,
                       self.button_modify):
            self.widget.pack_start(widget, False, False, 0)

    def on_button_reset__clicked(self, button):
        self.emit('transform-reset')

    def on_button_rotate_left__clicked(self, button):
        self.emit('transform-rotate-left')

    def on_button_rotate_right__clicked(self, button):
        self.emit('transform-rotate-right')

    def on_button_modify__toggled(self, button):
        self.emit('transform-modify-toggled', self.modify)

    @property
    def modify(self):
        return self.button_modify.get_active()


class VideoInfo(SlaveView):
    def create_ui(self):
        super(VideoInfo, self).create_ui()
        self.widget.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        self.label_tag_fps = gtk.Label('FPS: ')
        self.label_fps = gtk.Label()
        self.label_tag_dropped_rate = gtk.Label('  Dropped/s: ')
        self.label_dropped_rate = gtk.Label()
        self.widget.pack_start(self.label_tag_fps, False, False)
        self.widget.pack_start(self.label_fps, False, False)
        self.widget.pack_start(self.label_tag_dropped_rate, False, False)
        self.widget.pack_start(self.label_dropped_rate, False, False)

        self.frames_per_second = 0
        self.dropped_rate = 0

    @property
    def frames_per_second(self):
        return float(self.label_fps.get_text())

    @frames_per_second.setter
    def frames_per_second(self, value):
        self.label_fps.set_text('%.1f' % float(value))

    @property
    def dropped_rate(self):
        return float(self.label_dropped_rate.get_text())

    @dropped_rate.setter
    def dropped_rate(self, value):
        self.label_dropped_rate.set_text('%.1f' % float(value))


class VideoSink(SlaveView):
    gsignal('frame-rate-update', float, float)
    gsignal('frame-update', object)
    gsignal('frame-shape-changed', object, object)
    gsignal('transform-changed', object)

    def __init__(self, transport, target_host, port=None):
        self.status = {}
        super(VideoSink, self).__init__()
        self.socket_info = {'host': target_host,
                            'port': port,
                            'transport': transport}
        self.video_timeout_id = None
        self.frame_shape = None
        self._transform = np.identity(3, dtype='float32')
        self.shape = None
        self._check_duration = 50

    @property
    def transform(self):
        return self._transform

    @transform.setter
    def transform(self, value):
        self._transform = value
        self.emit('transform-changed', value)

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
        self.video_timeout_id = gtk.timeout_add(self._check_duration,
                                                self.check_sockets, status)

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
            #print '\r%5.1f frames/second (%2d dropped)' % (status['fps'],
                                                           #status
                                                           #['dropped_count']),
            self.emit('frame-rate-update', status['fps'],
                      status['dropped_count'] / status['duration'])
            if status['dropped_count'] > 0:
                gobject.source_remove(self.video_timeout_id)
                new_check_duration = .95e3 / status['fps']
                self._check_duration = int(new_check_duration)
                self.video_timeout_id = gtk.timeout_add(self._check_duration,
                                                        self.check_sockets,
                                                        status)
            elif status['frame_count'] > 0:
                gobject.source_remove(self.video_timeout_id)
                new_check_duration = 1.05 * self._check_duration
                self._check_duration = int(new_check_duration)
                self.video_timeout_id = gtk.timeout_add(self._check_duration,
                                                        self.check_sockets,
                                                        status)
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

        # Warp and scale
        if self.frame_shape != (width, height):
            # Frame shape has changed.
            old_frame_shape = self.frame_shape
            self.frame_shape = width, height
            self.emit('frame-shape-changed', old_frame_shape, self.frame_shape)
            if self.shape is None:
                self.shape = width, height
        np_warped = cv2.warpPerspective(im_buf, self.transform, self.shape)
        self.emit('frame-update', np_warped)


class VideoView(GtkCairoView):
    gsignal('point-pair-selected', object)
    gsignal('video-enabled')
    gsignal('video-disabled')

    def __init__(self, transport, target_host, port=None):
        self.socket_info = {'transport': transport,
                            'host': target_host,
                            'port': port}
        self.callback_id = None
        self._enabled = False
        self.start_event = None
        self.df_canvas_corners = pd.DataFrame(None, columns=['x', 'y'],
                                              dtype=float)
        self.df_frame_corners = pd.DataFrame(None, columns=['x', 'y'],
                                             dtype=float)
        self.frame_to_canvas_map = None
        self.canvas_to_frame_map = None
        self.shape = None
        super(VideoView, self).__init__()

    def reset_canvas_corners(self):
        if self.shape is None:
            return
        width, height = self.shape
        self.df_canvas_corners = pd.DataFrame([[0, 0], [width, 0],
                                               [width, height], [0, height]],
                                              columns=['x', 'y'], dtype=float)

    def reset_frame_corners(self):
        if self.video_sink.frame_shape is None:
            return
        width, height = self.video_sink.frame_shape
        self.df_frame_corners = pd.DataFrame([[0, 0], [width, 0],
                                              [width, height], [0, height]],
                                              columns=['x', 'y'], dtype=float)

    def update_transforms(self):
        import cv2

        if (self.df_canvas_corners.shape[0] <= 0 or
            self.df_frame_corners.shape[0] <= 0):
            return

        self.canvas_to_frame_map = cv2.findHomography(self.df_canvas_corners
                                                      .values,
                                                      self.df_frame_corners
                                                      .values)[0]
        self.frame_to_canvas_map = cv2.findHomography(self.df_frame_corners
                                                      .values,
                                                      self.df_canvas_corners
                                                      .values)[0]
        self.video_sink.transform = self.frame_to_canvas_map

    def create_ui(self):
        self.video_sink = VideoSink(*[self.socket_info[k]
                                      for k in ['transport', 'host', 'port']])
        self.video_sink.reset()
        self.surfaces = self.get_surfaces()
        super(VideoView, self).create_ui()
        self.widget.set_events(gtk.gdk.BUTTON_PRESS |
                               gtk.gdk.BUTTON_RELEASE |
                               gtk.gdk.BUTTON_MOTION_MASK |
                               gtk.gdk.BUTTON_PRESS_MASK |
                               gtk.gdk.BUTTON_RELEASE_MASK |
                               gtk.gdk.POINTER_MOTION_MASK)

    ###########################################################################
    # ## Properties ##
    @property
    def enabled(self):
        return self._enabled

    ###########################################################################
    # ## Mutators ##
    def enable(self):
        if self.callback_id is None:
            self.callback_id = self.video_sink.connect('frame-update',
                                                       self.on_frame_update)
            self._enabled = True
            self.emit('video-enabled')

    def disable(self):
        if self.callback_id is not None:
            self.video_sink.disconnect(self.callback_id)
            self.callback_id = None
            self._enabled = False
            self.emit('video-disabled')
        gtk.idle_add(self.on_frame_update, None, None)

    ###########################################################################
    # ## Mouse event handling ##
    def on_widget__button_press_event(self, widget, event):
        '''
        Called when any mouse button is pressed.
        '''
        if event.button == 1:
            self.start_event = event.copy()

    def on_widget__button_release_event(self, widget, event):
        '''
        Called when any mouse button is released.
        '''
        if event.button == 1 and self.start_event is not None:
            self.emit('point-pair-selected', {'start_event': self.start_event,
                                              'end_event': event.copy()})
            self.start_event = None

    def on_widget__configure_event(self, widget, event):
        '''
        Handle resize of Cairo drawing area.
        '''
        # Set new target size for scaled frames from video sink.
        width, height = event.width, event.height
        self.shape = width, height
        self.video_sink.shape = width, height
        self.reset_canvas_corners()
        self.update_transforms()
        if not self._enabled:
            gtk.idle_add(self.on_frame_update, None, None)

    ###########################################################################
    # ## Slave signal handling ##
    def on_video_sink__frame_shape_changed(self, slave, shape):
        # Video frame is a new shape.
        self.reset_frame_corners()
        self.update_transforms()

    def on_frame_update(self, slave, np_frame):
        if self.widget.window is None:
            return
        if np_frame is None:
            cr_warped = cairo.ImageSurface(cairo.FORMAT_RGB24, *self.shape)
        else:
            cr_warped, np_warped_view = np_to_cairo(np_frame)
            if not self._enabled:
                logging.error('got frame when not enabled')
        refresh_gui(0, 0)

        combined_surface = composite_surface([cr_warped] + self.surfaces)
        refresh_gui(0, 0)
        self.draw_surface(combined_surface)

    ###########################################################################
    # ## Drawing methods ##
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
        if width <= 0 and height <= 0 or self.widget.window is None:
            return
        cairo_context = self.widget.window.cairo_create()
        cairo_context.set_operator(operator)
        cairo_context.set_source_surface(surface)
        cairo_context.rectangle(0, 0, width, height)
        cairo_context.fill()


class View(SlaveView):
    def __init__(self, transport, target_host, port=None):
        self.socket_info = {'transport': transport,
                            'host': target_host,
                            'port': port}
        self.video_source_process = None
        super(View, self).__init__()

    def cleanup(self):
        if self.video_source_process is not None:
            self.video_source_process.terminate()
            logger.info('terminate video process')

    def __del__(self):
        self.cleanup()

    def on_widget__destroy(self, widget):
        self.cleanup()

    def create_ui(self):
        super(View, self).create_ui()
        self.debug_slave = self.add_slave(DebugView(), 'widget')
        self.video_mode_slave = self.add_slave(VideoModeSelector(), 'widget')
        self.info_slave = self.add_slave(VideoInfo(), 'widget')
        self.transform_slave = self.add_slave(Transform(), 'widget')
        self.transform_slave.widget.set_sensitive(False)
        video_view = VideoView(*[self.socket_info[k]
                                 for k in ['transport', 'host', 'port']])
        self.video_slave = self.add_slave(video_view, 'widget')

        for widget in (self.debug_slave.widget, self.video_mode_slave.widget,
                       self.transform_slave.widget, self.info_slave.widget):
            self.widget.set_child_packing(widget, False, False, 0,
                                          gtk.PACK_START)

        self.widget.set_child_packing(self.video_slave.widget, True, True, 0,
                                      gtk.PACK_START)
        self.video_slave.video_sink.connect('frame-rate-update',
                                            self.on_frame_rate_update)

    ###########################################################################
    # ## Slave signal handling ##
    def on_transform_slave__transform_reset(self, slave):
        logger.info('[View] reset transform')
        self.video_slave.reset_canvas_corners()
        self.video_slave.reset_frame_corners()
        self.video_slave.update_transforms()

    def on_transform_slave__transform_rotate_left(self, slave):
        self.video_slave.df_canvas_corners[:] = np.roll(self.video_slave
                                                        .df_canvas_corners.values,
                                                        1, axis=0)
        self.video_slave.update_transforms()

    def on_transform_slave__transform_rotate_right(self, slave):
        self.video_slave.df_canvas_corners[:] = np.roll(self.video_slave
                                                        .df_canvas_corners.values,
                                                        -1, axis=0)
        self.video_slave.update_transforms()

    def on_video_mode_slave__video_config_selected(self, slave, video_config):
        if video_config is None:
            self.cleanup()
            self.video_slave.disable()
            return
        caps_str = ('video/x-raw-rgb,width={width:d},height={height:d},'
                    'format=RGB,'
                    'framerate={framerate_num:d}/{framerate_denom:d}'
                    .format(**video_config))
        logging.info('[View] video config caps string: %s', caps_str)
        py_exe = sys.executable
        port = self.video_slave.video_sink.socket_info['port']
        transport = self.video_slave.video_sink.socket_info['transport']
        host = self.video_slave.video_sink.socket_info['host'].replace('*',
                                                                       'localhost')
        # Terminate existing process (if running).
        self.cleanup()
        command = [py_exe, '-m', 'pygst_utils.video_view.video_source', '-p',
                   str(port), transport, host,
                   'autovideosrc ! ffmpegcolorspace ! ' + caps_str +
                   ' ! videorate ! appsink name=app-video emit-signals=true']
        logger.info(' '.join(command))
        self.video_source_process = Popen(command)
        self.video_source_process.daemon = True
        self.video_slave.enable()

    def on_frame_rate_update(self, slave, frame_rate, dropped_rate):
        self.info_slave.frames_per_second = frame_rate
        self.info_slave.dropped_rate = dropped_rate

    def on_video_slave__point_pair_selected(self, slave, data):
        if not self.transform_slave.modify or not self.video_slave.enabled:
            return
        start_xy = [getattr(data['start_event'], k) for k in 'xy']
        end_xy = [getattr(data['end_event'], k) for k in 'xy']
        logger.debug('[View] point pair selected: %s, %s', start_xy, end_xy)

        slave = self.video_slave
        # Map GTK event x/y coordinates to the video frame coordinate space.
        frame_point_i = \
            cv2.perspectiveTransform(np.array([[start_xy]], dtype=float),
                                     slave.canvas_to_frame_map).ravel()
        # Find the closest corner point in the frame to the starting point.
        frame_corner_i = find_closest(slave.df_frame_corners, frame_point_i)
        # Find the closest corner point in the canvas to the end point.
        canvas_corner_i = find_closest(slave.df_canvas_corners, end_xy)
        # Replace the corresponding corner point coordinates with the
        # respective new points.
        slave.df_frame_corners.iloc[frame_corner_i.name] = frame_point_i
        slave.df_canvas_corners.iloc[canvas_corner_i.name] = end_xy
        slave.update_transforms()

    def on_video_slave__video_disabled(self, slave):
        self.transform_slave.widget.set_sensitive(False)

    def on_video_slave__video_enabled(self, slave):
        self.transform_slave.widget.set_sensitive(True)


def find_closest(df_points, point):
    return df_points.iloc[((df_points - point) ** 2).sum(axis=1).argmin()]


def parse_args(args=None):
    """Parses arguments, returns (options, args)."""
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='GStreamer to ZeroMQ socket.')
    log_levels = ('critical', 'error', 'warning', 'info', 'debug', 'notset')
    parser.add_argument('-l', '--log-level', type=str, choices=log_levels,
                        default='info')
    parser.add_argument('transport', nargs='?', default='tcp')
    parser.add_argument('host', nargs='?', default='*')
    parser.add_argument('-p', '--port', default=None, type=int)

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
