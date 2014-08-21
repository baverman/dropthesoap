from dropthesoap.schema import soap, xs
from dropthesoap.schema.model import Namespace

from .helpers import tostring


def test_soap_envelope_construction():
    schema = xs.schema(Namespace('http://boo'))(
        xs.element('Request', xs.int)
    )

    envelope = soap.make_envelope(schema['Request'].instance(50))

    envelope = soap.schema.fromstring(tostring(envelope))
    request = schema.from_node(envelope.Body._any[0])

    assert request == 50
