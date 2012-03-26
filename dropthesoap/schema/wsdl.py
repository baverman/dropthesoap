from . import xs
from .model import Namespace

namespace = Namespace('http://schemas.xmlsoap.org/wsdl/', 'wsdl')

types = xs.element('types')(xs.cts(
    xs.any(minOccurs=0)))

message = xs.element('message')(xs.cts(
    xs.element('part')
))

definitions = xs.element('definitions')(xs.cts(
    types,
))

schema = xs.schema(namespace)(
    definitions
)