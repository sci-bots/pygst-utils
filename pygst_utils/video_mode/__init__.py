from __future__ import division
from multiprocessing import Process, Pipe
from pprint import pprint
import logging
import time

from pygtkhelpers.ui.extra_dialogs import field_entry_dialog
from pygtkhelpers.ui.extra_widgets import Enum, Form
from pygtkhelpers.ui.form_view_dialog import create_form_view
try:
    import pygst
    pygst.require("0.10")
except:
    pass
finally:
    import gst
import glib

from ..video_source import (DeviceNotFound, FilteredInput,
                            GstVideoSourceManager, get_available_video_modes,
                            get_video_source_configs)


def get_video_mode_enum(video_modes=None):
    if video_modes is None:
        video_modes = get_available_video_modes(
                format_='YUY2')
    video_mode_map = get_video_mode_map(video_modes)
    video_keys = sorted(video_mode_map.keys())
    return Enum.named('video_mode').valued(*video_keys)


def get_video_mode_map(video_modes=None):
    '''
    Args
    ----

        video_modes (pandas.DataFrame) : Table of video modes, including the
            columns: `device`, `width`, `height`, `fourcc`, and `framerate`.

    Returns
    -------

        (dict): `pandas.Series` video configurations keyed by corresponding
            human-readable string label.
    '''
    if video_modes is None:
        video_modes = get_available_video_modes(format_='YUY2')
    format_cap = (lambda c: '[%s] ' % getattr(c['device'], 'name',
                                              c['device'])[:20] +
                  '{width:4d}x{height:d} {framerate:2.0f}fps '\
                  '({fourcc:s})'.format(**c))
    video_mode_map = dict([(format_cap(c), c)
                           for i, c in video_modes.iterrows()])
    return video_mode_map


def select_video_mode(video_modes=None):
    video_mode_map = get_video_mode_map(video_modes)
    video_keys = sorted(video_mode_map.keys())
    enum = get_video_mode_enum(video_modes)
    valid, response = field_entry_dialog(enum.using(default=video_keys[0]))
    try:
        if valid:
            return video_mode_map[response]
    except:
        raise ValueError, 'No video mode matching: %s' % response


def select_video_caps():
    video_modes = get_available_video_modes(format_='YUY2')
    selected_mode = select_video_mode(video_modes)
    if selected_mode:
        return selected_mode['device'], GstVideoSourceManager.get_caps_string(selected_mode)
    else:
        return None


def get_video_mode_form(video_modes=None):
    if video_modes is None:
        video_modes = get_available_video_modes(format_='YUY2')
    video_mode_map = get_video_mode_map(video_modes)
    video_keys = sorted(video_mode_map.keys())
    form = Form.of(Enum.named('video_mode').valued(
            *video_keys).using(default=video_keys[0]))
    return form


def get_video_mode_form_view(video_modes=None, values=None, use_markup=True):
    form_view = create_form_view(get_video_mode_form(), values=values,
            use_markup=use_markup)
    return form_view


def select_video_source():
    result = select_video_caps()
    if result is None:
        return None
    device, caps_str = result
    return create_video_source(device, caps_str)


def create_video_source(device, caps_str):
    if not device:
        # Assume blank video test src
        video_source = gst.element_factory_make('videotestsrc', 'video_source')
        video_source.set_property('pattern', 2)
    else:
        video_source = GstVideoSourceManager.get_video_source()
        device_key, devices = get_video_source_configs()
        video_source.set_property(device_key, device)
    filtered_input = FilteredInput('filtered_input', caps_str, video_source)
    return filtered_input


def test_pipeline():
    pipeline = gst.Pipeline()
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    video_source = select_video_source()
    pipeline.add(video_sink, video_source)
    video_source.link(video_sink)
    pipeline.set_state(gst.STATE_PLAYING)
    glib.MainLoop().run()


def get_pipeline(video_source=None):
    pipeline = gst.Pipeline()
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    if video_source is None:
        video_source = select_video_source()
    pipeline.add(video_sink, video_source)
    video_source.link(video_sink)
    return pipeline


