from suds.client import Client
from suds.client import WebFault

from dropthesoap.service import Service, optional, Fault, array
from dropthesoap.schema import xs

from .helpers import DirectSudsTransport, tostring

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

    service.schema(
        xs.element('addResponse')(xs.cts(
            xs.element('foo', xs.string),
            xs.element('bar', xs.string)))
    )

    @service.expose
    def add(x=xs.int, y=xs.int):
        return {'foo': str(x+y), 'bar': str(x-y)}

    #open('/tmp/wow.xml', 'w').write(service.get_wsdl('http://localhost/'))

    cl = Client('some address', transport=DirectSudsTransport(service), cache=None)

    result = cl.service.add('1', '10')
    assert result.foo == '11'
    assert result.bar == '-9'

def test_aliased_types_in_params():
    service = Service('Boo', 'http://boo')

    service.schema(
        xs.complexType(name='paramType')(xs.sequence()(
            xs.element('foo', xs.string)))
    )

    @service.expose(xs.string)
    def concat(param=array('paramType')):
        return ''.join(r.foo for r in param)

    open('/tmp/wow.xml', 'w').write(service.get_wsdl('http://localhost/'))

    cl = Client('some address', transport=DirectSudsTransport(service), cache=None)

    result = cl.service.concat([{'foo':'boo'}, {'foo':'bar'}])
    assert result == 'boobar'


def test_header():
    service = Service('Boo', 'http://boo')

    service.schema(
        xs.element('AuthHeader')(xs.cts(
            xs.element('what', xs.string)))
    )


    def auth(func):
        @service.header('AuthHeader')
        @service.wraps(func)
        def inner(request, *args):
            if request.header.what == 'auth':
                return func(*args)
            else:
                return 'blam'

        return inner

    @auth
    @service.expose(xs.string)
    def upper(string=xs.string):
        return string.upper()

    #open('/tmp/wow.xml', 'w').write(service.get_wsdl('http://localhost/'))

    cl = Client('some address', transport=DirectSudsTransport(service), cache=None)

    token = cl.factory.create('AuthHeader')
    token.what = 'auth'
    cl.set_options(soapheaders=token)
    result = cl.service.upper('boo')
    assert result == 'BOO'

    token = cl.factory.create('AuthHeader')
    token.what = 'abracadabra'
    cl.set_options(soapheaders=token)
    result = cl.service.upper('boo')
    assert result == 'blam'

def test_faults():
    service = Service('Boo', 'http://boo')

    @service.expose(xs.string)
    def upper(string=xs.string):
        if string == 'boo':
            raise Exception('Boo')
        if string == 'bar':
            raise Fault('Client.Auth', 'Authentication failed')

    cl = Client('some address', transport=DirectSudsTransport(service), cache=None)

    try:
        result = cl.service.upper('boo')
        assert False, 'WebFault must be thrown'
    except WebFault as e:
        assert e.fault.faultcode == 'Server'
        assert e.fault.faultstring == 'Boo'
        assert 'in upper' in e.fault.detail

    try:
        result = cl.service.upper('bar')
        assert False, 'WebFault must be thrown'
    except WebFault as e:
        assert e.fault.faultcode == 'Client.Auth'
        assert e.fault.faultstring == 'Authentication failed'
        assert not hasattr(e, 'detail')