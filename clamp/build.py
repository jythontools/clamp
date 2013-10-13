import argparse
import glob
import java
import setuptools
import jarray
import os
import os.path
import site
import sys
import time

from collections import OrderedDict
from contextlib import closing  # FIXME maybe directly support a context manager interface
from distutils.errors import DistutilsOptionError, DistutilsSetupError
from java.io import BufferedInputStream
from java.util.jar import Attributes, JarEntry, JarInputStream, JarOutputStream, Manifest
from java.util.zip import ZipException, ZipInputStream

import clamp  # FIXME change to relative path


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


def write_jar_pth(jar_pth_path, paths):
    with open(jar_pth_path, "w") as jar_pth:
        for name, path in sorted(paths.iteritems()):
            jar_pth.write(path + "\n")


class OutputJar(object):

    # Derived, with heavy modifications, from
    # http://stackoverflow.com/questions/1281229/how-to-use-jaroutputstream-to-create-a-jar-file

    def __init__(self, jar=None, output_path="output.jar"):
        # self.manifest = None
        self.output_path = output_path
        if jar is not None:
            self.jar = jar
            self.output = None
            return

        manifest = Manifest()
        manifest.getMainAttributes()[Attributes.Name.MANIFEST_VERSION] = "1.0"

        # FIXME only do this if __run__.py defined, otherwise select "org.python.util.jython"
        manifest.getMainAttributes()[Attributes.Name.MAIN_CLASS] = "org.python.util.JarRunner"

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
                print "Adding", ancestor
                entry = JarEntry(ancestor)
                entry.time = self.build_time
                try:
                    self.jar.putNextEntry(entry)
                    self.jar.closeEntry()
                except ZipException, e:
                    if not "duplicate entry" in str(e):
                        print "Problem in creating entry", entry
                        raise
                self.created_paths.add(ancestor)


class JarCopy(OutputJar):

    # FIXME change JarCopy to a better name
    # if __run__.py defined, set manifest to point to this: org.python.util.JarRunner
    # http://stackoverflow.com/questions/9689793/cant-execute-jar-file-no-main-manifest-attribute

    def copy_zip_input_stream(self, zip_input_stream):
        """Given a `zip_input_stream`, copy all entries to the output jar"""

        chunk = jarray.zeros(8192, "b")
        while True:
            entry = zip_input_stream.getNextEntry()
            if entry is None:
                break
            try:
                # NB: cannot simply use old entry because we need
                # to recompute compressed size
                output_entry = JarEntry(entry.name)
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
                    print "Problem in copying entry", output_entry
                    raise

    def copy_jars(self, jars):
        """Consumes a sequence of jar paths, fixing up paths as necessary"""
        seen = set()
        for jar_path in jars:
            normed_path = os.path.realpath(os.path.normpath(jar_path))
            if os.path.splitext(normed_path)[1] != ".jar":
                print "Will only copy jars, not", normed_path
                next
            if normed_path in seen:
                print "Ignoring duplicate jar", normed_path
                next
            seen.add(normed_path)
            print "Copying", normed_path
            with open(normed_path) as f:
                with closing(JarInputStream(f)) as input_jar:
                    self.copy_zip_input_stream(input_jar)

    def copy_file(self, relpath, path):
        path_parts = tuple(os.path.split(relpath)[0].split(os.sep))
        # print "Creating", path_parts
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

    def canonical_path_parts(self, package, classname):
        return tuple(classname.split("."))

    def saveBytes(self, package, classname, bytes):
        path_parts = self.canonical_path_parts(package, classname)
        self.create_ancestry(path_parts)
        entry = JarEntry("/".join(path_parts) + ".class")
        entry.time = self.build_time
        self.jar.putNextEntry(entry)
        self.jar.write(bytes.toByteArray())
        self.jar.closeEntry()


def validate_clamp(distribution, keyword, values):
    print "Validating: ", keyword, values
    if keyword != "clamp":
        raise DistutilsSetupError("invalid keyword: {}".format(keyword))
    try:
        invalid = []
        clamped = list(distribution.clamp)
        for v in clamped:
            # FIXME test if valid module name too
            if not isinstance(v, basestring):
                invalid.append(v)
        if invalid:
            raise DistutilsSetupError(
                "clamp={} is invalid, must be an iterable of importable module names".format(
                    values))
    except TypeError, ex:
        print type(ex), ex
        raise DistutilsSetupError("clamp={} is invalid: {}".format(values, ex))
    distribution.clamp = clamped


