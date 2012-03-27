from . import xs
from .model import Namespace

namespace = Namespace('http://schemas.xmlsoap.org/wsdl/', 'wsdl')

types = xs.element('types')(xs.cts(
    xs.any(minOccurs=0)))

part = xs.element('part')(
    xs.complexType()(
        xs.attribute('name', xs.string),
        xs.attribute('element', xs.string)))

message = xs.element('message', minOccurs=0, maxOccurs=xs.unbounded)(
    xs.complexType()(
        xs.sequence()(
            part),
        xs.attribute('name', xs.string)))

input = xs.element('input')(
    xs.complexType()(
        xs.attribute('message', xs.string)))

output = xs.element('output')(
    xs.complexType()(
        xs.attribute('message', xs.string)))

operation = xs.element('operation', minOccurs=0, maxOccurs=xs.unbounded)(
    xs.complexType()(
        xs.sequence()(
            input,
            output),
        xs.attribute('name', xs.string)))

portType = xs.element('portType', minOccurs=0, maxOccurs=xs.unbounded)(
    xs.complexType()(
        xs.sequence()(
            operation),
        xs.attribute('name', xs.string)))

definitions = xs.element('definitions')(xs.cts(
    types,
    message,
    portType))

schema = xs.schema(namespace)(
    definitions
)