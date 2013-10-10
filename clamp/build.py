import java
import setuptools
import jarray
import os.path
import site
import time

from contextlib import closing  # FIXME maybe directly support a context manager interface
from distutils.errors import DistutilsOptionError, DistutilsSetupError
from java.util.jar import Attributes, JarEntry, JarInputStream, JarOutputStream, Manifest

import clamp


class OutputJar(object):

    # Derived, with heavy modifications, from
    # http://stackoverflow.com/questions/1281229/how-to-use-jaroutputstream-to-create-a-jar-file

    # FIXME include in site-packages? if so, we will need to add to
    # 

    def __init__(self, jar=None, output_path="output.jar"):
        self.output_path = output_path
        if jar is not None:
            self.jar = jar
            self.output = None
            return

        manifest = Manifest()
        manifest.getMainAttributes()[Attributes.Name.MANIFEST_VERSION] = "1.0"
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
            if ancestor not in self.created_paths:
                print "Adding", ancestor
                entry = JarEntry(ancestor)
                entry.time = self.build_time
                self.jar.putNextEntry(entry)
                self.jar.closeEntry()
                self.created_paths.add(path_parts[:-i])


class JarCopy(OutputJar):
    # Given a CLASSPATH, adds every jar on list to jar
    # Then adds Jython jar itself, using the jython script resolution
    # Then adds Jython Lib, including site-packages
    # Then the result of JarBuilder
    # Lastly adds an optional __run__.py

    # Should also support an incremental version to faciliate
    # development, starting with site-packages and the following steps

    # http://rosettacode.org/wiki/Walk_a_directory/Recursively#Python

    # of course use os.path.walk or something like it, vs java's File;
    # perhaps it will even fixup paths properly on windows (probably
    # not - but maybe can do os.path.split, then rejoin with /)

    # looksl like i can do a very chaining together of JarInputStream to
    # JarOutputStream, then quite possibly add new entries at the end

    def copy(self, f):
        """Given a file handle `f`, copy to the jar"""

        chunk = jarray.zeros(8192, 'b')
        with closing(JarInputStream(f)) as input_jar:
            while True:
                entry = input_jar.getNextEntry()
                if entry is None:
                    break
                try:
                    # Cannot simply use old entry because we need
                    # to recompute compressed size
                    output_entry = JarEntry(entry.getName())
                    # FIXME add timestamp
                    self.jar.putNextEntry(output_entry)
                    while True:
                        read = input_jar.read(chunk, 0, 8192)
                        if read == -1:
                            break
                        self.jar.write(chunk, 0, read)
                    self.jar.closeEntry()
                except java.util.zip.ZipException, e:
                    if not "duplicate entry" in str(e):
                        print "Problem in copying entry", output_entry
                        raise

    # use os.path.realpath to ensure we don't keep traversing symbolic links
    # def add_file(self, path):
    #     # need to compute relpath
    #     # eg Lib/..., Lib/site-packages, ...
    #     self.create_ancestry(...)
    #     os.path.getmtime(path)

    # move jars in site-packages/jars/* to top level; don't copy over jar.pth

    def copy_classpath(self, classpath):
        for path in classpath.split(":"):
            if path.endswith(".jar"):
                with open(path) as f:
                    print "Copying", path
                    self.copy(f)

    # need the following functions: copy_classpath (as specified explicitly); copy jython jars (including Lib, if available); copy site-packages (possibly mutltiple), into Lib; copy jars from jars/*.jar, based on what is directed in jar.pth (ignore other jars)


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


# FIXME no need to use this crap apparently, just modify site-packages directory directly

def write_arg(cmd, basename, filename):  # FIXME change this name to write_jar
    metadata = cmd.distribution.metadata
    output = "{}-{}.jar".format(metadata.get_name(), metadata.get_version())  # FIXME extract util fn
    clamp = getattr(cmd.distribution, "clamp")
    if clamp is not None:
        argname = os.path.splitext(basename)[0]
        cmd.write_or_delete_file(argname, filename, output)

    print "!!! Got this", cmd, cmd.egg_info, output, clamp, basename, filename







class buildjar(setuptools.Command):

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

    def get_package_name(self, path):
        return "-".join(os.path.split(path)[1].split("-")[:-1])

    def read_jar_pth(self, jar_pth_path):
        paths = {}
        if os.path.exists(jar_pth_path):
            with open(jar_pth_path) as jar_pth:
                for jar_path in jar_pth:
                    jar_path = jar_path.strip()
                    if jar_path.startswith("#"):
                        continue  # FIXME consider preserving comments, other user changes
                    name = self.get_package_name(os.path.split(jar_path)[1])
                    paths[name] = jar_path
        return paths

    def write_jar_pth(self, jar_pth_path, paths):
        with open(jar_pth_path, "w") as jar_pth:
            for name, path in sorted(paths.iteritems()):
                jar_pth.write(path + "\n")

    def run(self):
        if not self.distribution.clamp:
            raise DistutilsOptionError("Specify the modules to be built into a jar  with the 'clamp' setup keyword")
        jar_dir = os.path.join(site.getsitepackages()[0], "jars")
        if not os.path.exists(jar_dir):
            os.mkdir(jar_dir)
        if self.output_jar_pth:
            jar_pth_path = os.path.join(site.getsitepackages()[0], "jar.pth")
            paths = self.read_jar_pth(jar_pth_path)
            paths[self.distribution.metadata.get_name()] = os.path.join("./jars", self.get_jar_name())
            self.write_jar_pth(jar_pth_path, paths)
        with closing(JarBuilder(output_path=self.output)) as builder:
            clamp.register_builder(builder)
            for module in self.distribution.clamp:
                __import__(module)



class singlejar(setuptools.Command):

    # FIXME should ensure __run__.py is used

    # import site; site.getsitepackages() - apparently there can be more than one

    # FIXME we need some mechanism by which clamped packages can place
    # their jars in their package, then this can vacuum up; perhaps
    # best by just defaulting buildjar to go to site-packages, then
    # just scan for them; maybe it should be at the top-level? or can we play with sys.path in some way?


    description = "create a singlejar of all Jython dependencies, including clamped classes"
    user_options = [
        ("output=",    "o",  "output jar (defaults to 'output.jar')"),
        ("classpath=", "cp", "jars to include in addition to Jython runtime jar and clamped jar"),

    ]

    def initialize_options(self):
        metadata = self.distribution.metadata
        jar_dir = os.path.join(site.getsitepackages()[0], "jars")
        try:
            os.mkdir(jar_dir)
        except OSError:
            pass
        self.output = os.path.join(jar_dir, "{}-{}.jar".format(metadata.get_name(), metadata.get_version()))

    def finalize_options(self):
        # could validate self.output is a valid path FIXME
        pass

    def run(self):
        if not self.distribution.clamp:
            raise DistutilsOptionError("Specify the modules to be built into a jar  with the 'clamp' setup keyword")
        with closing(JarBuilder(output_path=self.output)) as builder:
            clamp.register_builder(builder)
            for module in self.distribution.clamp:
                __import__(module)



