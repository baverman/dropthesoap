from dropthesoap.service import Service
from dropthesoap.schema import xs

from .helpers import tostring

def test_simple_service():
    s = Service('Boo', 'http://boo')

    @s.expose(returns=xs.int)
    def add(x=xs.int, y=xs.int):
        return x + y

    print s.get_wsdl('boo')

    assert False