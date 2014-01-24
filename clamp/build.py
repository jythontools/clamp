# NOTE the obivious lack of support for simultaneous installs.  If in
# fact we need to do this, implement an obvious advisory locking
# scheme when writing files like jar.pth

import distutils
import glob
import jarray
import os
import os.path
import site
import sys
import time
import logging

from collections import OrderedDict
from contextlib import closing, contextmanager  # FIXME need to merge in Java 7 support for AutoCloseable
from java.io import BufferedInputStream, FileInputStream
from java.util.jar import Attributes, JarEntry, JarInputStream, JarOutputStream, Manifest
from java.util.zip import ZipException, ZipInputStream

log = logging.getLogger(__name__)


class NullBuilder(object):

    def __repr__(self):
        return "NullBuilder"

    def write_class_bytes(self, package, classname, bytes):
        pass


_builder = NullBuilder = NullBuilder()


@contextmanager
def register_builder(builder):
    global _builder
    log.debug("Registering builder %r, old builder was %r", builder, _builder)
    old_builder = _builder
    _builder = builder
    yield
    _builder = old_builder


def get_builder():
    return _builder


# probably refactor in a class

def get_package_name(path):
    return "-".join(os.path.split(path)[1].split("-")[:-1])


def read_pth(pth_path):
    paths = OrderedDict()
    if os.path.exists(pth_path):
        with open(pth_path) as pth:
            for path in pth:
                path = path.strip()
                if path.startswith("#") or path.startswith("import "):
                    continue  # FIXME consider preserving comments, other user changes
                name = get_package_name(os.path.split(path)[1])
                paths[name] = path
    return paths


class JarPth(object):
    def __init__(self):
        self._jar_pth_path = os.path.join(site.getsitepackages()[0], "jar.pth")
        self._paths = read_pth(self._jar_pth_path)
        self._mutated = False
        log.debug("paths in jar.pth %s are %r", self._jar_pth_path, self)

    def __enter__(self):
        return self

    def __exit__ (self, type, value, tb):
        self.close()

    def _write_jar_pth(self):
        if self._mutated:
            with open(self._jar_pth_path, "w") as jar_pth:
                for name, path in sorted(self.iteritems()):
                    jar_pth.write(path + "\n")

    def close(self):
        self._write_jar_pth()

    def __getitem__(self, key):
        return self._paths[key]
 
    def __setitem__(self, key, value):
        self._paths[key] = value
        self._mutated = True

    def __delitem__(self, key):
        del self._paths[key]
        self._mutated = True
 
    def __contains__(self, key):
        return key in self._paths
 
    def __len__(self):
        return len(self._paths)
 
    def __repr__(self):
        return repr(self._paths)
    
    def __iter__(self):
        return self._paths.__iter__()

    def iterkeys(self):
        return self._paths.iterkeys()

    def itervalues(self):
        return self._paths.itervalues()

    def iteritems(self):
        return self._paths.iteritems()


# Default location for storing clamped jars
def init_jar_dir():
    jar_dir = os.path.join(site.getsitepackages()[0], "jars")
    if not os.path.exists(jar_dir):
        os.mkdir(jar_dir)
    return jar_dir


class OutputJar(object):

    # Derived, with heavy modifications, from
    # http://stackoverflow.com/questions/1281229/how-to-use-jaroutputstream-to-create-a-jar-file

    def __init__(self, jar=None, output_path="output.jar"):
        self.output_path = output_path
        if jar is not None:
            self.jar = jar
            self.output = None
            return
        self.runpy = None
        self.setup()

    def __enter__ (self):
        return self

    def __exit__ (self, type, value, tb):
        self.close()

    def setup(self):
        manifest = Manifest()
        manifest.getMainAttributes()[Attributes.Name.MANIFEST_VERSION] = "1.0"
        if self.runpy and os.path.exists(self.runpy):
            manifest.getMainAttributes()[Attributes.Name.MAIN_CLASS] = "org.python.util.JarRunner"
        else:
            log.debug("No __run__.py defined, so defaulting to Jython command line")
            manifest.getMainAttributes()[Attributes.Name.MAIN_CLASS] = "org.python.util.jython"

        self.output = open(self.output_path, "wb")
        self.jar = JarOutputStream(self.output, manifest)
        self.created_paths = set()
        self.build_time = int(time.time() * 1000)

    def close(self):
        self.jar.close()
        if self.output:
            self.output.close()

    def create_ancestry(self, path_parts):
        for i in xrange(len(path_parts), 0, -1):  # right to left
            ancestor = "/".join(path_parts[:-i]) + "/"
            if ancestor == "/":
                continue  # FIXME shouldn't need to do this special casing
            if ancestor not in self.created_paths:
                entry = JarEntry(ancestor)
                entry.time = self.build_time
                try:
                    self.jar.putNextEntry(entry)
                    self.jar.closeEntry()
                except ZipException, e:
                    if not "duplicate entry" in str(e):
                        log.error("Problem in creating entry %r", entry, exc_info=True)
                        raise
                self.created_paths.add(ancestor)


