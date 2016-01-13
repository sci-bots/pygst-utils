import cairo
import numpy as np


def np_to_cairo(np_buf, format=cairo.FORMAT_RGB24):
    height, width, channels = np_buf.shape
    cr_buf = cairo.ImageSurface(format, width, height)

    # Create a numpy view to modify the underlying Cairo `ImageSurface` buffer.
    np_buf_view = np.frombuffer(cr_buf.get_data(), dtype='uint8',
                                count=cr_buf.get_width() * cr_buf.get_height()
                                * 4).reshape(cr_buf.get_height(),
                                             cr_buf.get_width(), -1)[:, :, :3]
    np_buf_view[:] = np_buf
    return cr_buf, np_buf_view
