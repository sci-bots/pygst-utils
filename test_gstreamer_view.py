import logging

from gstreamer_view import GStreamerVideoView


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)

    v = GStreamerVideoView()
    v.widget.set_size_request(640, 480)
    v.show_and_run()
