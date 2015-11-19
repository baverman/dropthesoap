from . import xs
from .model import Namespace

# soap elements
soap_binding = xs.element('binding')(
    xs.complexType()(
        xs.attribute('transport', xs.string),
        xs.attribute('style', xs.string)))

soap_operation = xs.element('operation', minOccurs=0)(
    xs.complexType()(
        xs.attribute('soapAction', xs.string)))

soap_body = xs.element('body', minOccurs=0)(
    xs.complexType()(
        xs.attribute('use', xs.string)))

soap_header = xs.element('header', minOccurs=0)(
    xs.complexType()(
        xs.attribute('use', xs.string),
        xs.attribute('message', xs.string),
        xs.attribute('part', xs.string)))

soap_address = xs.element('address', minOccurs=0)(
    xs.complexType()(
        xs.attribute('location', xs.string)))

soap_schema = xs.schema(Namespace('http://schemas.xmlsoap.org/wsdl/soap/', 'soap'))(
    soap_binding,
    soap_operation,
    soap_body,
    soap_header,
    soap_address
)


# wsdl elements
types = xs.element('types')(xs.cts(
    xs.any(minOccurs=0, maxOccurs=xs.unbounded)))

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
        xs.sequence()(
            soap_body,
            soap_header),
        xs.attribute('message', xs.string)))

output = xs.element('output')(
    xs.complexType()(
        xs.sequence()(
            soap_body),
        xs.attribute('message', xs.string)))

operation = xs.element('operation', minOccurs=0, maxOccurs=xs.unbounded)(
    xs.complexType()(
        xs.sequence()(
            soap_operation,
            input,
            output),
        xs.attribute('name', xs.string)))

portType = xs.element('portType', minOccurs=0, maxOccurs=xs.unbounded)(
    xs.complexType()(
        xs.sequence()(
            operation),
        xs.attribute('name', xs.string)))

binding = xs.element('binding', minOccurs=0, maxOccurs=xs.unbounded)(
    xs.complexType()(
        xs.sequence()(
            soap_binding,
            operation),
        xs.attribute('name', xs.string),
        xs.attribute('type', xs.string)))

port = xs.element('port')(
    xs.complexType()(
        xs.sequence()(
            soap_address),
        xs.attribute('binding', xs.string),
        xs.attribute('name', xs.string)))

service = xs.element('service', minOccurs=0, maxOccurs=xs.unbounded)(
    xs.complexType()(
        xs.sequence()(
            port),
        xs.attribute('name', xs.string)))

definitions = xs.element('definitions')(xs.cts(
    types,
    message,
    portType,
    binding,
    service))

schema = xs.schema(Namespace('http://schemas.xmlsoap.org/wsdl/', 'wsdl'))(
    definitions
)
