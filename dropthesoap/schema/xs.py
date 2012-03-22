from .model import Model, Namespace

namespace = Namespace('http://www.w3.org/2001/XMLSchema', 'xs')

class element(Model):
    __namespace__ = namespace


class sequence(Model):
    __namespace__ = namespace


class complexType(Model):
    __namespace__ = namespace


class string(Model):
    __namespace__ = namespace

    def __init__(self, value):
        Model.__init__(self)
        self._value = unicode(value)


class int_(Model):
    __namespace__ = namespace
    def __init__(self, value):
        Model.__init__(self)
        self._value = int(value)


class float_(Model):
    __namespace__ = namespace
    def __init__(self, value):
        Model.__init__(self)
        self._value = float(value)
