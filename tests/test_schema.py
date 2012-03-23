from dropthesoap.schema import xs
from dropthesoap.schema.model import etree

def test_simple_schema():
    AddRequest = xs.element(name='AddRequest')(
        xs.complexType()(
            xs.sequence()(
                xs.element(name='x', type=xs.string),
                xs.element(name='y', type=xs.string)
            )
        )
    )

    AddResponse = xs.element(name='AddResponse', type=xs.int_)

    print etree.tostring(AddRequest.get_node())
    print etree.tostring(AddRequest.instance(x=10, y=15).get_node())
    print etree.tostring(AddResponse.instance(15).get_node())

    assert False