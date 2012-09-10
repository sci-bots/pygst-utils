#!/usr/bin/env python

import cgi
import logging
import sys, os
import pygtk, gtk, gobject
from subprocess import Popen, PIPE
import time
if os.name == 'nt':
    import win32com
    import pythoncom

try:
    import pygst
    pygst.require("0.10")
except ImportError:
    pass
finally:
    import gst
import gobject
from jsonrpclib import Server
import blinker
import decimal
from path import path

from warp_perspective import warp_perspective, WarpBin
from gstreamer_view import GStreamerVideoView
from test_pipeline_process import PipelineWindowProcess
from rated_bin import RatedBin
from gst_video_source_caps_query.gst_video_source_caps_query import\
        DeviceNotFound, GstVideoSourceManager, FilteredInput
from gst_video_source_caps_query.video_mode_dialog import\
        FormViewDialog, create_form_view, get_video_mode_form,\
        get_video_mode_map, create_video_source, get_video_mode_enum,\
        get_available_video_modes, get_video_source_configs
from test_video import get_pipeline
from pygtkhelpers.ui.extra_widgets import Filepath
from pygtkhelpers.ui.dialogs import error
from flatland import Form, Integer
from flatland.validation import ValueAtLeast, ValueAtMost


#gst.debug_set_active(True)
#gst.debug_set_default_threshold(3)


def base_path():
    # When executing from a frozen (pyinstaller) executable...
    if hasattr(sys, 'frozen'):
        return path(sys.executable).parent

    # Otherwise...
    try:
        script = path(__file__)
    except NameError:
        script = path(sys.argv[0])
    return script.parent.parent


class GTK_Main:
    try:
        video_modes = get_available_video_modes(
                format_='YUY2')
        video_mode_map = get_video_mode_map(video_modes)
        video_mode_keys = sorted(video_mode_map.keys())
        device_key, devices = get_video_source_configs()
        if video_mode_keys:
            _video_available = True
        else:
            _video_available = False
    except DeviceNotFound:
        _video_available = False

    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title("Mpeg2-Player")
        window.set_default_size(640, 500)
        window.connect("destroy", self.on_destroy)
        vbox = gtk.VBox()
        window.add(vbox)
        hbox = gtk.HBox()
        vbox.pack_start(hbox, expand=False)

        form = Form.of(get_video_mode_enum().using(
                default=self.video_mode_keys[0]), Filepath.named('output_path')\
                        .using(default=''), Integer.named('bitrate').using(
                                default=150, validators=[ValueAtLeast(
                                        minimum=25)], properties={'step': 25, 
                                                'label': 'Bitrate (KB/s)', }))
        self.video_mode_form_view = create_form_view(form)
        for field in ['video_mode', 'output_path', 'bitrate']:
            setattr(self, '%s_field' % field, self.video_mode_form_view.form\
                    .fields[field])
        self.video_mode_field.proxy.connect('changed', self._on_mode_changed)
        self.video_source = None
        # Set default transform to identity
        hbox.add(self.video_mode_form_view.widget)
        self.button = gtk.Button("Start")
        hbox.pack_start(self.button, False)
        self.button.connect("clicked", self.start_stop)
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=1.0, ratio=4.0 / 3.0,
                obey_child=False)
        
        self.pipeline = None
        self._server = None

        vbox.pack_start(self.aframe, expand=True)
        self.movie_view = GStreamerVideoView() 
        self.movie_window = self.movie_view.widget
        self.aframe.add(self.movie_window)
        window.show_all()
        self.window = window

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

    def get_video_source(self):
        selected_mode = self.video_mode_map[self.video_settings]
        caps_str = GstVideoSourceManager.get_caps_string(selected_mode)
        video_source = create_video_source(
                selected_mode['device'], caps_str)
        return video_source

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

        # Start JSON-RPC server to control GStreamer video pipeline.
        # There are issues with the GTK gui freezing when the
        # GStreamer pipeline is started here directly.
        if hasattr(sys, 'frozen'):
            self._server = Popen([base_path().joinpath('server', 'server.exe')], stdout=PIPE, stderr=PIPE)
        else:
            self._server = Popen([sys.executable, base_path().joinpath('server.py')], stdout=PIPE, stderr=PIPE)
        time.sleep(0.5)
        # Connect to JSON-RPC server and request to run the pipeline
        s = Server('http://localhost:8080')
        s.run_pipeline(self.movie_view.window_xid)

        self.video_mode_field.proxy.widget.set_button_sensitivity(gtk.SENSITIVITY_OFF)
        self.output_path_field.widget.set_sensitive(False)
        self.bitrate_field.widget.set_sensitive(False)

        self.button.set_label("Stop")

    def stop(self):
        s = Server('http://localhost:8080')
        s.stop_pipeline(self.movie_view.window_xid)
        s.terminate_pipeline(self.movie_view.window_xid)
        self._server.kill()
        self._server = None
        #self.aframe.remove(self.movie_window)
        #del self.movie_view
        #self.movie_view = None
        self.button.set_label("Start")
        self.video_mode_field.proxy.widget.set_button_sensitivity(gtk.SENSITIVITY_AUTO)
        self.output_path_field.widget.set_sensitive(True)
        self.bitrate_field.widget.set_sensitive(True)

    def on_destroy(self, *args):
        if self._server:
            self.stop()
        gtk.main_quit()


if __name__ == '__main__':        
    logging.basicConfig(format='[%(levelname)s] %(message)s', loglevel=logging.DEBUG)
    GTK_Main()
    gtk.main()
