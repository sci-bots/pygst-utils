"""
Copyright 2011 Ryan Fobel

This file is part of Microdrop.

Microdrop is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Microdrop is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Microdrop.  If not, see <http://www.gnu.org/licenses/>.
"""

import urllib2
import subprocess
import sys
import site
import tempfile
import os
import zipfile
import tarfile
import re
from distutils.dir_util import copy_tree


PYTHON_VERSION = "%s.%s" % (sys.version_info[0],
                            sys.version_info[1])
CACHE_PATH = "download_cache"


def in_path(filename):
    for d in os.environ['PATH'].split(';'):
        if os.path.isfile(os.path.join(d, filename)):
            return True
    return False


def install(package):
    name = package[0]
    type = package[1]
    print "installing %s" % name

    if type=="py":
        file = download_file(p[2], name, type)
        subprocess.call("python " + file, shell=False)
    elif type=="msi":
        file = download_file(p[2], name, type)
        subprocess.call("msiexec /i " + file, shell=False)
    elif type=="exe":
        file = download_file(p[2], name, type)
        subprocess.call(file, shell=False)
    elif type=="easy_install":
        subprocess.call("easy_install --upgrade " + name, shell=False)
    elif type=="zip":
        src = os.path.join(CACHE_PATH, name, p[3])
        dst = p[4]
        file = download_file(p[2], name, type)
        z = zipfile.ZipFile(file, 'r')
        try:
            print "extracting zip file..."
            z.extractall(os.path.join(CACHE_PATH, name))
        finally:
            z.close()
        print "copying extracted files to %s" % dst
        copy_tree(src, dst)
    elif type=="tar.gz":
        src = os.path.join(CACHE_PATH, name, p[3])
        dst = p[4]
        file = download_file(p[2], name, type)
        z = tarfile.open(file, 'r')
        try:
            print "extracting tar.gz file..."
            z.extractall(os.path.join(CACHE_PATH, name))
        finally:
            z.close()
        print "copying extracted files to %s" % dst
        copy_tree(src, dst)
    elif type=="pip":
        if len(p)>2:
            subprocess.call("pip install --upgrade " + p[2], shell=False)
        else:
            subprocess.call("pip install --upgrade " + name, shell=False)
    else:
        raise Exception("Invalid type")
        

def download_file(link, name, type):
    filepath_path = os.path.join(CACHE_PATH,"%s.%s" % (name,type))
    fp = open(filepath_path, 'wb')
    downloaded = 0
    print link
    resp = urllib2.urlopen(link)
    total_length = None
    try:
        if resp.info().getheaders("Content-Length"):
            total_length = int(resp.info().getheaders("Content-Length")[0])
            print('Downloading %s (%s kB): ' % (link, total_length/1024))
        else:
            print('Downloading %s (unknown size): ' % link)
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            downloaded += len(chunk)
            if not total_length:
                sys.stdout.write('\r%s kB' % (downloaded/1024))
            else:
                sys.stdout.write('\r%3i%%  %s kB' % (100*downloaded/total_length, downloaded/1024))
            sys.stdout.flush()
            fp.write(chunk)
    finally:
        fp.close()
        sys.stdout.write('\n');
        sys.stdout.flush()
    return filepath_path

if __name__ == "__main__":
    if os.name!='nt':
        print "This program only works on Windows."
        exit(1)

    warnings = []

    # get the microdrop root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))

    if os.path.isdir(CACHE_PATH) == False:
        os.mkdir(CACHE_PATH)

    packages = []

    # We must check for setupstools, pip and path since they are used by this
    # script.
    for p in (("setuptools", "py", "http://python-distribute.org/distribute_setup.py"),
              ("pip", "easy_install"),
              ("path", "pip", "http://microfluidics.utoronto.ca/git/path.py.git/snapshot/da43890764f1ee508fe6c32582acd69b87240365.zip")
              ):
        try:
            exec("import " + p[0])
        except:
            packages.append(p)

    # binary dependencies
    if not os.path.isdir(os.path.join("microdrop", "devices")) or \
       not os.path.isdir(os.path.join("microdrop", "lib")) or \
       not os.path.isdir(os.path.join("microdrop", "share")) or \
       not os.path.isdir(os.path.join("microdrop", "etc")) or \
       not os.path.isdir(os.path.join("microdrop", "gst")):
        packages.append(('binary_dependencies',
                         'zip',
                         'http://microfluidics.utoronto.ca/git/microdrop___dependencies.git/snapshot/91714880d27f981cf18a46ccc3cd9b20e1e9c3c9.zip',
                         'microdrop___dependencies-9171488',
                         os.path.abspath('.')))

    if len(packages)>0:
        print "The following packages need to be installed:"
        for p in packages:
            print "\t%s" % p[0]
        
        for p in packages:
            install(p)

    print "\nAll dependencies are installed."

    if len(warnings)>0:
        print
        for w in warnings:
            print w
