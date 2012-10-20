#!/usr/bin/env python

import cgi
import logging
import sys, os
import pygtk, gtk
import time
if os.name == 'nt':
    import win32com
    import pythoncom

import multiprocessing
if hasattr(sys, 'frozen'):
    print 'Enabling multiprocessing freeze support.'
    multiprocessing.freeze_support()
import pkgutil
import platform
import numpy

try:
    import pygst
    pygst.require("0.10")
except ImportError:
    pass
finally:
    import gst
import jsonrpclib
import jsonrpclib.SimpleJSONRPCServer
from jsonrpclib import Server
import blinker
import decimal
from path import path


import pygst_utils
from pygst_utils.video_view.gtk_view import GtkVideoView
from pygst_utils.video_source import GstVideoSourceManager
from pygst_utils.video_pipeline.window_service_proxy import WindowServiceProxy
from pygtkhelpers.ui.extra_widgets import Filepath, Enum, Form
from pygtkhelpers.ui.form_view_dialog import create_form_view
from pygtkhelpers.ui.dialogs import error
from flatland import Integer, String, Boolean
from flatland.validation import ValueAtLeast, ValueAtMost


class GTKGStreamerWindow(object):
    with WindowServiceProxy(port=59000) as w:
        video_mode_map = w.get_video_mode_map()
        video_mode_keys = sorted(video_mode_map.keys())
        device_key, devices = w.get_video_source_configs()

    if not video_mode_keys:
        raise DeviceNotFound

    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title("Mpeg2-Player")
        window.set_default_size(640, 500)
        window.connect("destroy", self.on_destroy)
        vbox = gtk.VBox()
        window.add(vbox)
        hbox = gtk.HBox()
        vbox.pack_start(hbox, expand=False)

        video_mode_enum = Enum.named('video_mode').valued(*self.video_mode_keys)
        form = Form.of(
            video_mode_enum.using(default=self.video_mode_keys[0]),
            Filepath.named('output_path').using(default=''),
            Integer.named('bitrate').using(default=150, validators=[ValueAtLeast(
                    minimum=25)], properties={'step': 25,
                            'label': 'Bitrate (KB/s)', }),
            String.named('transform_string').using(default='1,0,0,0,1,0,0,0,1'),
            Boolean.named('draw_cairo').using(default=False),
        )
        self.video_mode_form_view = create_form_view(form)
        for field in ['video_mode', 'output_path', 'bitrate',
                'transform_string', 'draw_cairo']:
            setattr(self, '%s_field' % field, self.video_mode_form_view.form\
                    .fields[field])
        self.video_mode_field.proxy.connect('changed', self._on_mode_changed)
        self.video_source = None
        hbox.add(self.video_mode_form_view.widget)
        self.button = gtk.Button("Start")
        hbox.pack_start(self.button, False)
        self.button.connect("clicked", self.start_stop)
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=1.0, ratio=4.0 / 3.0,
                obey_child=False)

        self.pipeline = None
        self._proxy = None

        vbox.pack_start(self.aframe, expand=True)
        self.movie_view = GtkVideoView()
        self.movie_window = self.movie_view.widget
        self.aframe.add(self.movie_window)
        window.show_all()
        self.window = window

    @property
    def transform_str(self):
        transform_string = self.video_mode_form_view.form\
                .fields['transform_string'].element.value
        data = [float(v) for v in transform_string.split(',')]
        if len(data) != 9:
            print '''
                Transform string must be 9 comma-separated floats'''.strip()
            return '1,0,0,0,1,0,0,0,1'
        return ','.join(['{}'.format(v) for v in data])

    @property
    def draw_cairo(self):
        return self.video_mode_form_view.form.fields['draw_cairo'].element.value

    @property
    def bitrate(self):
        return (self.video_mode_form_view.form.fields['bitrate'].element.value << 13)

    @property
    def output_path(self):
        return self.video_mode_form_view.form.fields['output_path'].element.value

    @property
    def video_settings(self):
        return self.video_mode_form_view.form.fields['video_mode'].element.value

    def _on_mode_changed(self, *args):
        self.video_settings = self.video_mode_form_view.form.fields[
                'video_mode'].element.value

    @video_settings.setter
    def video_settings(self, value):
        self._video_settings = value

    def get_video_device_and_caps_str(self):
        selected_mode = self.video_mode_map[self.video_settings]
        caps_str = GstVideoSourceManager.get_caps_string(selected_mode)
        return (str(selected_mode['device']), caps_str)

    def start_stop(self, w):
        if self.button.get_label() == "Start":
            self.start()
        else:
            self.stop()

    def start(self):
        if not self.output_path:
            error('Please select a valid output filepath.')
            return
        self.movie_window.set_size_request(640, 480)
        self.aframe.show_all()

        # Use GStreamer WindowServiceProxy to control GStreamer video
        # pipeline.  Behind the scenes, it runs GStreamer in a separate
        # process (subprocess.Popen), exposed through a JSON-RPC
        # interface.
        # There are issues with the GTK gui freezing when the
        # GStreamer pipeline is started here directly.
        from pygst_utils.elements.draw_queue import get_example_draw_queue
        if self.draw_cairo:
            print 'using draw_queue'
            x, y, width, height = self.movie_window.get_allocation()
            draw_queue = get_example_draw_queue(width, height)
        else:
            print 'NOT using draw_queue'
            draw_queue = None
        self._proxy = WindowServiceProxy(port=59000)

        try:
            self._proxy.window_xid(self.movie_view.window_xid)
            device, caps_str = self.get_video_device_and_caps_str()
            self._proxy.create(device, caps_str, record_path=self.output_path,
                    bitrate=self.bitrate, draw_queue=draw_queue, with_warp=True,
                    with_scale=True)
            self._proxy.set_warp_transform(self.transform_str)
            self._proxy.start()
            self._proxy.scale(width, height)
        except (Exception, ), why:
            print why
            self.stop()
            return

        self.video_mode_field.proxy.widget.set_button_sensitivity(gtk.SENSITIVITY_OFF)
        self.transform_string_field.widget.set_sensitive(False)
        self.output_path_field.widget.set_sensitive(False)
        self.bitrate_field.widget.set_sensitive(False)

        self.button.set_label("Stop")

    def stop(self):
        self._proxy.stop()
        self._proxy.close()
        # Terminate GStreamer service server
        self._proxy = None
        self.button.set_label("Start")
        self.video_mode_field.proxy.widget.set_button_sensitivity(gtk.SENSITIVITY_AUTO)
        self.transform_string_field.widget.set_sensitive(True)
        self.output_path_field.widget.set_sensitive(True)
        self.bitrate_field.widget.set_sensitive(True)

    def on_destroy(self, *args):
        if self._proxy:
            self.stop()
        gtk.main_quit()


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', loglevel=logging.DEBUG)
    GTKGStreamerWindow()
    gtk.main()
