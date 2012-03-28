from suds.client import Client

from dropthesoap.service import Service, optional
from dropthesoap.schema import xs

from .helpers import DirectSudsTransport

def test_simple_service():
    service = Service('Boo', 'http://boo')

    @service.expose(returns=xs.int)
    def add(x=xs.int, y=xs.int):
        return x + y

    #open('/tmp/wow.xml', 'w').write(service.get_wsdl('http://localhost/'))

    cl = Client('some address', transport=DirectSudsTransport(service), cache=None)

    result = cl.service.add(1, 10)
    assert result == 11

def test_optional_arguments_service():
    service = Service('Boo', 'http://boo')

    @service.expose(returns=xs.int)
    def add(x=xs.int, y=optional(xs.int)):
        if y is None:
            return 1
        return 0

    cl = Client('some address', transport=DirectSudsTransport(service), cache=None)

    result = cl.service.add(1)
    assert result == 1

def test_complex_return_type():
    service = Service('Boo', 'http://boo')

    ResponseType = xs.complexType(name='ResponseType')(
        xs.sequence()(
            xs.element('foo', xs.string),
            xs.element('bar', xs.string)))

    service.schema(
        ResponseType
    )

    @service.expose(returns=ResponseType)
    def add(x=xs.int, y=xs.int):
        return ResponseType.instance(foo=x+y, bar=x-y)

    #open('/tmp/wow.xml', 'w').write(service.get_wsdl('http://localhost/'))

    cl = Client('some address', transport=DirectSudsTransport(service), cache=None)

    result = cl.service.add(1, 10)
    print result
    assert result.foo == '11'
    assert result.bar == '-9'