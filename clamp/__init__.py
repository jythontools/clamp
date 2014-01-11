import java
import os
import os.path

from java.io import Serializable
from java.lang.reflect import Modifier
from org.python.core import Py
from org.python.compiler import CustomMaker, ProxyCodeHelpers
from org.python.util import CodegenUtils


__all__ = ["ClampProxyMaker"]


# FIXME maybe this should be supported with a context manager; we
# could also do this in the context of a threadlocal; however, this is
# currently just used by setup.py in an indirect fashion, so probably
# OK

_builder = None

def register_builder(builder):
    global _builder
    old_builder = _builder
    _builder = builder
    return old_builder


class SerializableProxyMaker(CustomMaker):

    # FIXME and push in docs presumably - in general, unless user otherwise specifies,
    # serialVersionUID of 1 is OK for python, thanks to dynamic
    # typing. Other errors -not having the right interface support
    # - will be caught earlier anyway.

    # NOTE: SerializableProxyMaker is itself a java proxy, but it's not a custom one!

    # TODO support fields in conjunction with property support in Python

# (None, 
#  array(java.lang.Class, [<type 'java.util.concurrent.Callable'>, <type 'java.io.Serializable'>]),
#  u'BarClamp',
#  u'__main__',
#  u'clamped.__main__.BarClamp',
#  {'__init__': <function __init__ at 0x2>, '__module__': '__main__', 'call': <function call at 0x3>, '__proxymaker__': <clamp.ClampProxyMaker object at 0x4>}, 'clamped', {})

    def __init__(self, superclass, interfaces, className, pythonModuleName, fullProxyName, mapping, package, kwargs):
        self.package = package
        self.kwargs = kwargs
        
        print "superclass=%s, interfaces=%s, className=%s, pythonModuleName=%s, fullProxyName=%s, mapping=%s, package=%s, kwargs=%s" % (superclass, interfaces, className, pythonModuleName, fullProxyName, mapping, package, kwargs)

        # FIXME break this out
        is_serializable = False
        inheritance = list(interfaces)
        if superclass:
            inheritance.append(superclass)
        for cls in inheritance:
            if issubclass(cls, Serializable):
                is_serializable = True

        if is_serializable:
            self.constants = { "serialVersionUID" : (java.lang.Long(1), java.lang.Long.TYPE) }
        else:
            self.constants = {}
        if "constants" in kwargs:
            self.constants.update(self.kwargs["constants"])
        CustomMaker.__init__(self, superclass, interfaces, className, pythonModuleName, fullProxyName, mapping)
    
    def doConstants(self):
        # FIXME eg, self.constants = { "fortytwo": (java.lang.Long(42), java.lang.Long.TYPE) }
        print "Constants", self.constants
        code = self.classfile.addMethod("<clinit>", ProxyCodeHelpers.makeSig("V"), Modifier.STATIC)
        for constant, (value, constant_type) in sorted(self.constants.iteritems()):
            self.classfile.addField(
                constant,
                CodegenUtils.ci(constant_type), Modifier.PUBLIC | Modifier.STATIC | Modifier.FINAL)
            code.visitLdcInsn(value)
            code.putstatic(self.classfile.name, constant, CodegenUtils.ci(constant_type))
        code.return_()

    def saveBytes(self, bytes):
        global _builder
        if _builder:
            _builder.saveBytes(self.package, self.myClass, bytes)

    def makeClass(self):
        global _builder
        print "Entering makeClass", self
        try:
            import sys
            print "sys.path", sys.path
            # If already defined on sys.path (including CLASSPATH), simply return this class
            # if you need to tune this, derive accordingly from this class or create another CustomMaker
            cls = Py.findClass(self.myClass)
            print "Looked up proxy", self.myClass, cls
            if cls is None:
                raise TypeError("No proxy class")
        except:
            if _builder:
                print "Calling super...", self.package
                cls = CustomMaker.makeClass(self)
                print "Built proxy", self.myClass
            else:
                raise TypeError("FIXME better err msg - Cannot construct class without a defined builder")
        return cls


class ClampProxyMaker(object):

    def __init__(self, package, **kwargs):
        self.package = package
        self.kwargs = kwargs
    
    def __call__(self, superclass, interfaces, className, pythonModuleName, fullProxyName, mapping):
        """Constructs a usable proxy name that does not depend on ordering"""
        print "ClampProxyMaker:", self.package, superclass, interfaces, className, pythonModuleName, fullProxyName, mapping
        return SerializableProxyMaker(
            superclass, interfaces, className, pythonModuleName,
            self.package + "." + pythonModuleName + "." + className, mapping,
            self.package, self.kwargs)


def clamp_base(package, proxy_maker=ClampProxyMaker):
    """ A helper method that allows you to create clamped classes

    Example::

        BarClamp = clamp_base(package='bar')


        class Test(BarClamp, Callable, Serializable):

            def __init__(self):
                print "Being init-ed", self

            def call(self):
                print "foo"
                return 42
    """

    def _clamp_closure(package, proxy_maker):
        """This closure sets the metaclass with our desired attributes
        """
        class ClampProxyMakerMeta(type):

            def __new__(cls, name, bases, dct):
                newdct = dict(dct)
                newdct['__proxymaker__'] = proxy_maker(package=package)
                return type.__new__(cls, name, bases, newdct)

        return ClampProxyMakerMeta


    class ClampBase(object):
        """Allows us not to have to set the __metaclass__ at all"""
        __metaclass__ = _clamp_closure(package=package, proxy_maker=proxy_maker)

    return ClampBase
