import os
import logging
from multiprocessing import Process, Pipe
try:
    import cPickle as pickle
except ImportError:
    import pickle

import gst
import gtk
gtk.threads_init()

from __init__ import get_pipeline
from pipeline_manager import PipelineManager

from ..video_source import DeviceNotFound


class WindowProcess(Process):
    def __init__(self, window_xid, port=None, force_aspect_ratio=True):
        super(WindowProcess, self).__init__()
        self.force_aspect_ratio = force_aspect_ratio
        self.parent_pipe, self.child_pipe = Pipe()
        self.window_xid = window_xid
        self.pm = None
        self.last_frame = None
        self.port = port

    def run(self):
        '''
        Method to be run in the child process.
        '''
        import zmq
        from serialsocket import SerializingSocket

        self.ctx = zmq.Context.instance()
        self.sock = SerializingSocket(self.ctx, zmq.REP)
        if self.port is None:
            self.port = self.sock.bind_to_random_port('tcp://*')
        else:
            self.sock.bind('tcp://*:%d' % self.port)
        print 'socket bound to port %d' % self.port
        self.child_pipe.send(self.port)

        self.pm = PipelineManager(force_aspect_ratio=self.force_aspect_ratio)
        self.pm.window_xid = self.window_xid

        update_period_ms = 10
        print 'using update period of %d ms' % update_period_ms
        gtk.timeout_add(update_period_ms, self._update_state)
        gtk.main()

    def _update_state(self):
        '''
        This method will be called at regular intervals to handle any
        pending requests in the pipe.
        '''
        while self.sock.poll(timeout=10):
            request = self.sock.recv_zipped_pickle()
            try:
                threads_entered = False
                gtk.threads_enter()
                threads_entered = True
                response = self._process_request(request)
                self.sock.send_zipped_pickle(response)
            finally:
                if threads_entered:
                    gtk.threads_leave()
        return True

    def _process_request(self, request):
        '''
        Execute the specified command by looking up the corresponding
        member function.
        '''
        command_attr = '_command___%s' % request.get('command', None)
        if hasattr(self, command_attr):
            return getattr(self, command_attr)(*request.get('args', []),
                                               **request.get('kwargs', {}))
        else:
            logging.warning('Invalid command: %s' % request.get('command',
                                                                None))
            return None

    ### command-processing methods ####################################################

    def _command___get_available_commands(self):
        command_prefix = '_command___'
        return [k[len(command_prefix):] for k in dir(self)
                if k.startswith(command_prefix)]

    def _command___window_xid(self, window_xid):
        if window_xid is not None:
            self.pm.window_xid = window_xid
        return self.pm.window_xid

    def _command___start(self):
        # Cast GStreamer state-change return value _(i.e.,
        # `GstStateChangeReturn`)_ enumerated type as integer.  Otherwise,
        # there can be issues when calling through a proxy.
        #
        # For example, when running the [MicroDrop][1] application by calling
        # `python -m microdrop.microdrop` from outside of the source directory,
        # the following error occurs when calling one of the remote API
        # commands:
        #
        #     Traceback (most recent call last):
        #       File ".../microdrop/gui/dmf_device_view.py", line 266, in destroy_video_proxy
        #         self._proxy.stop()
        #       File ".../pygst-utils/pygst_utils/video_pipeline/window_service_proxy.py", line 40, in __call__
        #         return self.sock.recv_zipped_pickle()
        #       File ".../pygst-utils/pygst_utils/video_pipeline/serialsocket.py", line 31, in recv_zipped_pickle
        #         return pickle.loads(pobj)
        #     AttributeError: 'NoneType' object has no attribute 'StateChangeReturn'
        #
        # [1]: http://microfluidics.utoronto.ca/microdrop
        return int(self.pm.pipeline.set_state(gst.STATE_PLAYING))

    def _command___pipeline_available(self):
        return not (self.pm.pipeline is None)

    def _command___get_pid(self):
        return os.getpid()

    def _command___get_state(self):
        # Cast GStreamer state-change return value _(i.e.,
        # `GstStateChangeReturn`)_ enumerated type as integer.  Otherwise,
        # there can be issues when calling through a proxy.
        # See `_command___start` for more details
        return int(self.pm.pipeline.get_state(gst.STATE_NULL))

    def _command___get_video_mode_enum(self):
        from ..video_mode import get_video_mode_enum

        return get_video_mode_enum()

    def _command___get_video_mode_map(self):
        from ..video_mode import get_video_mode_map

        try:
            result = get_video_mode_map()
        except DeviceNotFound:
            result = {}
        return result

    def _command___select_video_mode(self):
        from ..video_mode import select_video_mode

        return select_video_mode()

    def _command___select_video_caps(self):
        from ..video_mode import select_video_caps

        device, caps_str = select_video_caps()
        return {'device': str(device), 'caps_str': caps_str}

    def _command___get_available_video_modes(self):
        from ..video_mode import get_available_video_modes

        return get_available_video_modes()

    def _command___get_video_source_configs(self):
        from ..video_mode import get_video_source_configs

        return get_video_source_configs()

    def _command___stop(self):
        response = self.pm.pipeline.set_state(gst.STATE_NULL)
        # Cast GStreamer state-change return value _(i.e.,
        # `GstStateChangeReturn`)_ enumerated type as integer.  Otherwise,
        # there can be issues when calling through a proxy.
        # See `_command___start` for more details
        return int(response)

    def _command___request_frame(self):
        frame_grabber = self.pm.pipeline.get_by_name('grab_frame')
        if frame_grabber:
            frame_grabber.set_property('grab-requested', True)

    def _command___set_draw_queue(self, draw_queue):
        cairo_draw = self.pm.pipeline.get_by_name('cairo_draw')
        if cairo_draw:
            cairo_draw.set_property('draw-queue', pickle.dumps(draw_queue))

    def _command___set_warp_transform(self, transform_str):
        warp_bin = self.pm.pipeline.get_by_name('warp_bin')
        if warp_bin:
            warp_bin.warper.set_property('transform-matrix', transform_str)

    def _command___scale(self, width, height):
        if width is None or height is None:
            return None
        caps_filter = self.pm.pipeline.get_by_name('video_scale_caps_filter')
        if not caps_filter:
            return None
        caps_str = 'video/x-raw-yuv,width={},height={}'.format(width, height)
        caps = gst.Caps(caps_str)
        caps_filter.set_property('caps', caps)
        print '[_scale] width={} height={} DONE'.format(width, height)

    def _command___join(self):
        gtk.main_quit()
        return False

    def _command___pop_frame(self):
        frame = self.last_frame
        self.last_frame = None
        return frame

    def _command___get_frame(self):
        return self.last_frame

    def _command___create(self, device, caps_str, record_path=None,
                          bitrate=None, draw_queue=None, with_scale=False,
                          with_warp=False, with_frame_grab=True):
        from ..video_mode import create_video_source

        def init_pipeline(pm, device, caps_str, bitrate, record_path,
                          draw_queue, with_scale, with_warp, with_frame_grab):
            values = [device, caps_str, bitrate, record_path, draw_queue,
                      with_scale, with_warp, with_frame_grab]
            print 'init_pipeline args={}'.format(values)
            video_source = create_video_source(device, caps_str)
            if with_frame_grab:
                on_frame_grabbed = self.on_frame_grabbed
            else:
                on_frame_grabbed = None
            pipeline = get_pipeline(video_source, bitrate, record_path,
                                    draw_queue, with_scale=with_scale,
                                    with_warp=with_warp,
                                    on_frame_grabbed=on_frame_grabbed)
            pm.pipeline = pipeline
            return pm.pipeline.set_state(gst.STATE_READY)

        response = init_pipeline(self.pm, device, caps_str, bitrate,
                                 record_path, draw_queue, with_scale,
                                 with_warp, with_frame_grab)
        # Cast GStreamer state-change return value _(i.e.,
        # `GstStateChangeReturn`)_ enumerated type as integer.  Otherwise,
        # there can be issues when calling through a proxy.
        # See `_command___start` for more details
        return int(response)

    ### utility methods ####################################################

    def on_frame_grabbed(self, frame):
        self.last_frame = frame


if __name__ == '__main__':
    import multiprocessing

    multiprocessing.freeze_support()

    p = WindowProcess(0, 8888)
    p.start()
    port = p.parent_pipe.recv()
    print 'Received port {} from child process'.format(port)

    import zmq
    from serialsocket import SerializingSocket

    ctx = zmq.Context.instance()
    req = SerializingSocket(ctx, zmq.REQ)
    req.connect('tcp://localhost:%d' % port)
    req.send_zipped_pickle({'command': 'select_video_mode'})
    response = req.recv_zipped_pickle()
    print response
    try:
        p.join()
    except:
        p.terminate()
