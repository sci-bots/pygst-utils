import re
import os
import sys

from path_find import path_find

AddOption('--wix-sval',
          dest='wix_sval',
          action="store_true",
          help='Skip WiX ICE validation')

env = Environment(ENV=os.environ)
Export('env')

if os.name == 'nt':
    pyinstaller_path = path_find('Build.py')
    if pyinstaller_path is None:
        raise IOError, 'Cannot find PyInstaller on PATH.'
    BUILD_PATH = pyinstaller_path.joinpath('Build.py')

    exe = env.Command('gstreamer_video_test/dist/gstreamer_video_test.exe',
            'test_video.spec', '%s %s -y $SOURCE' % (sys.executable,
                    BUILD_PATH))
    env.Clean(exe, 'dist') 
    env.Clean(exe, 'build') 
    
    AlwaysBuild(exe)
