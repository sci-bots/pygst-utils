#!/usr/bin/env python
import distutils.core
import platform
import sys

from setuptools import setup

import version


install_requires = ['opencv_helpers', 'redirect-io', 'wheeler.pygtkhelpers']

# Platform-specific package requirements.
if platform.system() == 'Windows':
    install_requires += ['pygst-0.10-win']
else:
    try:
        import gst
    except ImportError:
        print >> sys.stderr, ('Please install GStreamer Python bindings using '
                              'your systems package manager.')


setup(name="pygst_utils",
      version=version.getVersion(),
      description='GStreamer Windows server',
      author="Christian Fobel",
      author_email="christian@fobel.net",
      url="https://github.com/sci-bots/pygst-utils",
      license="GPLv2 License",
      packages=['pygst_utils', 'pygst_utils.bin', 'pygst_utils.elements',
                'pygst_utils.video_mode', 'pygst_utils.video_pipeline',
                'pygst_utils.video_view'],
      install_requires=install_requires)
