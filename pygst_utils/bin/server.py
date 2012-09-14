#!/usr/bin/env python
import logging

from pygst_utils.video_pipeline.window_service import WindowService


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', loglevel=logging.DEBUG)

    service = WindowService()
    logging.info('Starting server')

    service.run()
