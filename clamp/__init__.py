import java
import os
import os.path

from java.lang.reflect import Modifier
from org.python.util import CodegenUtils
from org.python.compiler import CustomMaker, ProxyCodeHelpers


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

    # TODO support fields, along with property support in Python

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

        # FIXME only add serialVersionUID if the class in question
        # actually is (transitively) implementing Serializable
        # (presumably already part of the MRO by time we are called
        # here - not certain if visible to this code however)

        self.constants = { "serialVersionUID" : (java.lang.Long(1), java.lang.Long.TYPE) }
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
            # If already defined on CLASSPATH/classloader chain, simply return this class
            # if you need to tune this, derive accordingly from this class or create another CustomMaker
            cls = java.lang.Class.forName(self.myClass)
            print "Looked up proxy", self.myClass
        except:
            if _builder:
                print "Calling super...", self.package
                cls = CustomMaker.makeClass(self)
                print "Built proxy", self.myClass
            else:
                raise TypeError("Cannot construct class without a defined builder FIXME better err msg")
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

