from .model import Node, Namespace, Type, Instance
from ..utils import cached_property

namespace = Namespace('http://www.w3.org/2001/XMLSchema', 'xs')

def extract_type(value):
    return value if type(value) is type else value.__class__

def is_type(value):
    return (type(value) is type and issubclass(value, Type)) or isinstance(value, Type)


class element(Node):
    __namespace__ = namespace

    def __init__(self, **kwargs):
        Node.__init__(self, **kwargs)

        etype = self.attributes.get('type', None)
        if etype is not None:
            self.attributes['type'] = etype.ptag
            self.type = extract_type(etype)

        if 'name' in self.attributes:
            self.name = self.attributes['name']

    def __call__(self, *children):
        Node.__call__(self, *children)
        for c in children:
            if is_type(c):
                self.type = extract_type(c)
                break

        return self

    def instance(self, *args, **kwargs):
        return self.type.instance_class(self.name, *args, **kwargs)


class sequence(Node):
    __namespace__ = namespace

    @cached_property
    def element_dict(self):
        result = {}
        for c in self.children:
            if isinstance(c, element):
                result[c.name] = c

        return result

    @cached_property
    def element_list(self):
        return [c for c in self.children if isinstance(c, element)]

    def init(self, instance, **kwargs):
        elements = self.element_dict
        for name, value in kwargs.iteritems():
            if name not in elements:
                raise Exception("Can't found [%s] in sequence")

            setattr(instance, name, value)

    def fill_node(self, node, instance):
        for e in self.element_list:
            if hasattr(instance, e.name):
                value = getattr(instance, e.name)
                if isinstance(value, Instance):
                    node.append(value.get_node())
                else:
                    node.append(e.instance(value).get_node())
            else:
                raise Exception('Boo')


class complexType(Type):
    __namespace__ = namespace
    type_counter = 0

    def __call__(self, *children):
        complexType.type_counter += 1
        name = 'ComplexType{}'.format(complexType.type_counter)

        fields = {
            '__call__': Type.__call__,
            '__tag__': self.tag
        }

        for c in children:
            if isinstance(c, (sequence,)):
                fields['realtype'] = c
                break
        else:
            raise Exception('No any subtype')

        return type(name, (complexType,), fields)(**self.attributes)(*children)

    @classmethod
    def fill_node(cls, node, instance):
        cls.realtype.fill_node(node, instance)

    @classmethod
    def init(cls, instance, **kwargs):
        cls.realtype.init(instance, **kwargs)


class simpleType(Type):
    __namespace__ = namespace

    @staticmethod
    def init(instance, value):
        instance.value = value

    @classmethod
    def fill_node(cls, node, instance):
        node.text = cls.from_python(instance.value)

    @staticmethod
    def from_python(value):
        return unicode(value)


class string(simpleType):
    __namespace__ = namespace


class int_(simpleType):
    __namespace__ = namespace


class float_(simpleType):
    __namespace__ = namespace

