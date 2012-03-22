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

    AddResponse = xs.element(type=xs.int_)

    print etree.tostring(AddRequest.get_node())

    assert False