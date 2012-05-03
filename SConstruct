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

    SOFTWARE_VERSION = '0.1.0'
    version_target = env.Command('version.txt', None,
                            'echo %s > $TARGET' % SOFTWARE_VERSION)
    exe = env.Command('gstreamer_video_test/dist/gstreamer_video_test.exe',
            'test_video.spec', '%s %s -y $SOURCE' % (sys.executable,
                    BUILD_PATH))
    wxs = env.Command('test_video.wxs', None,
            '%s generate_wxs.py -v %s > $TARGET' % (sys.executable,
                    SOFTWARE_VERSION))
    wixobj = env.Command('test_video.wixobj', wxs,
                            'candle -o $TARGET $SOURCE')
    env.Clean(exe, 'dist') 
    env.Clean(exe, 'build') 
    env.Clean(wixobj, 'test_video.wixpdb') 
    
    msi = env.Command('test_video-%s.msi' % SOFTWARE_VERSION, wixobj,
            'light -ext WixUIExtension -cultures:en-us $SOURCE '
            '-out $TARGET')
    AlwaysBuild(version_target)
    Depends(exe, version_target)
    Depends(wxs, exe)
    Depends(wxs, 'generate_wxs.py')
    Default(msi)
