from dropthesoap.schema import soap, xs
from dropthesoap.schema.model import Namespace

from .helpers import tostring

def test_soap_envelope_construction():
    Request = xs.element('Request', xs.int)

    schema = xs.schema(Namespace('http://boo'))(
        Request
    )

    envelope = soap.Envelope.instance(Body=soap.Body.instance(_any=[Request.instance(50)]))

    envelope = soap.schema.fromstring(tostring(envelope))
    request = schema.from_node(envelope.Body._any[0])

    assert request == 50