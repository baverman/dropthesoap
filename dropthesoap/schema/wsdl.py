from . import xs
from .model import Namespace

namespace = Namespace('http://schemas.xmlsoap.org/wsdl/', 'wsdl')

types = xs.element('types')(xs.cts(
    xs.any(minOccurs=0)))

message = xs.element('message', minOccurs=0, maxOccurs=xs.unbounded)(
    xs.complexType()(
        xs.sequence()(
            xs.element('part')(
                xs.complexType()(
                    xs.attribute('name', xs.string),
                    xs.attribute('element', xs.string)
                )
            )
        ),
        xs.attribute('name', xs.string)
    )
)

definitions = xs.element('definitions')(xs.cts(
    types,
    message,
))

schema = xs.schema(namespace)(
    definitions
)