class JarCopy(OutputJar):

    def __init__(self, jar=None, output_path="output.jar", runpy=None):
        self.output_path = output_path
        if jar is not None:
            self.jar = jar
            self.output = None
            return
        self.runpy = runpy
        self.setup()

    def copy_zip_input_stream(self, zip_input_stream, parent=None):
        """Given a `zip_input_stream`, copy all entries to the output jar"""

        chunk = jarray.zeros(8192, "b")
        while True:
            entry = zip_input_stream.getNextEntry()
            if entry is None:
                break
            try:
                # NB: cannot simply use old entry because we need
                # to recompute compressed size
                if parent:
                    name = "/".join([parent, entry.name])
                else:
                    name = entry.name
                output_entry = JarEntry(name)
                output_entry.time = entry.time
                self.jar.putNextEntry(output_entry)
                while True:
                    read = zip_input_stream.read(chunk, 0, 8192)
                    if read == -1:
                        break
                    self.jar.write(chunk, 0, read)
                self.jar.closeEntry()
            except ZipException, e:
                if not "duplicate entry" in str(e):
                    log.error("Problem in copying entry %r", output_entry, exc_info=True)
                    raise

    def copy_jars(self, jars):
        """Consumes a sequence of jar paths, fixing up paths as necessary"""
        seen = set()
        for jar_path in jars:
            normed_path = os.path.realpath(os.path.normpath(jar_path))
            if os.path.splitext(normed_path)[1] != ".jar":
                log.warn("Will only copy jars, not %s", normed_path)
                next
            if normed_path in seen:
                next
            seen.add(normed_path)
            log.debug("Copying %s", normed_path)
            with open(normed_path) as f:
                with closing(JarInputStream(f)) as input_jar:
                    self.copy_zip_input_stream(input_jar)

    def copy_file(self, relpath, path):
        path_parts = tuple(os.path.split(relpath)[0].split(os.sep))
        self.create_ancestry(path_parts)
        chunk = jarray.zeros(8192, "b")
        with open(path) as f:
            with closing(BufferedInputStream(f)) as bis:
                output_entry = JarEntry(relpath)
                output_entry.time = os.path.getmtime(path) * 1000
                self.jar.putNextEntry(output_entry)
                while True:
                    read = bis.read(chunk, 0, 8192)
                    if read == -1:
                        break
                    self.jar.write(chunk, 0, read)
        self.jar.closeEntry()


class JarBuilder(OutputJar):

    def __repr__(self):
        return "JarBuilder(output={!r})".format(self.output_path)

    def _canonical_path_parts(self, package, classname):
        return tuple(classname.split("."))

    def write_class_bytes(self, package, classname, bytes):
        path_parts = self._canonical_path_parts(package, classname)
        self.create_ancestry(path_parts)
        entry = JarEntry("/".join(path_parts) + ".class")
        entry.time = self.build_time
        self.jar.putNextEntry(entry)
        self.jar.write(bytes.toByteArray())
        self.jar.closeEntry()


def find_jython_jars():
    """Uses the same classpath resolution as bin/jython"""
    jython_jar_path = os.path.normpath(os.path.join(sys.executable, "../../jython.jar"))
    jython_jar_dev_path = os.path.normpath(os.path.join(sys.executable, "../../jython-dev.jar"))
    if os.path.exists(jython_jar_dev_path):
        jars = [jython_jar_dev_path]
        jars.extend(glob.glob(os.path.normpath(os.path.join(jython_jar_dev_path, "../javalib/*.jar"))))
    elif os.path.exists(jython_jar_path):
        jars = [jython_jar_path]
    else:
        raise Exception("Cannot find jython jar")
    return jars


def find_jython_lib_files():
    seen = set()
    sitepackages = site.getsitepackages()
    root = os.path.normpath(os.path.join(sys.executable, "../../Lib"))
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        ignore = False
        for pkg in sitepackages:
            if dirpath.startswith(pkg):
                ignore = True
        if ignore:
            continue
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            relpath = path[len(root)-3:]   # this will of course not work for included directories FIXME bad hack!
            yield relpath, os.path.realpath(path)

    # FIXME verify realpath, realpath(dirpath) has not been seen (no cycles!)


