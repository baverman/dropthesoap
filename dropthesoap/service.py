from functools import wraps

from .schema import xs, soap
from .schema.model import Namespace

class customize(object):
    def __init__(self, type, minOccurs=None, maxOccurs=None, default=None, nillable=None):
        self.attributes = locals().copy()
        del self.attributes['self']
        del self.attributes['type']
        self.type = type

    def get_element(self, name):
        return xs.element(name, self.type, **self.attributes)

class optional(customize):
    def __init__(self, type):
        customize.__init__(self, type, minOccurs=0)


class array(customize):
    def __init__(self, type):
        customize.__init__(self, type, minOccurs=0, maxOccurs=xs.unbounded)


class Service(object):
    def __init__(self, name, tns):
        self.name = name
        self.methods = {}

        self.method_schema = xs.schema(Namespace(tns))
        self.schema = xs.schema(Namespace(tns))

    def expose(self, returns=None):
        def inner(func):
            name = func.__name__
            defaults = func.__defaults__
            names = func.__code__.co_varnames[-len(defaults):]

            celements = []
            for n, t in zip(names, defaults):
                if isinstance(t, customize):
                    celements.append(t.get_element(n))
                else:
                    celements.append(xs.element(n, t))

            request = xs.element(name=name)(
                xs.complexType()(
                    xs.sequence()(*celements)))

            self.method_schema(request)
            self.schema(request)

            if returns:
                rname = name + 'Response'
                if isinstance(returns, customize):
                    response = returns.get_element(rname)
                else:
                    response = xs.element(rname, returns)

                self.schema(response)

            self.methods[name] = func
            return func

        return inner

    def get_wsdl(self, url):
        return 'Boo'

    def execute(self, xml):
        pass