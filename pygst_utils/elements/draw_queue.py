try:
    import cPickle as pickle
except ImportError:
    import pickle
from collections import deque
import cairo


#### drawing closures
class Paint(object):
    def __call__(self, ctx):
        ctx.paint()


class Fill(object):
    def __call__(self, ctx):
        ctx.fill()


class SetSourceRgb(object):
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def __call__(self, ctx):
        ctx.set_source_rgb(self.r, self.g, self.b)


class MoveTo(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __call__(self, ctx):
        ctx.move_to(self.x, self.y)


class Rectangle(object):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __call__(self, ctx):
        ctx.rectangle(self.x, self.y, self.w, self.h)


class Stroke(object):
    def __call__(self, ctx):
        ctx.stroke()


class StrokePreserve(object):
    def __call__(self, ctx):
        ctx.stroke_preserve()


class SetLineWidth(object):
    def __init__(self, line_width):
        self.line_width = line_width

    def __call__(self, ctx):
        ctx.set_line_width(self.line_width)


class Save(object):
    def __call__(self, ctx):
        ctx.save()


class Restore(object):
    def __call__(self, ctx):
        ctx.restore()


class Scale(object):
    def __init__(self, sx, sy):
        self.sx = sx
        self.sy = sy

    def __call__(self, ctx):
        ctx.scale(self.sx, self.sy)


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
    def __init__(self, render_callables = None):
        self.render_callables = render_callables or deque()

    def append(self, render_callable):
        '''
        Add a render callable to the queue
        '''
        self.render_callables.append(render_callable)

    def render(self, cairo_ctx):
        '''
        Call all the render callables with cairo_ctx
        '''
        for render_callable in self.render_callables:
            render_callable(cairo_ctx)

    operations = {
        'paint': Paint,
        'fill': Fill,
        'set_source_rgb': SetSourceRgb,
        'move_to': MoveTo,
        'rectangle': Rectangle,
    }

    def paint(self, *args):
        self.append(Paint(*args))

    def fill(self, *args):
        self.append(Fill(*args))

    def set_source_rgb(self, *args):
        self.append(SetSourceRgb(*args))

    def move_to(self, *args):
        self.append(MoveTo(*args))

    def rectangle(self, *args):
        self.append(Rectangle(*args))

    def stroke(self, *args):
        self.append(Stroke(*args))

    def save(self, *args):
        self.append(Save(*args))

    def restore(self, *args):
        self.append(Restore(*args))

    def scale(self, *args): self.append(Scale(*args))
    def stroke_preserve(self, *args): self.append(StrokePreserve(*args))
    def set_line_width(self, *args): self.append(SetLineWidth(*args))


def get_example_draw_queue(width, height):
    draw_queue = DrawQueue()
    draw_queue.save()
    draw_queue.scale(width, height)
    draw_queue.move_to(0.4, 0.4)
    draw_queue.set_line_width(0.02)
    draw_queue.rectangle(0.4, 0.4, 0.2, 0.2)
    draw_queue.set_source_rgb(1, 1, 1)
    draw_queue.stroke_preserve()
    draw_queue.set_source_rgb(0, 0, 0)
    draw_queue.fill()
    draw_queue.restore()
    return draw_queue
