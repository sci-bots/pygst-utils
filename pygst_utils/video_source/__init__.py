# coding: utf-8
from path_helpers import path
import gst
import pandas as pd
import platform


if platform.system() == 'Linux':
    VIDEO_SOURCE_PLUGIN = 'v4l2src'
    DEVICE_KEY = 'device'
else:
    VIDEO_SOURCE_PLUGIN = 'dshowvideosrc'
    DEVICE_KEY = 'device-name'


class DeviceNotFound(Exception):
    pass


def get_video_source_names():
    '''
    Returns
    -------

         (list) : List of names (`str`) of video source devices available
             for use with GStreamer.
    '''
    if platform.system() == 'Linux':
        try:
            devices = path('/dev/v4l/by-id').listdir()
        except OSError:
            raise DeviceNotFound('No devices available')
    else:
        try:
            video_source = gst.element_factory_make(VIDEO_SOURCE_PLUGIN,
                                                    'video_source')
            devices = video_source.probe_get_values_name(DEVICE_KEY)
        except:
            devices = []
        if not devices:
            raise DeviceNotFound('No devices available')
    return devices


def get_allowed_capabilities(device_name):
    '''
    Args
    ----

        device_name (str) : Name of device to query.

    Returns
    -------

         (pandas.DataFrame) : Video source capabilities queried from source pad
             of device with specified device name.  Columns contain GStreamer data types
             (e.g., `gst.Fourcc, gst.Fraction`, etc.).  See `expand_allowed_capabilities`
             to convert output of this function to data frame using only basic types
             (i.e., string and numeric data types).
    '''
    pipeline = gst.Pipeline()

    video_source = gst.element_factory_make(VIDEO_SOURCE_PLUGIN, 'video_source')
    video_source.set_property(DEVICE_KEY, device_name)

    source_pad = video_source.get_pad('src')
    #video_sink = gst.element_factory_make('fakesink', 'video_sink')
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    pipeline.add(video_source)
    pipeline.add(video_sink)
    try:
        video_source.link(video_sink)
        pipeline.set_state(gst.STATE_READY)
        allowed_caps = [dict([(k, c[k]) for k in c.keys()] + [('name',
                                                               c.get_name())])
                        for c in source_pad.get_allowed_caps()]
        pipeline.set_state(gst.STATE_NULL)
    finally:
        del pipeline

    return pd.DataFrame(allowed_caps)


def extract_dimensions(dimensions_obj):
    '''
    Args
    ----

        dimensions_obj (pandas.Series) : Width and height.

    Returns
    -------

        (pandas.Series) : Replace width/height values in `gst.IntRange` form
            with maximum value in range.
    '''
    for field in ['width', 'height']:
        if isinstance(dimensions_obj[field], gst.IntRange):
            dimensions_obj[field] = dimensions_obj[field].high
    return [dimensions_obj['width'], dimensions_obj['height']]


def extract_format(format_obj):
    '''
    Args
    ----

        format_obj (gst.Fourcc) : Four CC video format code.
            TODO: Add URL to four CC format list.

    Returns
    -------

        (str) : Four CC code as four character string.
    '''
    return format_obj.fourcc


def extract_fps(framerate_obj):
    '''
    Args
    ----

        framerate_obj (gst.Fraction, gst.FractionRange) : Either a single
            GStreamer frame rate fraction, or a range of fractions.

    Returns
    -------

        (list) : One `Fps` object for each frame rate fraction (multiple if
            `framerate_obj` is a `gst.FractionRange`).
    '''
    framerates = []
    try:
        for fps in framerate_obj:
            framerates.append((fps.num, fps.denom))
    except TypeError:
        if isinstance(framerate_obj, gst.FractionRange):
            for fps in (framerate_obj.low,
                        framerate_obj.high):
                framerates.append((fps.num, fps.denom))
        else:
            fps = framerate_obj
            framerates.append((fps.num, fps.denom))
    return sorted(set(framerates))


def expand_allowed_capabilities(df_allowed_caps):
    '''
    Convert GStreamer data types to basic Python types.

    For example, `format` in `df_allowed_caps` is of type `gst.Fourcc`, but can
    simply be converted to a string of four characters.

    Args
    ----

        df_allowed_caps (pandas.DataFrame) : Video capabilities configurations
            in form returned by `get_allowed_capabilities` function.

    Returns
    -------

        (pandas.DataFrame) : One row per video configuration containing only
            basic string or numeric data types.  Also, lists of frame rates in
            `df_allowed_caps` are expanded to multiple rows.
    '''
    df_modes = df_allowed_caps.copy().drop(['framerate', 'width', 'height',
                                            'format'], axis=1)
    df_modes['fourcc'] = df_allowed_caps.format.map(lambda v:
                                                    extract_format(v))
    df_dimensions = (df_allowed_caps[['width', 'height']]
                     .apply(lambda v: extract_dimensions(v), axis=1))
    df_modes.insert(0, 'width', df_dimensions.width)
    df_modes.insert(1, 'height', df_dimensions.height)

    # From GStreamer, framerates are encoded as either a ratio or a list of
    # ratios.
    # The `expand_fps` function normalizes the framerate entry for each row to
    # be a *`list`* of GStreamer ratios.
    frame_rates = df_allowed_caps.framerate.map(lambda v: extract_fps(v))

    # Expand the list of ratios for each row into one row per ratio, and
    # replace `framerate` column with *numerator* (`framerate_num`) and
    # *denominator* (`framerate_denom`).
    frames = []

    for (i, mode_i), framerates_i in zip(df_modes.iterrows(), frame_rates):
        frame_i = [mode_i.tolist() + list(fps_j) for fps_j in framerates_i]
        frames.extend(frame_i)
    df_modes = pd.DataFrame(frames, columns=df_modes.columns.tolist() +
                            ['framerate_num', 'framerate_denom'])
    # Compute framerate as float for convenience (ratio form is required for
    # setting GStreamer capabilities when creating a pipeline).
    df_modes['framerate'] = (df_modes['framerate_num'] /
                             df_modes['framerate_denom'])
    return df_modes


def get_source_capabilities(video_source_names=None):
    '''
    Args
    ----

        video_source_names (list) : List of video source names.  See
            `get_video_source_names` function to query available device names.

    Returns
    -------

        (pandas.DataFrame) : One row per available video source configuration.
            Columns include: `['device_name', 'width', 'height', 'fourcc',
            'name', 'framerate_num', 'framerate_denom', 'framerate']`.
    '''
    if video_source_names is None:
        video_source_names = get_video_source_names()

    frames = []

    for device_name_i in video_source_names:
        df_allowed_caps_i = get_allowed_capabilities(device_name_i)
        df_source_caps_i = expand_allowed_capabilities(df_allowed_caps_i)
        df_source_caps_i.insert(0, 'device_name', device_name_i)
        frames.append(df_source_caps_i)

    return pd.concat(frames).reset_index(drop=True)
