from __future__ import division
from functools import partial
from collections import deque


class DrawQueue(object):
    '''
    A list of draw commands, appended by calling the method corresponding to
    the cairo action to be performed.  These commands can then be rendered by
    calling the render() method, passing in the cairo context to draw on.

    For example:

    >>> import pickle
    >>> import cairo
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

    # Note that the following list of methods will be added as attributes.
    # Each method represents a cairo draw command.  By calling any of these
    # methods on a DrawQueue instance, the corresponding command (along with
    # the specified arguments) will be recorded to be played back using the
    # render() method.
    cairo_methods = ['restore', 'save', 'scale', 'move_to', 'set_line_width',
                     'line_to', 'close_path', 'rectangle', 'set_source_rgb',
                     'stroke_preserve', 'set_source_rgba', 'fill', 'translate',
                     'stroke', 'fill_preserve', 'clip', 'clip_preserve']

    def __init__(self, render_callables=None):
        self.render_callables = render_callables or deque()

        # Dynamically add the methods listed in cairo_methods
        self._add_methods()

    def __getstate__(self):
        data_dict = self.__dict__.copy()
        # Since instance methods may not be pickled, remove all dynamically
        # added methods before pickling.  These methods can be added again
        # using the _add_methods() method.
        for f in self.cairo_methods:
            if f in data_dict:
                del data_dict[f]
        return data_dict

    def __setstate__(self, data_dict):
        self.__dict__ = data_dict
        # Since instance methods are not pickled, dynamically add the methods
        # listed in cairo_method.
        self._add_methods()

    def _add_methods(self):
        for f in self.cairo_methods:
            setattr(self, f, partial(self.append, f))

    def append(self, attr, *args): #self, attr, args):
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


def get_example_draw_queue(width, height, fill_color=(0, 0, 0),
        stroke_color=(1, 1, 1)):
    draw_queue = DrawQueue()
    draw_queue.save()
    draw_queue.scale(width, height)
    draw_queue.move_to(0.1, 0.1)
    draw_queue.set_line_width(0.02)
    draw_queue.rectangle(0.1, 0.1, 0.2, 0.2)
    draw_queue.set_source_rgb(*stroke_color)
    draw_queue.stroke_preserve()
    draw_queue.set_source_rgb(*fill_color)
    draw_queue.fill()
    draw_queue.restore()
    return draw_queue
