# -*- mode: python -*-
import zmq
from path import path
import gst
import pygst_utils
import flatland
import opencv_helpers
import pygtkhelpers


extra_py = []
a = Analysis([os.path.join(HOMEPATH,'support\\_mountzlib.py'),
            os.path.join(HOMEPATH,'support\\useUnicode.py'),
            'pygst_utils/bin/server.py'] + extra_py,
            excludes=['gst', 'pygst_utils', 'opencv_helpers', 'flatland',
            'pygtkhelpers'])

for mod in [gst, pygst_utils, flatland, opencv_helpers, pygtkhelpers]:
    mod_path = path(mod.__file__).parent
    a.datas += [(str(mod_path.parent.relpathto(p)), str(p.abspath()), 'DATA')\
            for p in mod_path.walkfiles(ignore=[r'\.git', r'site_scons',
                    r'.*\.pyc'])]

zmq_dll_path = path(zmq.__file__).parent.joinpath('libzmq.dll')
if not zmq_dll_path.isfile():
    raise IOError, 'Cannot find zmq DLL: %s' % zmq_dll_path

a.datas += [(zmq_dll_path.name, str(zmq_dll_path), 'DATA')]


pyz = PYZ(a.pure)
exe = EXE(pyz,
            a.scripts,
            exclude_binaries=True,
            name=os.path.join('build\\pyi.win32\\gstreamer_test_video\\pygst_utils_windows_server',
                    'server.exe'),
            debug=True,
            strip=False,
            upx=True,
            console=True)
coll = COLLECT(exe,
                a.datas,
                a.binaries,
                a.zipfiles,
                upx=True,
                name=os.path.join('dist', 'gstreamer_test_video', 'pygst_utils_windows_server'))
