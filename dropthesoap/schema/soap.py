from . import xs
from .model import Namespace, get_root, etree

namespace = Namespace('http://schemas.xmlsoap.org/soap/envelope/', 'soap')

schema = xs.schema(namespace)(
    xs.element('Envelope', xs.cts(
        xs.element('Header', xs.optional(xs.cts(
            xs.any(minOccurs=0, maxOccurs=xs.unbounded)))),
        xs.element('Body', xs.optional(xs.cts(
            xs.any(minOccurs=0, maxOccurs=xs.unbounded)))),
    )),
    xs.element('Fault', xs.cts(
        xs.element('faultcode', xs.string),
        xs.element('faultstring', xs.string),
        xs.element('faultactor', xs.optional(xs.string)),
        xs.element('detail', xs.optional(xs.string)),
    )),
)

Envelope = schema['Envelope']
Fault = schema['Fault']


def make_envelope(response=None, header=None):
    envelope = {}
    if response:
        envelope['Body'] = {'_any': [response]}
    if header:
        envelope['Header'] = {'_any': [header]}

    return Envelope.normalize(envelope)


def response_tostring(response=None, header=None):
    renvelope = make_envelope(response, header)
    tree = get_root(renvelope)
    tree.attrib['soap:encodingStyle'] = 'http://www.w3.org/2001/12/soap-encoding'
    return etree.tostring(tree, encoding='utf-8')
