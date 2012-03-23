from .model import Node, Namespace, Type, Instance
from ..utils import cached_property

namespace = Namespace('http://www.w3.org/2001/XMLSchema', 'xs')

def extract_type(value):
    return value if type(value) is type else value.__class__

def is_type(value):
    return (type(value) is type and issubclass(value, Type)) or isinstance(value, Type)


class schema(Node):
    namespace = namespace

    def __init__(self, targetNamespace, elementFormDefault='qualified'):
        self.targetNamespace = targetNamespace
        Node.__init__(self, targetNamespace=targetNamespace.namespace, elementFormDefault=elementFormDefault)

    def update_schema(self, node):
        for c in node.children:
            if isinstance(c, element):
                c.schema = self

            self.update_schema(c)

    def __call__(self, *children):
        Node.__call__(self, *children)
        self.update_schema(self)
        return self


class element(Node):
    namespace = namespace

    def __init__(self, name=None, type=None, **kwargs):
        kwargs = kwargs.copy()
        if type is not None:
            kwargs['type'] = type
            self.type = extract_type(type)

        if name:
            kwargs['name'] = name
            self.name = name

        Node.__init__(self, **kwargs)

    def __call__(self, *children):
        Node.__call__(self, *children)
        for c in children:
            if is_type(c):
                self.type = extract_type(c)
                break

        return self

    def instance(self, *args, **kwargs):
        return self.type.instance_class(self, *args, **kwargs)


class sequence(Node):
    namespace = namespace

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

    def fill_node(self, node, instance, creator):
        for e in self.element_list:
            if hasattr(instance, e.name):
                value = getattr(instance, e.name)
                if not isinstance(value, Instance):
                    value = e.instance(value)

                node.append(value.get_node(creator))
            else:
                raise Exception('Boo')


class complexType(Type):
    namespace = namespace
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
    def fill_node(cls, node, instance, creator):
        cls.realtype.fill_node(node, instance, creator)

    @classmethod
    def init(cls, instance, **kwargs):
        cls.realtype.init(instance, **kwargs)


class simpleType(Type):
    namespace = namespace

    @staticmethod
    def init(instance, value):
        instance.value = value

    @classmethod
    def fill_node(cls, node, instance, _creator):
        node.text = cls.from_python(instance.value)

    @staticmethod
    def from_python(value):
        return unicode(value)


class string(simpleType):
    namespace = namespace


class int_(simpleType):
    __tag__ = 'int'
    namespace = namespace


class float_(simpleType):
    __tag__ = 'float'
    namespace = namespace

