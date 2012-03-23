from StringIO import StringIO
from dropthesoap.schema import xs
from dropthesoap.schema.model import etree, Namespace, get_root

from lxml import etree as lxml_etree

def validate(schema, instance):
    schema_doc = lxml_etree.parse(StringIO(etree.tostring(get_root(schema))))
    xmlschema = lxml_etree.XMLSchema(schema_doc)

    doc = lxml_etree.parse(StringIO(etree.tostring(get_root(instance))))
    return xmlschema.validate(doc)

def test_simple_schema():
    AddRequest = xs.element('AddRequest')(
        xs.complexType()(
            xs.sequence()(
                xs.element('x', xs.string),
                xs.element('y', xs.string))))

    AddResponse = xs.element('AddResponse', xs.int_)

    schema = xs.schema(Namespace('http://boo', 'boo'))(
        AddRequest,
        AddResponse
    )

    assert validate(schema, AddRequest.instance(x=10, y=15))
    assert validate(schema, AddResponse.instance(15))