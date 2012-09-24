import os
import logging
from multiprocessing import Process, Pipe
import multiprocessing
multiprocessing.freeze_support()

from __init__ import get_pipeline
from pipeline_manager import PipelineManager
import gst
import gtk
gtk.threads_init()


class WindowProcess(Process):
    def __init__(self, window_xid, force_aspect_ratio=True):
        super(WindowProcess, self).__init__()
        self.force_aspect_ratio = force_aspect_ratio
        self.parent_pipe, self.child_pipe = Pipe()
        self.window_xid = window_xid
        self.pm = None

    def __call__(self, **kwargs):
        logging.debug('{}'.format(kwargs.get('command', None)))
        request = kwargs
        self.parent_pipe.send(request)
        if request.get('ack', False):
            return self.parent_pipe.recv()
        return None

    def run(self):
        '''
        Method to be run in the child process.
        '''
        self.pm = PipelineManager(force_aspect_ratio=self.force_aspect_ratio)
        self.pm.window_xid = self.window_xid

        gtk.timeout_add(500, self._update_state)
        gtk.main()

    def _update_state(self):
        '''
        This method will be called at regular intervals to handle any
        pending requests in the pipe.
        '''
        while self.child_pipe.poll():
            request = self.child_pipe.recv()
            try:
                threads_entered = False
                gtk.threads_enter()
                threads_entered = True
                response = self._process_request(request)
                if request.get('ack', False):
                    self.child_pipe.send({'response': response})
            finally:
                if threads_entered:
                    gtk.threads_leave()
        return True

    def _process_request(self, request):
        '''
        Execute the specified command by looking up the corresponding
        member function.
        '''
        command_attr = '_%s' % request.get('command', None)
        if hasattr(self, command_attr):
            return getattr(self, command_attr)(**request)
        else:
            logging.warning('Invalid command: %s' % request.get('command',
                    None))
            return None

    ### command-processing methods ####################################################

    def _start(self, **kwargs):
        response = self.pm.pipeline.set_state(gst.STATE_PLAYING)
        return response

    def _get_pid(self, **kwargs):
        return os.getpid()

    def _get_state(self, **kwargs):
        response = self.pm.pipeline.get_state(gst.STATE_NULL)
        return response

    def _get_video_mode_enum(self, **kwargs):
        from ..video_mode import get_video_mode_enum

        return get_video_mode_enum()

    def _get_video_mode_map(self, **kwargs):
        from ..video_mode import get_video_mode_map

        return get_video_mode_map()

    def _select_video_mode(self, **kwargs):
        from ..video_mode import select_video_mode

        return select_video_mode()

    def _select_video_caps(self, **kwargs):
        from ..video_mode import select_video_caps

        device, caps_str = select_video_caps()
        return {'device': str(device), 'caps_str': caps_str}

    def _get_available_video_modes(self, **kwargs):
        from ..video_mode import get_available_video_modes

        return get_available_video_modes()

    def _get_video_source_configs(self, **kwargs):
        from ..video_mode import get_video_source_configs

        return get_video_source_configs()

    def _stop(self, **kwargs):
        response = self.pm.pipeline.set_state(gst.STATE_NULL)
        return response

    def _scale(self, width=None, height=None, **kwargs):
        if width is None or height is None:
            return None
        caps_filter = self.pm.pipeline.get_by_name('video_scale_caps_filter')
        if not caps_filter:
            return None
        caps_str = 'video/x-raw-yuv,width={},height={}'.format(width, height)
        caps = gst.Caps(caps_str)
        caps_filter.set_property('caps', caps)
        print '[_scale] width={} height={} DONE'.format(width, height)

    def _create(self, **kwargs):
        response = self.create(kwargs['device'], kwargs['caps_str'],
                kwargs.get('bitrate', None),
                        kwargs.get('output_path', None),
                        kwargs.get('draw_queue', None),
                        kwargs.get('with_scale', False))
        return response

    def _join(self, **kwargs):
        gtk.main_quit()
        return False

    ### utility methods ####################################################

    def create(self, device, caps_str, bitrate=None, record_path=None,
            draw_queue=None, with_scale=False):
        from ..video_mode import create_video_source

        def init_pipeline(pm, device, caps_str, bitrate, record_path,
                draw_queue, with_scale):
            video_source = create_video_source(device, caps_str)
            pipeline = get_pipeline(video_source, bitrate, record_path,
                    draw_queue, with_scale=with_scale)
            pm.pipeline = pipeline
            return pm.pipeline.set_state(gst.STATE_READY)
        return init_pipeline(self.pm, device, caps_str, bitrate, record_path,
                draw_queue, with_scale=with_scale)