class _GStreamerProcess(Process):
    def __init__(self, *args, **kwargs):
        super(_GStreamerProcess, self).__init__(*args, **kwargs)

    def start(self, pipe_connection):
        self._pipe = pipe_connection
        return super(_GStreamerProcess, self).start()

    def run(self):
        self.pipeline = None
        self._check_count = 0
        self._main_loop = glib.MainLoop()
        glib.timeout_add(500, self._update_state)
        try:
            self._main_loop.run()
        except DeviceNotFound:
            self._finish()

    def _finish(self):
        self._cleanup_pipeline()
        self._main_loop.quit()

    def _cleanup_pipeline(self):
        if self.pipeline:
            del self.pipeline
            self.pipeline = None

    def _process_request(self, request):
        if request['command'] == 'create':
            '''
            Create a pipeline
            '''
            if self.pipeline is None:
                device, caps_str = request['video_caps']
                video_source = create_video_source(device, caps_str)
                self.pipeline = get_pipeline(video_source)
        elif request['command'] == 'start':
            if self.pipeline:
                result = self.pipeline.set_state(gst.STATE_PLAYING)
                return (result != gst.STATE_CHANGE_FAILURE)
        elif request['command'] == 'stop':
            if self.pipeline:
                self.pipeline.set_state(gst.STATE_NULL)
        elif request['command'] == 'reset':
            self._cleanup_pipeline()
        elif request['command'] == 'finish':
            self._finish()
            raise SystemExit
        elif request['command'] == 'select_video_caps':
            result = select_video_caps()
            return result
        elif request['command'] == 'get_available_video_modes':
            result = get_available_video_modes(**request['kwargs'])
            return result

    def _update_state(self):
        while self._pipe.poll():
            request = self._pipe.recv()
            logging.debug('  [request] {}'.format(request))
            try:
                result = self._process_request(request)
                if request.get('ack', False):
                    self._pipe.send({'result': result})
            except DeviceNotFound:
                if request.get('ack', False):
                    self._pipe.send({'result': None, 'error': True})
            except SystemExit:
                return False
        return True


class GStreamerProcess(object):
    child_class = _GStreamerProcess

    def __init__(self):
        self.master_pipe, self.worker_pipe = Pipe()
        self._process = self.child_class(args=(self.worker_pipe, ))
        self._process.start(self.worker_pipe)
        self._finished = False

    def select_video_caps(self):
        self.master_pipe.send({'command': 'select_video_caps',
                'ack': True})
        # Wait for result so we block until video caps have been
        # selected
        response = self.master_pipe.recv()
        if response.get('error', False):
            raise DeviceNotFound, 'No devices/video modes available'
        return response['result']

    def create(self, video_caps):
        self.master_pipe.send({'command': 'create', 'video_caps': video_caps})

    def start(self):
        logging.debug('sending START')
        self.master_pipe.send({'command': 'start', 'ack': True})
        response = self.master_pipe.recv()
        if not response['result']:
            raise RuntimeError, 'Unable to start pipeline.  Is device already in use?'

    def stop(self, block=True):
        logging.debug('sending STOP')
        self.master_pipe.send({'command': 'stop', 'ack': block})
        if block:
            response = self.master_pipe.recv()
            return response

    def reset(self, block=True):
        self.master_pipe.send({'command': 'reset', 'ack': block})
        if block:
            response = self.master_pipe.recv()
            return response

    def run(self, sleep_duration=1.5):
        video_caps = self.select_video_caps()
        self.create(video_caps)
        for i in range(1):
            self.start()
            time.sleep(sleep_duration)
            self.stop()
        self.reset()

    def finish(self):
        logging.debug('sending FINISH')
        self.master_pipe.send({'command': 'finish'})
        self._finished = True

    def join(self):
        if not self._finished:
            self.finish()
        if self._process:
            self._process.join()
            self._process = None

    def get_available_video_modes(self, **kwargs):
        self.master_pipe.send({'command': 'get_available_video_modes',
                               'kwargs': kwargs, 'ack': True})
        response = self.master_pipe.recv()
        return response['result']

    def get_video_mode_form(self, video_modes=None):
        if video_modes is None:
            video_modes = self.get_available_video_modes(format_='YUY2')
        video_mode_map = get_video_mode_map(video_modes)
        video_keys = sorted(video_mode_map.keys())
        form = Form.of(Enum.named('video_mode').valued(
                *video_keys).using(default=video_keys[0]))
        return form

    def get_video_mode_enum(self, video_modes=None):
        if video_modes is None:
            video_modes = self.get_available_video_modes(format_='YUY2')
        video_mode_map = get_video_mode_map(video_modes)
        video_keys = sorted(video_mode_map.keys())
        return Enum.named('video_mode').valued(*video_keys)


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', loglevel=logging.INFO)
    logging.info('Using GStreamerProcess')
    p = GStreamerProcess()
    pprint(p.get_available_video_modes(format_='YUY2'))
    try:
        p.run(15)
    except (RuntimeError, DeviceNotFound), why:
        logging.error('%s' % why)
    p.join()
