import logging

from redirect_io import nostderr
import pandas as pd

logger = logging.getLogger(__name__)


def pipeline_command_from_json(json_source, colorspace='bgr'):
    '''
    Args
    ----

        json_source (dict) : A dictionary containing at least the keys
            `device_name`, `width`, `height`, `framerate_num`, and
            `framerate_denom`.
        colorspace (str) : Supported values are `bgr` or `rgb`.

    Returns
    -------

        (str) : A pipeline command string compatible with `gst-launch`
            terminated with an `appsink` element.
    '''
    # Import here, since importing `gst` before calling `parse_args` causes
    # command-line help to be overridden by GStreamer help.
    with nostderr():
        from .video_source import VIDEO_SOURCE_PLUGIN, DEVICE_KEY

    caps_str = (u'video/x-raw-rgb,width={width:d},height={height:d},'
                u'framerate={framerate_num:d}/{framerate_denom:d}'
                .format(**json_source))

    # Set `(red|green|blue)_mask` to ensure RGB channel order for both YUY2 and
    # I420 video sources.  If this is not done, red and blue channels might be
    # swapped.
    #
    # See [here][1] for default mask values.
    #
    # [1]: https://www.freedesktop.org/software/gstreamer-sdk/data/docs/latest/gst-plugins-bad-plugins-0.10/gst-plugins-bad-plugins-videoparse.html#GstVideoParse--blue-mask
    if colorspace == 'bgr':
        caps_str += (u',red_mask=(int)255,green_mask=(int)65280,'
                     u'blue_mask=(int)16711680')

    device_str = u'{} {}="{}"'.format(VIDEO_SOURCE_PLUGIN, DEVICE_KEY,
                                      json_source['device_name'])
    logger.debug('[View] video config device string: %s', device_str)
    logger.debug('[View] video config caps string: %s', caps_str)

    video_command = ''.join([device_str, ' ! ffmpegcolorspace ! ', caps_str,
                             ' ! appsink name=app-video emit-signals=true'])
    return video_command


def default_video_source():
    '''
    Returns
    -------

        (pandas.Series) : Available video source configuration with highest
            width and framerate.
    '''
    with nostderr():
        from .video_source import (get_video_source_names,
                                   expand_allowed_capabilities,
                                   get_allowed_capabilities)

        device_names = get_video_source_names()
        device_name = device_names[0]
        df_allowed_caps = get_allowed_capabilities(device_name)
        df_source_caps = expand_allowed_capabilities(df_allowed_caps)
    df_source_caps.sort_values(['width', 'framerate'], ascending=False, inplace=True)
    df_source_caps.insert(0, 'device_name', device_name)
    return df_source_caps.iloc[0]


def get_available_video_source_configs():
    '''
    Returns
    -------

        (pandas.DataFrame) : Available video source configuration with highest
            width and framerate.
    '''
    with nostderr():
        from .video_source import (get_video_source_names,
                                   expand_allowed_capabilities,
                                   get_allowed_capabilities)

    device_names = get_video_source_names()
    frames = []
    for device_name_i in device_names:
        df_allowed_caps = get_allowed_capabilities(device_name_i)
        df_source_caps = expand_allowed_capabilities(df_allowed_caps)
        df_source_caps.insert(0, 'device_name', device_name_i)
        frames.append(df_source_caps)
    return pd.concat(frames)
