from __future__ import division
from collections import namedtuple
import logging
import platform
from pprint import pprint
from multiprocessing import Process, Pipe
import traceback

from path_helpers import path
try:
    import pygst
    pygst.require("0.10")
except:
    pass
finally:
    import gst


Fps = namedtuple('Fps', 'num denom')


def test(**kw):
    return []


class DeviceNotFound(Exception):
    pass


def get_available_video_modes(**kwargs):
    video_source_manager = GstVideoSourceManager()
    caps = video_source_manager.query_device_extracted_caps(**kwargs)
    video_modes = []
    for device, caps in caps.items():
        for c in caps:
            c['device'] = device
            video_modes.append(c)
    if not video_modes:
        raise DeviceNotFound, 'No video modes available.'
    return video_modes


def get_video_source_configs():
    logging.basicConfig(format='%(message)s', level=logging.INFO)

    if platform.system() == 'Linux':
        try:
            devices = path('/dev/v4l/by-id').listdir()
        except OSError:
            raise DeviceNotFound, 'No devices available'
        device_key = 'device'
    else:
        try:
            devices = GstVideoSourceManager.get_video_source().probe_get_values_name(
                    'device-name')
        except:
            devices = []
        if not devices:
            raise DeviceNotFound, 'No devices available'
        device_key = 'device-name'
    return device_key, devices


class GstVideoSourceManager(object):
    def __init__(self, video_source=None):
        self.device_key, self.devices = get_video_source_configs()

    @staticmethod
    def get_video_source():
        if platform.system() == 'Linux':
            video_source = gst.element_factory_make('v4l2src', 'video_source')
        else:
            video_source = gst.element_factory_make('dshowvideosrc', 'video_source')
        return video_source

    def _device_iter(self):
        for video_device in self.devices:
            if 'ASUS Virtual' in video_device:
                continue
            video_source = self.get_video_source()
            video_source.set_property(self.device_key, video_device)
            try:
                video_caps = GstVideoSourceCapabilities(video_source)
            except gst.LinkError:
                logging.warning('error querying device %s (skipping)' % video_device)
                continue
            yield video_device, video_caps

    @staticmethod
    def get_caps_string(extracted_cap):
        return '{name:s},width={width:d},height={height:d},fourcc={fourcc:s},'\
                'framerate={framerate.num:d}/{framerate.denom:d}'.format(**extracted_cap)

    def _query_device_extracted_caps(self, pipe_conn, dimensions=None,
            framerate=None, format_=None, name=None):
        extracted_device_caps = {}
        for video_device, video_caps in self._device_iter():
            final_caps = []
            combined_caps = video_caps.get_extracted_allowed_caps(
                    dimensions=dimensions, framerate=framerate, format_=format_,
                            name=name)
            for combined_cap in combined_caps:
                framerates = combined_cap['framerate']
                del combined_cap['format']
                for framerate in framerates:
                    cap = combined_cap.copy()
                    cap['framerate'] = framerate
                    final_caps.append(cap)
            extracted_device_caps[video_device] = final_caps
        #pipe_conn.send(extracted_device_caps)
        return extracted_device_caps

    def query_device_extracted_caps(self, dimensions=None, framerate=None, format_=None,
            name=None):
        #master_pipe, worker_pipe = Pipe()
        #p = Process(target=self._query_device_extracted_caps, args=(worker_pipe,
                #), kwargs={ 'dimensions': dimensions, 'framerate': framerate,
                        #'format_': format_, 'name': name, })
        #p.start()
        #extracted_device_caps = master_pipe.recv()
        #p.join()
        extracted_device_caps = self._query_device_extracted_caps(None,
                dimensions=dimensions, framerate=framerate, format_=format_,
                        name=name)
        return extracted_device_caps

    def query_device_caps(self, dimensions=None, framerate=None, format_=None,
            name=None):
        return dict([(video_device, video_caps.get_allowed_caps(dimensions=dimensions,
                framerate=framerate, format_=format_, name=name))
                        for video_device, video_caps in self._device_iter()])

    def query_devices(self, dimensions=None, framerate=None, format_=None,
            name=None):
        for video_device, video_caps in self._device_iter():
            print '%s:' % getattr(video_device, 'name', video_device)
            for k, v in video_caps.unique_settings(video_caps.get_allowed_caps(
                    dimensions=dimensions, framerate=framerate,
                            format_=format_, name=name)).items():
                print 3 * ' ', '%s: %s' % (k, v)
            print 72 * '-'

    @staticmethod
    def validate(extracted_caps):
        try:
            extracted_caps = sorted(extracted_caps.items())
        except:
            raise
        video_modes = get_available_video_modes()
        mode_map = dict([(sorted(v), v) for v in video_modes])
        if extracted_caps not in mode_map:
            raise ValueError, 'Unsupported video mode'
        return mode_map[extracted_caps]


