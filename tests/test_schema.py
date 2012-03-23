from dropthesoap.schema import xs
from dropthesoap.schema.model import etree, Namespace, get_root

def test_simple_schema():
    AddRequest = xs.element('AddRequest')(
        xs.complexType()(
            xs.sequence()(
                xs.element('x', xs.string),
                xs.element('y', xs.string)
            )
        )
    )

    AddResponse = xs.element('AddResponse', xs.int_)

    schema = xs.schema(Namespace('http://boo', 'boo'))(
        AddRequest,
        AddResponse
    )

    print etree.tostring(get_root(schema))
    print etree.tostring(get_root(AddRequest.instance(x=10, y=15)))
    print etree.tostring(get_root(AddResponse.instance(15)))

    assert False