#!/usr/bin/env python
import logging
import sys
from subprocess import Popen

from path_helpers import path


def base_path():
    p = path(__file__).parent.abspath()
    attempted_paths = []
    while p != path('/').abspath() and not p.joinpath('pygst_utils').isdir():
        attempted_paths.append(p)
        p = p.parent
    if not p:
        raise RuntimeError('cannot find server.exe (attempted paths: %s)' %
                           attempted_paths)
    return p.joinpath('pygst_utils')


package_root = base_path().parent.parent
sys.path.insert(0, package_root)

from pygst_utils.video_pipeline.window_process import WindowProcess


def server_popen(port, force_aspect_ratio=False):
    print '[server_popen] force_aspect_ratio={}'.format(force_aspect_ratio)
    command_args = [str(port)]
    if force_aspect_ratio:
        command_args.insert(0, '--force_aspect_ratio')
    script_path = base_path().joinpath('bin', 'server.py')
    print '[server_popen] script_path=%s' % script_path
    server_process = Popen([sys.executable, script_path] + command_args,
                           cwd=script_path.parent)
    return server_process


def parse_args():
    """Parses arguments, returns (options, args)."""
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Run GStreamer WindowService server')
    parser.add_argument('--force_aspect_ratio', action='store_true')
    parser.add_argument('port', default=8080, type=int, nargs='?')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s',
                        loglevel=logging.INFO)

    args = parse_args()
    print args

    # Create a GStreamer window server process, with an initial `window_xid`
    # set to zero.  The `window_xid` can be set via the server proxy API to
    # specify which window buffer the GStreamer frames should be drawn to.
    service = WindowProcess(0, port=args.port,
                            force_aspect_ratio=args.force_aspect_ratio)

    logging.info('Starting server')
    service.start()

    port = service.parent_pipe.recv()
    logging.info('Received port %s from child process', port)

    try:
        service.join()
    except KeyboardInterrupt:
        pass
    finally:
        service.terminate()
