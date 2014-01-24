# Declarative should do all type inference, etc, in
# ClampProxyMakerMeta (other than of course class decorator)

from clamp.proxymaker import ClampProxyMaker
from clamp.signature import Constant


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
