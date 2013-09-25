import setuptools
import time
from collections import Iterable
from contextlib import closing
from distutils.errors import DistutilsOptionError, DistutilsSetupError
from java.util.jar import Attributes, JarEntry, JarInputStream, JarOutputStream, Manifest

import clamp


class JarCopy(object):
    # http://rosettacode.org/wiki/Walk_a_directory/Recursively#Python

    # of course use os.path.walk or something like it, vs java's File;
    # perhaps it will even fixup paths properly on windows (probably
    # not - but maybe can do os.path.split, then rejoin with /)

    # looksl like i can do a very chaining together of JarInputStream to
    # JarOutputStream, then quite possibly add new entries at the end
    pass


class JarBuilder(object):
    
    # Derived, with heavy modifications, from
    # http://stackoverflow.com/questions/1281229/how-to-use-jaroutputstream-to-create-a-jar-file

    def __init__(self, jar=None, output_path="output.jar"):
        self.output_path = output_path
        if jar is not None:
            self.jar = jar
            return

        manifest = Manifest()
        manifest.getMainAttributes()[Attributes.Name.MANIFEST_VERSION] = "1.0"
        self.output = open(self.output_path, "wb")
        self.jar = JarOutputStream(self.output, manifest)
        self.created_paths = set()
        self.build_time = int(time.time() * 1000)

    def close(self):
        self.jar.close()
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
                "clamp={} is invalid, must be an iterable of importable module names".format(values))
    except TypeError, ex:
        print type(ex), ex
        raise DistutilsSetupError("clamp={} is invalid: {}".format(values, ex))
    distribution.clamp = clamped


class buildjar(setuptools.Command):

    description = "create a jar for all clamped Python classes"
    user_options = [
        ("output=",   "o", "output jar (defaults to output.jarpatterns to match (required)"),
    ]

    def initialize_options(self):
        metadata = self.distribution.metadata
        self.output = "{}-{}.jar".format(metadata.get_name(), metadata.get_version())

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