class build_jar(setuptools.Command):

    description = "create a jar for all clamped Python classes for this package"
    user_options = [
        ("output=",   "o", "write jar to output path"),
    ]

    def initialize_options(self):
        self.output = None
        self.output_jar_pth = True

    def finalize_options(self):
        if self.output is None:
            jar_dir = os.path.join(site.getsitepackages()[0], "jars")
            self.output = os.path.join(jar_dir, self.get_jar_name())
        else:
            self.output_jar_pth = False
            dir_path = os.path.split(self.output)[0]
            if dir_path and not os.path.exists(dir_path):
                raise DistutilsOptionError("Directory {} to write jar must exist".format(dir_path))
            if os.path.splitext(self.output)[1] != ".jar":
                raise DistutilsOptionError("Path must be to a valid jar name, not {}".format(self.output))

    def get_jar_name(self):
        metadata = self.distribution.metadata
        return "{}-{}.jar".format(metadata.get_name(), metadata.get_version())

    def run(self):
        if not self.distribution.clamp:
            raise DistutilsOptionError("Specify the modules to be built into a jar  with the 'clamp' setup keyword")
        jar_dir = os.path.join(site.getsitepackages()[0], "jars")
        if not os.path.exists(jar_dir):
            os.mkdir(jar_dir)
        if self.output_jar_pth:
            jar_pth_path = os.path.join(site.getsitepackages()[0], "jar.pth")
            paths = read_pth(jar_pth_path)
            print "paths in jar.pth", paths
            paths[self.distribution.metadata.get_name()] = os.path.join("./jars", self.get_jar_name())
            write_jar_pth(jar_pth_path, paths)
        with closing(JarBuilder(output_path=self.output)) as builder:
            clamp.register_builder(builder)
            for module in self.distribution.clamp:
                __import__(module)


def find_jython_jars():
    """Uses the same classpath resolution as bin/jython"""
    # FIXME ensure no symbolic links using realpath
    jython_jar_path = os.path.join(sys.executable, "../../jython.jar")
    jython_jar_dev_path = os.path.join(sys.executable, "../../jython-dev.jar")
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
                print "ignoring dirpath", dirpath, sitepackages
                ignore = True
        if ignore:
            continue
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            relpath = path[len(root)-3:]   # this will of course not work for included directories FIXME bad hack!
            yield relpath, os.path.realpath(path)

    # FIXME verify realpath, realpath(dirpath) has not been seen (no cycles!)


# def find_setuptools_libs():
#     # need to take in account if zipped or not; then create appropriate entries

#     # 1. assume the file is zipped; if so copy over;
#     # 2. otherwise copy over 
#     # need to preserve the easy-install.pth order
    
#     seen = set()
#     sitepackages = site.getsitepackages()
#     root = os.path.normpath(os.path.join(sys.executable, "../../Lib"))
#     for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
#         ignore = False
#         for pkg in sitepackages:

def find_package_libs(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            relpath = path[len(root)+1:]
            yield relpath, path


def create_singlejar(output_path, classpath, include, runpy):
    jars = classpath
    jars.extend(find_jython_jars())
    site_path = site.getsitepackages()[0]
    jar_pth_path = os.path.join(site_path, "jar.pth")
    for jar_path in sorted(read_pth(jar_pth_path).itervalues()):
        print "Adding jar", jar_path
        jars.append(os.path.join(site_path, jar_path))
    
    with closing(JarCopy(output_path=output_path)) as singlejar:
        singlejar.copy_jars(jars)
        # add include roots
        for relpath, realpath in find_jython_lib_files():
            singlejar.copy_file(relpath, realpath)
        sitepackage = site.getsitepackages()[0]
        for path in read_pth(os.path.join(sitepackage, "easy-install.pth")).itervalues():
            relpath = os.path.normpath(os.path.join("Lib", path))
            path = os.path.realpath(os.path.normpath(os.path.join(sitepackage, path)))

            try:
                with open(path) as f:
                    with closing(ZipInputStream(f)) as input_zip:
                        singlejar.copy_zip_input_stream(input_zip)
                print "Copied zip file", path
            except IOError:
                print "Need to copy file tree", path
                for pkg_relpath, pkg_realpath in find_package_libs(path):
                    # Filter out egg metadata
                    parts = pkg_relpath.split(os.sep)
                    if len(parts) < 2:
                        continue
                    head = parts[0]
                    if head == "EGG-INFO" or head.endswith(".egg-info"):
                        continue
                    print "Copy file", pkg_realpath, "to", os.path.join("Lib", pkg_relpath)
                    singlejar.copy_file(pkg_relpath, pkg_realpath)

        if runpy and os.path.exists(runpy):
            singlejar.copy_file("__run__.py", runpy)


class singlejar(setuptools.Command):

    description = "create a singlejar of all Jython dependencies, including clamped jars"
    user_options = [
        ("output=",    "o",  "write jar to output path"),
        ("classpath=", None, "jars to include in addition to Jython runtime and site-packages jars"),  # FIXME take a list?
        ("include=",   "i",  "paths to additional Python libraries and other files to include"),  # FIXME ditto, take a list?
        ("runpy=",     "r",  "path to __run__.py to make a runnable jar"),
    ]

    def initialize_options(self):
        metadata = self.distribution.metadata
        jar_dir = os.path.join(site.getsitepackages()[0], "jars")
        try:
            os.mkdir(jar_dir)
        except OSError:
            pass
        self.output = os.path.join(os.getcwd(), "{}-{}-single.jar".format(metadata.get_name(), metadata.get_version()))
        self.classpath = []
        self.include = []
        self.runpy = os.path.join(os.getcwd(), "__run__.py")
            
    def finalize_options(self):
        # could validate self.output is a valid path FIXME
        if self.classpath:
            self.classpath = self.classpath.split(":")
        if self.include:
            self.include = self.include.split(":")

    def run(self):
        create_singlejar(self.output, self.classpath, self.include, self.runpy)



def singlejar_command():
    print "args", sys.argv
    clamp.build.create_singlejar("jython-single.jar", [], [], os.path.join(os.getcwd(), "__run__.py"))
