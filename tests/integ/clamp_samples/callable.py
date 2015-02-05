from java.io import Serializable
from java.util.concurrent import Callable

from clamp import clamp_base


TestBase = clamp_base("org")


class CallableSample(TestBase, Callable, Serializable):

    def call(self):
        return 42