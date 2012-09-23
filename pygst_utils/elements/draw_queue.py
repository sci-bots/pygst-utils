try:
    import cPickle as pickle
except ImportError:
    import pickle
from collections import deque
import cairo


class DrawQueue:
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


#### drawing closures
class paint(object):
    def __call__(self, ctx):
        ctx.paint()

class fill(object):
    def __call__(self, ctx):
        ctx.fill()

class set_source_rgb(object):
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def __call__(self, ctx):
        ctx.set_source_rgb(self.r, self.g, self.b)


class moveto(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __call__(self, ctx):
        ctx.move_to(self.x, self.y)


class rectangle(object):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __call__(self, ctx):
        ctx.rectangle(self.x, self.y, self.w, self.h)


if __name__ == '__main__':
    #### /drawing closures
    dq = DrawQueue()

    # Add some commands to the drawing queue
    dq.append(set_source_rgb_closure(1, 1, 1))
    dq.append(paint_closure())
    dq.append(moveto_closure(10, 0))
    dq.append(rectangle_closure(0, 0, 20, 20))
    dq.append(set_source_rgb_closure(0, 0, 0))
    dq.append(fill_closure())

    # Create a surface and context
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    ctx = cairo.Context(surface)

    # run defered rendering
    draw_queue_pickle = pickle.dumps(dq)
    draw_queue = pickle.loads(draw_queue_pickle)
    draw_queue.render(ctx)

    surface.write_to_png('output.png')
