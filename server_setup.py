#!/usr/bin/env python

import distutils.core

try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py

from path import path

# Setup script for path

server_path = path('pygst_utils_windows_server')

kw = {
    'name': "pygst_utils_windows_server",
    'version': "{{ ___VERSION___ }}",
    'description': 'GStreamer Windows server',
    'author': "Christian Fobel",
    'author_email': "christian@fobel.net",
    'url': "https://github.com/cfobel/pygst_utils",
    'license': "GPLv2 License",
    'packages': ['pygst_utils_windows_server', ],
    'package_data': {'pygst_utils_windows_server': [server_path.relpathto(p)
            for p in server_path.walkfiles()]},
    'cmdclass': dict(build_py=build_py),
}


# If we're running Python 2.3, add extra information
if hasattr(distutils.core, 'setup_keywords'):
    if 'classifiers' in distutils.core.setup_keywords:
        kw['classifiers'] = [
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
            'Intended Audience :: Developers',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules'
          ]
    if 'download_url' in distutils.core.setup_keywords:
        urlfmt = "https://github.com/cfobel/pygst_utils/tarball/%s"
        kw['download_url'] = urlfmt % kw['version']


distutils.core.setup(**kw)
