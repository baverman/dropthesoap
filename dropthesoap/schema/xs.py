from datetime import datetime

from .model import Node, Namespace, Type, Instance, etree, BareInstance, ElementInstance, TypeInstance
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
            if isinstance(v, bool):
                attributes[k] = ('false', 'true')[v]
            else:
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

    def __getitem__(self, name):
        return self.top_elements[self.qname(name)]

    def update_schema(self, nodes):
        for c in nodes:
            if isinstance(c, element) and not hasattr(c, 'schema'):
                c.schema = self

            if isinstance(c, Type) and 'name' in c.attributes:
                c.namespace = self.targetNamespace

            self.update_schema(c.children)

    def __call__(self, *children):
        Node.__call__(self, *children)
        self.update_schema(children)
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

    def create_node(self, creator):
        return creator(self.schema.targetNamespace, self.name)

    def __call__(self, *children):
        Node.__call__(self, *children)
        for c in children:
            if is_type(c):
                self.type = extract_type(c)
                break

        return self

    def __getitem__(self, name):
        return self.type.realtype.element_dict[name]

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

    def normalize(self, value):
        if isinstance(value, TypeInstance):
            return value.create(self)
        elif not isinstance(value, Instance):
            return self.instance(value)
        else:
            return value

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
                    if v is None:
                        node.append(e.create_node(creator))
                    else:
                        node.append(e.normalize(v).get_node(creator))

            elif getattr(e, 'minOccurs', 1) == 0:
                pass
            else:
                raise Exception("Can't found field [%s] in instance" % e.name)

    def from_node(self, node):
        kwargs = {}
        cnodes = iter(node)
        c = next(cnodes, None)
        elements = iter(self.element_list)
        try:
            e = next(elements)
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

        if self.realtype:
            self.realtype.fill_node(node, instance, creator)

    def init(self, instance, **kwargs):
        for k in list(kwargs):
            if k in self.attributes:
                setattr(instance, k, kwargs[k])
                del kwargs[k]

        if self.realtype:
            self.realtype.init(instance, **kwargs)

    def from_node(self, node):
        kwargs = {}
        for k, v in node.items():
            kwargs[k] = self.attributes[k].type.to_python(v)

        if self.realtype:
            result = self.realtype.from_node(node)
            if kwargs:
                if isinstance(result, BareInstance):
                    result.kwargs.update(kwargs)
                elif not isinstance(result, Instance):
                    kwargs['value'] = result
                    result = BareInstance((), kwargs)

        else:
            result = BareInstance((), kwargs)

        return result


class _DelegateType(object):
    @classmethod
    def fill_node(cls, node, instance, creator):
        cls.realtype.fill_node(node, instance, creator)

    @classmethod
    def init(cls, instance, **kwargs):
        cls.realtype.init(instance, **kwargs)

    @classmethod
    def from_node(cls, node):
        return cls.realtype.from_node(node)


class complexType(Type, _DelegateType):
    namespace = namespace
    type_counter = 0

    def __call__(self, *children):
        name = self.attributes.get('name', None)
        if not name:
            complexType.type_counter += 1
            name = 'ComplexType{}'.format(complexType.type_counter)

        fields = {
            '__call__': Type.__call__,
            '__tag__': self.tag
        }

        attrs = {}
        for c in children:
            if isinstance(c, (sequence, simpleContent)):
                fields['realtype'] = c
            elif isinstance(c, attribute):
                attrs[c.name] = c

        if attrs:
            fields['realtype'] = AttributeFiller(fields.get('realtype', None), attrs)

        return type(name, (complexType,), fields)(**self.attributes)(*children)


class simpleType(Type, _DelegateType):
    namespace = namespace
    type_counter = 0

    @classmethod
    def init(cls, instance, value):
        cls.realtype.init(instance, value)

    def __call__(self, *children):
        name = self.attributes.get('name', None)
        if not name:
            simpleType.type_counter += 1
            name = 'SimpleType{}'.format(complexType.type_counter)

        fields = {
            '__call__': Type.__call__,
            '__tag__': self.tag
        }

        for c in children:
            if isinstance(c, restriction):
                fields['realtype'] = c
                break
        else:
            raise Exception('Child of simple type must be a restriction')

        for c in fields['realtype'].children:
            fields[c.value] = c.value

        return type(name, (simpleType,), fields)(**self.attributes)(*children)


class _FinalSimpleType(Type):
    @staticmethod
    def init(instance, value):
        instance.value = value

    @classmethod
    def fill_node(cls, node, instance, _creator):
        node.text = cls.from_python(instance.value)

    @classmethod
    def from_node(cls, node):
        return cls.to_python(node.text)


class string(_FinalSimpleType):
    namespace = namespace

    @staticmethod
    def from_python(value):
        assert isinstance(value, basestring), 'Value should be a string not %s' % (type(value))
        return value

    @staticmethod
    def to_python(value):
        return value


class dateTime(_FinalSimpleType):
    namespace = namespace

    @staticmethod
    def from_python(value):
        return value.replace(microsecond=0).isoformat()

    @staticmethod
    def to_python(value):
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')


class int(_FinalSimpleType):
    namespace = namespace

    @staticmethod
    def from_python(value):
        return str(value)

    @staticmethod
    def to_python(value):
        return _int(value)


class float(_FinalSimpleType):
    namespace = namespace

    @staticmethod
    def from_python(value):
        return str(value)

    @staticmethod
    def to_python(value):
        return _float(value)


class double(float):
    namespace = namespace


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

    def instance(self, node=None):
        return ElementInstance(node)

    def match(self, node):
        return True


class restriction(Node):
    namespace = namespace

    def __init__(self, base):
        self.base = extract_type(base)
        Node.__init__(self, base=base)

    def init(self, instance, value):
        self.base.init(instance, value)

    def fill_node(self, node, instance, _creator):
        self.base.fill_node(node, instance, _creator)

    def from_node(self, node):
        return self.base.from_node(node)


class _InstanceDelegateType(object):
    def init(self, instance, *args, **kwargs):
        self.delegate.init(instance, *args, **kwargs)

    def fill_node(self, node, instance, _creator):
        self.delegate.fill_node(node, instance, _creator)

    def from_node(self, node):
        return self.delegate.from_node(node)


class extension(_InstanceDelegateType, Node):
    namespace = namespace

    def __init__(self, base):
        self.base = extract_type(base)
        Node.__init__(self, base=base)

    def __call__(self, *children):
        Node.__call__(self, *children)

        attrs = {}
        for c in children:
            if isinstance(c, attribute):
                attrs[c.name] = c

        if attrs:
            self.delegate = AttributeFiller(self.base, attrs)
        else:
            self.delegate = self.base

        return self


class simpleContent(Node, _InstanceDelegateType):
    namespace = namespace

    def __call__(self, *children):
        Node.__call__(self, *children)

        for c in children:
            if isinstance(c, (extension, restriction)):
                self.delegate = c
                break

        return self


class enumeration(Node):
    namespace = namespace
    def __init__(self, value):
        self.value = value
        Node.__init__(self, value=value)


def cts(*args):
    return complexType()(sequence()(*args))
