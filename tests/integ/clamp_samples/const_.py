from java.lang import Long, Object
from clamp import clamp_base, Constant

TestBase = clamp_base("org")


class ConstSample(TestBase, Object):
    myConstant = Constant(Long(1234), Long.TYPE)