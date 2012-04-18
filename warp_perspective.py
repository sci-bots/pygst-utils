__author__ = 'Christian Fobel <christian@fobel.net>'


import gst
import gobject
gobject.threads_init()
import numpy as np
import cv


def registered_element(class_):
	"""Class decorator for registering a Python element.  Note that decorator
	syntax was extended from functions to classes in Python 2.6, so until 2.6
	becomes the norm we have to invoke this as a function instead of by
	saying::

		@gstlal_element_register
		class foo(gst.Element):
			...
	
	Until then, you have to do::

		class foo(gst.Element):
			...
		gstlal_element_register(foo)
	"""
	from inspect import getmodule
	gobject.type_register(class_)
	getmodule(class_).__gstelementfactory__ = (class_.__name__, gst.RANK_NONE,
            class_)
	return class_


@registered_element
class warp_perspective(gst.BaseTransform):
    '''
    Use OpenCV to apply a warp-perspective.
    '''
    __gstdetails__ = (
        "OpenCV warp-perspective",
        "Filter",
        __doc__.strip(),
        __author__
    )
    __gsttemplates__ = (
        gst.PadTemplate("sink",
            gst.PAD_SINK, gst.PAD_ALWAYS,
            gst.caps_from_string('video/x-raw-rgb,depth=24')
        ),
        gst.PadTemplate("src",
            gst.PAD_SRC, gst.PAD_ALWAYS,
            gst.caps_from_string('video/x-raw-rgb,depth=24')
        )
    )

    def do_start(self):
        """GstBaseTransform->start virtual method."""
        self.history = []
        transform_matrix = np.array([
                [1.2681043148040771, 0.1850511133670807, 28.115493774414062],
                [-0.03174028918147087, 1.4999419450759888, 181.2607421875],
                [1.831687222875189e-05, 0.0006744748097844422, 1.0]],
                        dtype='float32')
        self.transform_matrix = cv.fromarray(transform_matrix)
        return True

    def do_transform(self, inbuf, outbuf):
        """GstBaseTransform->transform virtual method."""
        def array2cv(a):
            dtype2depth = {
                    'uint8':   cv.IPL_DEPTH_8U,
                    'int8':    cv.IPL_DEPTH_8S,
                    'uint16':  cv.IPL_DEPTH_16U,
                    'int16':   cv.IPL_DEPTH_16S,
                    'int32':   cv.IPL_DEPTH_32S,
                    'float32': cv.IPL_DEPTH_32F,
                    'float64': cv.IPL_DEPTH_64F,
                }
            try:
                nChannels = a.shape[2]
            except:
                nChannels = 1
            cv_im = cv.CreateMat(a.shape[0], a.shape[1], cv.CV_8UC3)
            cv.SetData(cv_im, a.tostring(), a.shape[1] * nChannels)
            return cv_im

        y = np.fromstring(inbuf.data, dtype='uint8', count=len(inbuf))
        struct = inbuf.caps[0]
        width, height = struct['width'], struct['height']
        y.shape = (height, width, 3)
        cv_img = array2cv(y)

        warped = cv.CreateMat(height, width, cv.CV_8UC3)
        cv.WarpPerspective(cv_img, warped, self.transform_matrix,
                flags=cv.CV_WARP_INVERSE_MAP)
        data = warped.tostring()
        outbuf[:len(data)] = data

        # Done!
        return gst.FLOW_OK