def find_package_libs(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            relpath = path[len(root)+1:]
            yield relpath, path


def copy_zip_file(path, output_jar):
    try:
        with open(path) as f:
            with closing(BufferedInputStream(f)) as bis:
                if not skip_zip_header(bis):
                    return False
                with closing(ZipInputStream(bis)) as input_zip:
                    try:
                        output_jar.copy_zip_input_stream(input_zip, "Lib")
                        return True
                    except ZipException:
                        return False
    except IOError:
        return False


def skip_zip_header(bis):
    try:
        for i in xrange(2000):
            # peek ahead 2 bytes to look for PK in header
            bis.mark(2)
            first = chr(bis.read())
            second = chr(bis.read())
            if first == "P" and second == "K":
                bis.reset() 
                return True
            else:
                bis.reset()
                bis.read()
        else:
            return False
    except ValueError:  # consume -1 on unsuccessful read
        return False


def build_jar(package_name, jar_name, clamp_setup, output_path=None):
    if output_path is None:
        jar_dir = init_jar_dir()
        output_path = os.path.join(jar_dir, jar_name)
        with JarPth() as paths:
            paths[package_name] = os.path.join("./jars", jar_name)
    with JarBuilder(output_path=output_path) as builder:
        with register_builder(builder):
            for module in clamp_setup.modules:
                __import__(module)


def get_included_jars(src_dir, packages):
    for package in packages:
        for dirpath, dirs, files in os.walk(os.path.join(src_dir, package)):
            for name in files:
                _, ext = x = os.path.splitext(name)
                if ext == ".jar":
                    path = os.path.join(dirpath, name)
                    yield path[len(src_dir)+1:]


def copy_included_jars(package_name, packages, src_dir=None, dest_dir=None):
    # FIXME dest_dir should presumably be something like
    # clamped-0.1-py2.7.egg, not clamped
    # but this still might not work - eggs IIRC are protective of what they contain
    if src_dir is None:
        src_dir = os.getcwd()
    if dest_dir is None:
        dest_dir = os.path.join(site.getsitepackages()[0], package_name)
    print "src=%s, dest=%s" % (src_dir, dest_dir)
    jar_files = sorted(get_included_jars(src_dir, packages))
    print "jar_files"
    print jar_files
    distutils.dir_util.create_tree(dest_dir, jar_files)
    for jar_file in jar_files:
        distutils.file_util.copy_file(os.path.join(src_dir, jar_file), os.path.join(dest_dir, jar_file))
    with JarPth() as paths:
        for jar_file in jar_files:
            paths[jar_file] = os.path.join(".", jar_file)
            
            
def create_singlejar(output_path, classpath, runpy):
    jars = classpath
    jars.extend(find_jython_jars())
    site_path = site.getsitepackages()[0]
    with JarPth() as jar_pth:
        for jar_path in sorted(jar_pth.itervalues()):
            jars.append(os.path.join(site_path, jar_path))
    
    with JarCopy(output_path=output_path, runpy=runpy) as singlejar:
        singlejar.copy_jars(jars)
        log.debug("Copying standard library")
        for relpath, realpath in find_jython_lib_files():
            singlejar.copy_file(relpath, realpath)

        # FOR NOW: copy everything in site-packages into Lib/ in the built jar;
        # this is because Jython in standalone mode has the limitation that it can
        # only properly find packages under Lib/ and cannot process .pth files
        # THIS SHOULD BE FIXED
            
        sitepackage = site.getsitepackages()[0]

        for path in read_pth(os.path.join(sitepackage, "easy-install.pth")).itervalues():
            relpath = "/".join(os.path.normpath(os.path.join("Lib", path)).split(os.sep))  # ZIP only uses /
            path = os.path.realpath(os.path.normpath(os.path.join(sitepackage, path)))

            if copy_zip_file(path, singlejar):
                log.debug("Copying %s (zipped file)", path)  # tiny lie - already copied, but keeping consistent!
                continue

            log.debug("Copying %s", path)
            for pkg_relpath, pkg_realpath in find_package_libs(path):
                # Filter out egg metadata
                parts = pkg_relpath.split(os.sep)
                if len(parts) < 2:
                    continue
                head = parts[0]
                if head == "EGG-INFO" or head.endswith(".egg-info"):
                    continue
                singlejar.copy_file(os.path.join("Lib", pkg_relpath), pkg_realpath)

        if runpy and os.path.exists(runpy):
            singlejar.copy_file("__run__.py", runpy)
