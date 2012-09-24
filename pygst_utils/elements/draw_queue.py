try:
    import cPickle as pickle
except ImportError:
    import pickle
from collections import deque
import cairo


class DrawQueue(object):
    '''
    A list of draw commands, appended by calling the method corresponding to
    the cairo action to be performed.  These commands can then be rendered by
    calling the render() method, passing in the cairo context to draw on.

    For example:

    >>> dq = DrawQueue()

    Add some commands to the drawing queue

    >>> dq.set_source_rgb(1, 1, 1)
    >>> dq.paint()
    >>> dq.move_to(10, 0)
    >>> dq.rectangle(0, 0, 20, 20)
    >>> dq.set_source_rgb(0, 0, 0)
    >>> dq.fill()

    Create a surface and context

    >>> surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    >>> ctx = cairo.Context(surface)

    Run deferred rendering

    >>> draw_queue_pickle = pickle.dumps(dq)
    >>> draw_queue = pickle.loads(draw_queue_pickle)
    >>> draw_queue.render(ctx)

    >>> surface.write_to_png('output.png')
    '''
    def __init__(self, render_callables=None):
        self.render_callables = render_callables or deque()

    def append(self, attr, args):
        '''
        Add a render callable to the queue
        '''
        self.render_callables.append((attr, args))

    def render(self, cairo_ctx):
        '''
        Call all the render callables with cairo_ctx
        '''
        if self.render_callables:
            for attr, args in self.render_callables:
                getattr(cairo_ctx, attr)(*args)

    def __getattr__(self, attr):
        if hasattr(self, attr):
            return object.__getattribute__(self, attr)
        else:
            append = object.__getattribute__(self, 'append')
            return lambda *args: append(attr, args)


def get_example_draw_queue(width, height):
    draw_queue = DrawQueue()
    draw_queue.save()
    draw_queue.scale(width, height)
    draw_queue.move_to(0.1, 0.1)
    draw_queue.set_line_width(0.02)
    draw_queue.rectangle(0.1, 0.1, 0.2, 0.2)
    draw_queue.set_source_rgb(1, 1, 1)
    draw_queue.stroke_preserve()
    draw_queue.set_source_rgb(0, 0, 0)
    draw_queue.fill()
    draw_queue.restore()
    return draw_queue
