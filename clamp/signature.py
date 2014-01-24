class Constant(object):
    """ Use this class to declare class attributes as java const

    Example::

        class Test(BarClamp, Callable, Serializable):

            serialVersionUID = Constant(Long(1234), Long.TYPE)
    """

    def __init__(self, value, type=None):
        # FIXME do type inference on value_type when we have that
        if type is None:
            raise NotImplementedError("type has to be set right now")
        self.value = value
        self.type = type
