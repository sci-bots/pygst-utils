import sys
try:
    import cPickle as pickle
except ImportError:
    import pickle

from path_helpers import path
import gst
import gobject
gobject.threads_init()

package_path = path(__file__).abspath().parent.parent.parent
sys.path.insert(0, package_path)
from pygst_utils.video_mode import select_video_source
from pygst_utils.elements.cairo_draw import CairoDrawQueue
from pygst_utils.elements.draw_queue import get_example_draw_queue


def test_no_cairo():
    video_source = select_video_source()
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    pipeline = gst.Pipeline()
    pipeline.add(video_source, video_sink)
    gst.element_link_many(video_source, video_sink)
    pipeline.set_state(gst.STATE_PLAYING)
    pipeline.set_state(gst.STATE_NULL)


def test_cairo():
    video_source = select_video_source()
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    pipeline = gst.Pipeline()
    cairo_draw = CairoDrawQueue('cairo_draw')
    cairo_color_in = gst.element_factory_make('ffmpegcolorspace', 'cairo_color_in')
    cairo_color_out = gst.element_factory_make('ffmpegcolorspace', 'cairo_color_out')
    pipeline.add(video_source, video_sink, cairo_draw, cairo_color_in, cairo_color_out)
    gst.element_link_many(video_source, cairo_color_in, cairo_draw, cairo_color_out, video_sink)
    pipeline.set_state(gst.STATE_PLAYING)
    return pipeline



if __name__ == '__main__':
    pipeline = test_cairo()
    main_loop = gobject.MainLoop()

    def update_draw_queue_generator(pipeline, draw_queue_func):
        state_data = pipeline.get_state()
        while state_data[1] != gst.STATE_PLAYING:
            yield True
        video_sink = pipeline.get_by_name('video_sink')
        cairo_draw = pipeline.get_by_name('cairo_draw')
        sink_pad = video_sink.get_pad('sink')
        caps = sink_pad.get_negotiated_caps().get_structure(0)
        cairo_draw = pipeline.get_by_name('cairo_draw')
        cairo_draw.set_property('draw-queue', pickle.dumps(
                draw_queue_func(caps['width'], caps['height'])))
        yield False

    update_draw_queue = update_draw_queue_generator(pipeline,
            get_example_draw_queue)
    gobject.timeout_add(500, update_draw_queue.next)
    try:
        main_loop.run()
    except KeyboardInterrupt:
        main_loop.quit()
