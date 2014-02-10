#!/usr/bin/env python

import distutils.core

try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py

import version


# Setup script for path
kw = {'name': "pygst_utils",
      'version': version.getVersion(),
      'description': 'GStreamer Windows server',
      'author': "Christian Fobel",
      'author_email': "christian@fobel.net",
      'url': "https://github.com/cfobel/pygst_utils",
      'license': "GPLv2 License",
      'packages': ['pygst_utils', 'pygst_utils.bin', 'pygst_utils.elements',
                   'pygst_utils.video_mode', 'pygst_utils.video_pipeline',
                   'pygst_utils.video_source', 'pygst_utils.video_view'],
      'cmdclass': dict(build_py=build_py)}


# If we're running Python 2.3, add extra information
if hasattr(distutils.core, 'setup_keywords'):
    if 'classifiers' in distutils.core.setup_keywords:
        kw['classifiers'] = [
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
            'Intended Audience :: Developers',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules']
    if 'download_url' in distutils.core.setup_keywords:
        urlfmt = "https://github.com/cfobel/pygst_utils/tarball/%s"
        kw['download_url'] = urlfmt % kw['version']


distutils.core.setup(**kw)
