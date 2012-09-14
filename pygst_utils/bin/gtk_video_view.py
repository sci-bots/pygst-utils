import logging

from ..video_view.gtk_view import GtkVideoView


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)

    v = GtkVideoView()
    v.widget.set_size_request(640, 480)
    v.show_and_run()
