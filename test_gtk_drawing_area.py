#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
try:
    import pygst
    pygst.require("0.10")
except ImportError:
    pass
finally:
    import gst
import gobject
gobject.threads_init()
gtk.gdk.threads_init()

from warp_perspective import warp_perspective, WarpBin
from gstreamer_view import GStreamerVideoView, get_supported_dims
from rated_bin import RatedBin
from gst_video_source_caps_query.gst_video_source_caps_query import\
        DeviceNotFound, GstVideoSourceManager, FilteredInput
from gst_video_source_caps_query.video_mode_dialog import\
        FormViewDialog, create_form_view, get_video_mode_form,\
        get_video_mode_map, create_video_source, get_video_mode_enum
from test_video import get_pipeline
from pygtkhelpers.ui.extra_widgets import Filepath
from pygtkhelpers.ui.dialogs import error
from flatland import Form


#gst.debug_set_active(True)
#gst.debug_set_default_threshold(3)

class GTK_Main:
    try:
        video_modes = GstVideoSourceManager.get_available_video_modes(
                format_='YUY2')
        video_mode_map = get_video_mode_map(video_modes)
        video_mode_keys = sorted(video_mode_map.keys())
        device_key, devices = GstVideoSourceManager.get_video_source_configs()
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
        vbox.pack_start(hbox, False)

        get_video_mode_form(), 

                         
        form = Form.of(get_video_mode_enum().using(
                default=self.video_mode_keys[0]), Filepath.named('output_path')\
                        .using(default=''))
        self.video_mode_form_view = create_form_view(form)
        self.video_mode_field = self.video_mode_form_view.form.fields[
                'video_mode']
        self.output_path_field = self.video_mode_form_view.form.fields[
                'output_path']
        self.video_mode_field.proxy.connect('changed', self._on_mode_changed)
        #self._on_mode_changed()
        self.video_source = None
        # Set default transform to identity
        hbox.add(self.video_mode_form_view.widget)
        self.button = gtk.Button("Start")
        hbox.pack_start(self.button, False)
        self.button.connect("clicked", self.start_stop)
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=1.0, ratio=4.0 / 3.0,
                obey_child=False)
        
        self.pipeline = None

        vbox.pack_start(self.aframe, False)
        window.show_all()
        self.window = window

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
            if not self.output_path:
                error('Please select a valid output filepath.')               
                return
            self.pipeline = get_pipeline(self.get_video_source(),
                    self.output_path)

            self.movie_view = GStreamerVideoView(self.pipeline)
            self.movie_window = self.movie_view.widget
            self.movie_window.set_size_request(640, 480)
            self.aframe.add(self.movie_window)
            self.aframe.show_all()

            self.pipeline.set_state(gst.STATE_PLAYING)
            self.video_mode_field.proxy.widget.set_button_sensitivity(gtk.SENSITIVITY_OFF)
            self.output_path_field.widget.set_sensitive(False)

            self.button.set_label("Stop")
        else:
            self.pipeline.set_state(gst.STATE_NULL)
            self.aframe.remove(self.movie_window)
            del self.movie_view
            del self.pipeline
            self.pipeline = None
            self.movie_view = None
            self.button.set_label("Start")
            self.video_mode_field.proxy.widget.set_button_sensitivity(gtk.SENSITIVITY_AUTO)
            self.output_path_field.widget.set_sensitive(True)

    def on_destroy(self, *args):
        if self.pipeline:
            self.pipeline.set_state(gst.STATE_NULL)
        gtk.main_quit()


if __name__ == '__main__':        
    GTK_Main()
    gtk.main()
