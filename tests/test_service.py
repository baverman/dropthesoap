from suds.client import Client

from dropthesoap.service import Service
from dropthesoap.schema import xs

from .helpers import DirectSudsTransport

def test_simple_service():
    service = Service('Boo', 'http://boo')

    @service.expose(returns=xs.int)
    def add(x=xs.int, y=xs.int):
        return x + y

    open('/tmp/wow.xml', 'w').write(service.get_wsdl('http://localhost/'))

    cl = Client('some address', transport=DirectSudsTransport(service), cache=None)

    result = cl.service.add(1, 10)
    assert result == 11
