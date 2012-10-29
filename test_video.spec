# -*- mode: python -*-
from path import path
import pygst_utils
import flatland
import opencv_helpers
import pygtkhelpers


extra_py = []
a = Analysis([os.path.join(HOMEPATH,'support\\_mountzlib.py'),
            os.path.join(HOMEPATH,'support\\useUnicode.py'),
            'examples/gtk_gstreamer_window/gtk_gstreamer_window.py'] + extra_py,
            excludes=['pygst_utils', 'opencv_helpers', 'flatland', 'pygtkhelpers'])

for mod in [pygst_utils, flatland, opencv_helpers, pygtkhelpers]:
	mod_path = path(mod.__file__).parent
	a.datas += [(str(mod_path.parent.relpathto(p)), str(p.abspath()), 'DATA')\
		    for p in mod_path.walkfiles(ignore=[r'\.git', r'site_scons',
                    r'.*\.pyc'])]


pyz = PYZ(a.pure)
exe = EXE(pyz,
            a.scripts,
            exclude_binaries=True,
            name=os.path.join('build\\pyi.win32\\gstreamer_test_video',
                    'gstreamer_test_video.exe'),
            debug=True,
            strip=False,
            upx=True,
            console=True)
coll = COLLECT(exe,
                a.datas,
                a.binaries,
                a.zipfiles,
                upx=True,
                name=os.path.join('dist', 'gstreamer_test_video'))
