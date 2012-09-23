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


class DrawQueue(object):
    '''
    A list of draw commands, stored as callables that, are
    passed a set of parameters to draw on from the canvas
    implementation.
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


if __name__ == '__main__':
    #### /drawing closures
    dq = DrawQueue()

    # Add some commands to the drawing queue
    dq.set_source_rgb(1, 1, 1)
    dq.paint()
    dq.move_to(10, 0)
    dq.rectangle(0, 0, 20, 20)
    dq.set_source_rgb(0, 0, 0)
    dq.fill()

    # Create a surface and context
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    ctx = cairo.Context(surface)

    # run defered rendering
    draw_queue_pickle = pickle.dumps(dq)
    draw_queue = pickle.loads(draw_queue_pickle)
    draw_queue.render(ctx)

    surface.write_to_png('output.png')
