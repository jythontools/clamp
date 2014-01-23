import logging
import os
import os.path
import setuptools
from contextlib import contextmanager
from distutils.errors import DistutilsOptionError, DistutilsSetupError

from build import create_singlejar, build_jar

logging.basicConfig()
log = logging.getLogger("clamp") # __name__)


@contextmanager
def honor_verbosity(verbose):
    if verbose:
        old_level = log.getEffectiveLevel()
        log.setLevel(logging.DEBUG)
    yield
    if verbose:
        log.setLevel(old_level)


def validate_clamp_keyword(distribution, keyword, values):
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
        log.error("Invalid clamp", exc_info=True)
        raise DistutilsSetupError("clamp={} is invalid: {}".format(values, ex))
    distribution.clamp = clamped


class build_jar_command(setuptools.Command):

    description = "create a jar for all clamped Python classes for this package"
    user_options = [
        ("output=",   "o", "write jar to output path"),
    ]

    def initialize_options(self):
        self.output = None

    def finalize_options(self):
        if self.output is not None:
            dir_path = os.path.split(self.output)[0]
            if dir_path and not os.path.exists(dir_path):
                raise DistutilsOptionError("Directory {} to write jar must exist".format(dir_path))
            if os.path.splitext(self.output)[1] != ".jar":
                raise DistutilsOptionError("Path must be to a valid jar name, not {}".format(self.output))

    def get_jar_name(self):
        metadata = self.distribution.metadata
        return "{}-{}.jar".format(metadata.get_name(), metadata.get_version())

    def run(self):
        with honor_verbosity(self.distribution.verbose):
            if not self.distribution.clamp:
                raise DistutilsOptionError("Specify the modules to be built into a jar  with the 'clamp' setup keyword")
            build_jar(self.distribution.metadata.get_name(),
                      self.get_jar_name(), self.distribution.clamp, self.output)



class clamp_command(setuptools.Command):

    description = "create a jar for all clamped Python classes for this package"
    user_options = [
        ("output=",   "o", "write jar to output path"),
    ]

    def initialize_options(self):
        self.output = None

    def finalize_options(self):
        if self.output is not None:
            dir_path = os.path.split(self.output)[0]
            if dir_path and not os.path.exists(dir_path):
                raise DistutilsOptionError("Directory {} to write jar must exist".format(dir_path))
            if os.path.splitext(self.output)[1] != ".jar":
                raise DistutilsOptionError("Path must be to a valid jar name, not {}".format(self.output))

    def get_jar_name(self):
        metadata = self.distribution.metadata
        return "{}-{}.jar".format(metadata.get_name(), metadata.get_version())

    def run(self):
        with honor_verbosity(self.distribution.verbose):
            if not self.distribution.clamp:
                raise DistutilsOptionError("Specify the modules to be built into a jar  with the 'clamp' setup keyword")
            build_jar(self.distribution.metadata.get_name(),
                      self.get_jar_name(), self.distribution.clamp, self.output)


class singlejar_command(setuptools.Command):

    description = "create a singlejar of all Jython dependencies, including clamped jars"
    user_options = [
        ("output=",    "o",  "write jar to output path"),
        ("classpath=", None, "jars to include in addition to Jython runtime and site-packages jars"),  # FIXME take a list?
        ("runpy=",     "r",  "path to __run__.py to make a runnable jar"),
    ]

    def initialize_options(self):
        metadata = self.distribution.metadata
        self.output = os.path.join(os.getcwd(), "{}-{}-single.jar".format(metadata.get_name(), metadata.get_version()))
        self.classpath = []
        self.runpy = os.path.join(os.getcwd(), "__run__.py")
            
    def finalize_options(self):
        # could validate self.output is a valid path FIXME
        if self.classpath:
            self.classpath = self.classpath.split(":")

    def run(self):
        with honor_verbosity(self.distribution.verbose):
            create_singlejar(self.output, self.classpath, self.runpy)


def singlejar_script_command():
    parser = argparse.ArgumentParser(description="create a singlejar of all Jython dependencies, including clamped jars")
    parser.add_argument("--output", "-o", default="jython-single.jar", metavar="PATH",
                        help="write jar to output path")
    parser.add_argument("--classpath", default=None,
                        help="jars to include in addition to Jython runtime and site-packages jars")
    parser.add_argument("--runpy", "-r", default=os.path.join(os.getcwd(), "__run__.py"), metavar="PATH",
                        help="path to __run__.py to make a runnable jar")
    args = parser.parse_args()
    if args.classpath:
        args.classpath = args.classpath.split(":")
    else:
        args.classpath = []
    create_singlejar(args.output, args.classpath, args.runpy)
