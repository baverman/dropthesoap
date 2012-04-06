try:
    from xml.etree import cElementTree as etree
except ImportError:
    from xml.etree import ElementTree as etree


class TagDescriptor(object):
    def __get__(_self, _instance, cls):
        return getattr(cls, '__tag__', None) or cls.__name__


class TypeNameDescriptor(object):
    def __get__(_self, instance, cls):
        return instance.attributes['name'] if instance else cls.tag


class Node(object):
    tag = TagDescriptor()
    type_name = TypeNameDescriptor()

    def __init__(self, **attributes):
        self.attributes = attributes.copy()
        self.children = []

    def __call__(self, *children):
        self.children.extend(children)
        return self

    def get_node(self, creator):
        attributes = self.attributes
        if 'type' in attributes:
            attributes = attributes.copy()
            etype = attributes['type']
            attributes['type'] = creator.get_prefixed_tag(etype.namespace, etype.type_name)

        if 'base' in attributes:
            attributes = attributes.copy()
            etype = attributes['base']
            attributes['base'] = creator.get_prefixed_tag(etype.namespace, etype.type_name)

        node = creator(self.__class__.namespace, self.tag, attributes)
        for child in self.children:
            node.append(child.get_node(creator))

        return node


class Type(Node):
    class InstanceClassDescriptor(object):
        def __init__(self):
            self.cache = {}

        def __get__(self, _instance, cls):
            try:
                return self.cache[cls]
            except KeyError:
                pass

            result = self.cache[cls] = create_instance_class(cls)
            return result

    instance_class = InstanceClassDescriptor()

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def instance(cls, *args, **kwargs):
        return TypeInstance(cls, *args, **kwargs)


class Namespace(object):
    def __init__(self, namespace, abbr=None):
        self.namespace = namespace
        self.abbr = abbr

    def __str__(self):
        return self.namespace


class Instance(object):
    def __init__(self, _element, *args, **kwargs):
        self._element = _element
        self._type.init(self, *args, **kwargs)

    def get_node(self, creator):
        node = self._element.create_node(creator)
        self._type.fill_node(node, self, creator)
        return node

    @property
    def tag(self):
        return self._element.name


class TypeInstance(object):
    def __init__(self, type, *args, **kwargs):
        self.inferior_instance = type.instance_class(None, *args, **kwargs)

    def create(self, element):
        self.inferior_instance._element = element
        return self.inferior_instance

    def __getattr__(self, name):
        return getattr(self.inferior_instance, name)

    def __setattr__(self, name, value):
        if name in ('inferior_instance'):
            object.__setattr__(self, name, value)
        else:
            setattr(self.inferior_instance, name, value)


class ElementInstance(Instance):
    def __init__(self, tree):
        self.value = tree

    def get_node(self, _creator):
        return self.value


class BareInstance(object):
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

    def create(self, element):
        return element.instance(*self.args, **self.kwargs)


def create_instance_class(etype):
    fields = {}
    name = etype.get_name() + 'Instance'
    fields['_type'] = etype

    return type(name, (Instance,), fields)

def get_root(node_getter):
    creator = ElementCreator()
    node = node_getter.get_node(creator)
    for uri, prefix in creator.prefixes.iteritems():
        node.attrib['xmlns:%s' % prefix] = uri

    return node


class ElementCreator(object):
    def __init__(self):
        self.ns_counter = 0
        self.prefixes = {}

    def get_prefix(self, namespace):
        try:
            return self.prefixes[namespace.namespace]
        except KeyError:
            pass

        if namespace.abbr:
            prefix = namespace.abbr
        else:
            prefix = 'ns%d' % self.ns_counter
            self.ns_counter += 1

        self.prefixes[namespace.namespace] = prefix
        return prefix

    def get_prefixed_tag(self, namespace, tag):
        return '{}:{}'.format(self.get_prefix(namespace), tag)

    def __call__(self, namespace, tag, *args, **kwargs):
        return etree.Element(self.get_prefixed_tag(namespace, tag), *args, **kwargs)