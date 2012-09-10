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
    exe1 = env.Command('gstreamer_video_test/dist/gstreamer_video_test.exe',
            'test_video.spec', '%s %s -y $SOURCE' % (sys.executable,
                    BUILD_PATH))
    exe2 = env.Command('gstreamer_video_test_server/dist/gstreamer_video_test_server.exe',
            'test_video_server.spec', '%s %s -y $SOURCE' % (sys.executable,
                    BUILD_PATH))
    wxs = env.Command('test_video.wxs', None,
            '%s generate_wxs.py -v %s > $TARGET' % (sys.executable,
                    SOFTWARE_VERSION))
    wixobj = env.Command('test_video.wixobj', wxs,
                            'candle -o $TARGET $SOURCE')
    env.Clean(exe1, 'dist') 
    env.Clean(exe1, 'build') 
    env.Clean(wixobj, 'test_video.wixpdb') 
    
    msi = env.Command('test_video-%s.msi' % SOFTWARE_VERSION, wixobj,
            'light -ext WixUIExtension -cultures:en-us $SOURCE '
            '-out $TARGET')
    AlwaysBuild(version_target)
    Depends(exe1, version_target)
    Depends(exe2, version_target)
    Depends(wxs, exe1)
    Depends(wxs, exe2)
    Depends(wxs, 'generate_wxs.py')
    Default(msi)