class GstVideoSourceCapabilities(object):
    def __init__(self, video_source):
        pipeline = gst.Pipeline()
        source_pad = video_source.get_pad('src')
        video_sink = gst.element_factory_make('autovideosink', 'video_sink')
        pipeline.add(video_source)
        pipeline.add(video_sink)
        try:
            video_source.link(video_sink)
            pipeline.set_state(gst.STATE_READY)
            self.allowed_caps = [dict([(k, c[k])
                    for k in c.keys()] + [('name', c.get_name())])
                            for c in source_pad.get_allowed_caps()]
            pipeline.set_state(gst.STATE_NULL)
            self._allowed_info = self.unique_settings(self.allowed_caps)
        finally:
            del pipeline

    def extract_dimensions(self, dimensions_obj):
        for field in ['width', 'height']:
            if isinstance(dimensions_obj[field], gst.IntRange):
                dimensions_obj[field] = dimensions_obj[field].high
        return dimensions_obj['width'], dimensions_obj['height']

    def extract_format(self, format_obj):
        return format_obj['format'].fourcc

    def extract_fps(self, framerate_obj):
        framerates = []
        try:
            for fps in framerate_obj['framerate']:
                framerates.append(Fps(fps.num, fps.denom))
        except TypeError:
            if isinstance(framerate_obj['framerate'], gst.FractionRange):
                for fps in (framerate_obj['framerate'].low,
                        framerate_obj['framerate'].high):
                    framerates.append(Fps(fps.num, fps.denom))
            else:
                fps = framerate_obj['framerate']
                framerates.append(Fps(fps.num, fps.denom))
            #framerates.append({'num': fps.num, 'denom': fps.denom})
        return sorted(set(framerates))

    @property
    def framerates(self):
        return self._allowed_info['framerates']

    @property
    def dimensions(self):
        return self._allowed_info['dimensions']

    @property
    def formats(self):
        return self._allowed_info['formats']

    @property
    def names(self):
        return self._allowed_info['names']

    def get_extracted_allowed_caps(self, dimensions=None, framerate=None, format_=None, name=None):
        allowed_caps = self.get_allowed_caps(dimensions=dimensions,
                framerate=framerate, format_=format_, name=name)
        for cap in allowed_caps:
            if framerate:
                cap['framerate'] = (framerate, )
            else:
                cap['framerate'] = self.extract_fps(cap)
            cap['dimensions'] = self.extract_dimensions(cap)
            cap['fourcc'] = self.extract_format(cap)
        return allowed_caps

    def get_allowed_caps(self, dimensions=None, framerate=None, format_=None, name=None):
        allowed_caps = self.allowed_caps[:]
        if dimensions:
            allowed_caps = [c for c in allowed_caps
                    if dimensions == self.extract_dimensions(c)]
        if framerate:
            allowed_caps = [c for c in allowed_caps
                    if framerate in self.extract_fps(c)]
        if format_:
            allowed_caps = [c for c in allowed_caps
                    if format_ == self.extract_format(c)]
        if name:
            allowed_caps = [c for c in allowed_caps if name == c['name']]
        return allowed_caps

    def unique_settings(self, caps):
        framerates = []
        for d in caps:
            framerates.extend(self.extract_fps(d))
        framerates = tuple(sorted(set(framerates)))
        dimensions = tuple(sorted(set([self.extract_dimensions(d)
                for d in caps])))
        formats = tuple(sorted(set([self.extract_format(d)
                for d in caps])))
        names = tuple(sorted(set([d['name'] for d in caps])))
        info = {}
        for k, v in (('framerates', framerates), ('dimensions', dimensions),
                ('formats', formats), ('names', names)):
            if v:
                info[k] = v
        return info


class FilteredInput(gst.Bin):
    def __init__(self, name, caps_str, video_src):
        super(FilteredInput, self).__init__(name)

        try:
            caps = gst.Caps(caps_str)
        except (Exception, ), why:
            traceback.print_exc()
            print 'name: {}, caps_str: "{}"'.format(name, caps_str)
            raise
        caps_filter = gst.element_factory_make('capsfilter', 'caps_filter')
        caps_filter.set_property('caps', caps)

        self.add(video_src, caps_filter)
        video_src.link(caps_filter)

        src_gp = gst.GhostPad("src", caps_filter.get_pad('src'))
        self.add_pad(src_gp)


def parse_args():
    """Parses arguments, returns ``(options, args)``."""
    from argparse import ArgumentParser

    parser = ArgumentParser(description="""\
Queries for supported video modes for GStreamer input devices.""",
                            epilog="""\
(C) 2012  Christian Fobel, licensed under the terms of GPLv2.""",
                           )
    parser.add_argument('--width',
                    action='store', dest='width', type=int,
                    help='video width (required if height is specified)')
    parser.add_argument('--height',
                    action='store', dest='height', type=int,
                    help='video height (required if width is specified)')
    parser.add_argument('--fps',
                    action='store', dest='fps', type=int,
                    help='video frames per second')
    parser.add_argument('--format',
                    action='store', dest='format_',
                    help='video format')
    parser.add_argument('--stream_name',
                    action='store', dest='stream_name',
                    help='stream name (e.g., "video/x-raw-yuv")')
    args = parser.parse_args()

    return args


def format_cap(c):
    return '[{width:4d} {height:4d} {fps:2.0f}fps '\
        '({fourcc:s})]'.format(fps=c['framerate'].num / c['framerate'].denom, **c)


def main():
    args = parse_args()

    kwargs = {'framerate': args.fps, 'format_': args.format_,
            'name': args.stream_name}
    if args.width and args.height:
        kwargs['dimensions'] = (args.width, args.height)
    video_source_manager = GstVideoSourceManager()
    video_source_manager.query_devices(**kwargs)
    caps = video_source_manager.query_device_extracted_caps(**kwargs)
    pprint(sorted(['[%s] %s' % (getattr(device, 'name', device)[:20],
            format_cap(c)) for device, caps in caps.items() for c in caps]))


if __name__ == '__main__':
    main()
