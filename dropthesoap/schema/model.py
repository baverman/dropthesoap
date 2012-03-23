try:
    from xml.etree import cElementTree as etree
except ImportError:
    from xml.etree import ElementTree as etree

from ..utils import cached_property

class TagDescriptor(object):
    def __get__(self, instance, cls):
        return getattr(cls, '__tag__', None) or cls.__name__


class PTagDescriptor(object):
    def __get__(self, instance, cls):
        return cls.__namespace__.get_prefixed_name(cls.tag)


class Node(object):
    tag = TagDescriptor()
    ptag = PTagDescriptor()

    def __init__(self, **attributes):
        self.attributes = attributes.copy()
        self.children = []

    def __call__(self, *children):
        self.children = list(children)
        return self

    def get_node(self):
        node = etree.Element(self.ptag, self.attributes)
        for child in self.children:
            node.append(child.get_node())

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

    @classmethod
    def get_name(cls):
        return cls.__name__

    instance_class = InstanceClassDescriptor()


class Namespace(object):
    ns_counter = 0

    def __init__(self, namespace, abbr=None):
        self.namespace = namespace

        if not abbr:
            abbr = 'ns%d' % Namespace.ns_counter
            Namespace.ns_counter += 1

        self.abbr = abbr

    def get_prefixed_name(self, tag):
        return '{}:{}'.format(self.abbr, tag)

    def get_qname(self, tag):
        return etree.QName(self.namespace, tag).text


class Instance(object):
    def __init__(self, tag, *args, **kwargs):
        self._tag = tag
        self._type.init(self, *args, **kwargs)

    def get_node(self):
        node = etree.Element(self._tag)
        self._type.fill_node(node, self)
        return node


def create_instance_class(etype):
    fields = {}
    name = etype.get_name() + 'Instance'
    fields['_type'] = etype

    return type(name, (Instance,), fields)
