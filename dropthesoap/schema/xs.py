from itertools import izip_longest

from .model import Node, Namespace, Type, Instance, etree, BareInstance
from ..utils import cached_property

namespace = Namespace('http://www.w3.org/2001/XMLSchema', 'xs')
unbounded = 'unbounded'

_any = any
_int = int
_float = float

def extract_type(value):
    return value if type(value) is type else value.__class__

def is_type(value):
    return (type(value) is type and issubclass(value, Type)) or isinstance(value, Type)

def process_attributes(self, attributes):
    attributes = attributes.copy()
    attributes.pop('self', None)
    for k, v in attributes.items():
        if v is None:
            del attributes[k]
        else:
            setattr(self, k, v)
            attributes[k] = str(v)

    return attributes


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

    def __init__(self, name=None, type=None, ref=None, substitutionGroup=None, default=None,
            fixed=None, form=None, maxOccurs=None, minOccurs=None, nillable=None, abstract=None,
            block=None, final=None):

        attributes = process_attributes(self, locals())

        if type is not None:
            attributes['type'] = type
            self.type = extract_type(type)

        Node.__init__(self, **attributes)

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

    @cached_property
    def is_array(self):
        minOccurs = getattr(self, 'minOccurs', 1)
        maxOccurs = getattr(self, 'maxOccurs', 1)
        if maxOccurs == unbounded:
            maxOccurs = 99999999

        return minOccurs > 1 or maxOccurs > 1

    def match(self, node):
        return self.schema.qname(self.name) == node.tag

    def __repr__(self):
        return '<{} name="{}">'.format(self.tag, self.name)


class attribute(Node):
    namespace = namespace
    def __init__(self, name=None, type=None, default=None, use=None, ref=None, form=None, fixed=None):
        attributes = process_attributes(self, locals())

        if type is not None:
            attributes['type'] = type
            self.type = extract_type(type)

        Node.__init__(self, **attributes)

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
                raise Exception("Can't found [%s] in sequence" % name)

            setattr(instance, name, value)

    def fill_node(self, node, instance, creator):
        for e in self.element_list:
            if hasattr(instance, e.name):
                values = getattr(instance, e.name)
                if not e.is_array:
                    values = [values]

                for v in values:
                    if not isinstance(v, Instance):
                        v = e.instance(v)

                    node.append(v.get_node(creator))
            elif getattr(e, 'minOccurs', 1) == 0:
                pass
            else:
                raise Exception("Can't found field [%s] in instance" % e.name)

    def from_node(self, node):
        kwargs = {}
        cnodes = iter(node)
        c = next(cnodes, None)
        elements = iter(self.element_list)
        e = next(elements)

        try:
            while True:
                if c is None:
                    if e.name not in kwargs:
                        if getattr(e, 'minOccurs', 1) > 0:
                            raise ValueError('Boo')

                        if e.is_array:
                            kwargs[e.name] = []
                        else:
                            kwargs[e.name] = None

                    e = next(elements)
                elif e.match(c):
                    if e.is_array:
                        kwargs.setdefault(e.name, []).append(e.from_node(c))
                    else:
                        kwargs[e.name] = e.from_node(c)
                        e = next(elements)
                else:
                    if e.name not in kwargs:
                        if getattr(e, 'minOccurs', 1) > 0:
                            raise ValueError('Boo')

                        if e.is_array:
                            kwargs[e.name] = []
                        else:
                            kwargs[e.name] = None

                    e = next(elements)
                    continue

                c = next(cnodes, None)
        except StopIteration:
            pass

        return BareInstance((), kwargs)


class AttributeFiller(object):
    def __init__(self, realtype, attributes):
        self.attributes = attributes
        self.realtype = realtype

    def fill_node(self, node, instance, creator):
        for k, v in self.attributes.iteritems():
            if hasattr(instance, k):
                value = getattr(instance, k)
                if isinstance(value, Instance):
                    value = value.value

                node.attrib[k] = v.type.from_python(value)

        self.realtype.fill_node(node, instance, creator)

    def init(self, instance, **kwargs):
        for k in list(kwargs):
            if k in self.attributes:
                setattr(instance, k, kwargs[k])
                del kwargs[k]

        self.realtype.init(instance, **kwargs)

    def from_node(self, node):
        kwargs = {}
        for k, v in node.items():
            kwargs[k] = self.attributes[k].type.to_python(v)

        result = self.realtype.from_node(node)
        if kwargs and isinstance(result, BareInstance):
            result.kwargs.update(kwargs)

        return result


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

        attrs = {}
        for c in children:
            if isinstance(c, (sequence,)):
                fields['realtype'] = c
            elif isinstance(c, attribute):
                attrs[c.name] = c

        if not fields.get('realtype', None):
            raise Exception('No any subtype')

        if attrs:
            fields['realtype'] = AttributeFiller(fields['realtype'], attrs)

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

    @classmethod
    def from_node(cls, node):
        return cls.to_python(node.text)


class string(simpleType):
    namespace = namespace

    @staticmethod
    def to_python(value):
        return value


class int(simpleType):
    namespace = namespace

    @staticmethod
    def to_python(value):
        return _int(value)


class float_(simpleType):
    namespace = namespace

    @staticmethod
    def to_python(value):
        return _float(value)


class anyType(Type):
    @staticmethod
    def init(instance, value):
        instance.value = value

    @staticmethod
    def fill_node(node, instance, _creator):
        node.append(instance.value)

    @staticmethod
    def from_node(node):
        return node


class any(element):
    namespace = namespace
    def __init__(self, minOccurs=None, maxOccurs=None, namespace=None, processContents=None):
        attributes = process_attributes(self, locals())
        self.name = '_any'
        self.type = anyType
        Node.__init__(self, **attributes)

    def match(self, node):
        return True


def cts(*args):
    return complexType()(sequence()(*args))