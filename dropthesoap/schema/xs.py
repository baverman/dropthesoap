from .model import Node, Namespace, Type, Instance, etree, BareInstance
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

    @cached_property
    def top_elements(self):
        result = {}
        for c in self.children:
            if isinstance(c, element):
                result[self.qname(c.name)] = c

        return result

    def update_schema(self, node):
        for c in node.children:
            if isinstance(c, element):
                c.schema = self

            self.update_schema(c)

    def __call__(self, *children):
        Node.__call__(self, *children)
        self.update_schema(self)
        return self

    def from_node(self, tree):
        element = self.top_elements[tree.tag]
        return element.from_node(tree)

    def fromstring(self, xml):
        return self.from_node(etree.fromstring(xml))

    def qname(self, tag):
        if self.targetNamespace:
            return '{%s}%s' % (self.targetNamespace, tag)
        else:
            return tag

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

    def from_node(self, node):
        result = self.type.from_node(node)
        if isinstance(result, BareInstance):
            return result.create(self)

        return result


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
                raise Exception("Can't found [%s] in sequence" % name)

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

    def from_node(self, node):
        kwargs = {}
        for c in self.element_list:
            kwargs[c.name] = c.from_node(node.find(c.schema.qname(c.name)))

        return BareInstance((), kwargs)


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

    @classmethod
    def from_node(cls, node):
        return cls.realtype.from_node(node)


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

    @staticmethod
    def from_node(node):
        return node.text


class int_(simpleType):
    __tag__ = 'int'
    namespace = namespace

    @staticmethod
    def from_node(node):
        return int(node.text)


class float_(simpleType):
    __tag__ = 'float'
    namespace = namespace

    @staticmethod
    def from_node(node):
        return float(node.text)
