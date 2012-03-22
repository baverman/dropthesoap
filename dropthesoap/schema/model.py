try:
    from xml.etree import cElementTree as etree
except ImportError:
    from xml.etree import ElementTree as etree


class TagDescriptor(object):
    def __get__(self, instance, cls):
        return cls.__name__


class PTagDescriptor(object):
    def __get__(self, instance, cls):
        return cls.__namespace__.get_prefixed_name(cls.tag)


class Model(object):
    tag = TagDescriptor()
    ptag = PTagDescriptor()

    def __init__(self, **attributes):
        self._attributes = attributes.copy()
        for name, value in self._attributes.iteritems():
            if type(value) is type and issubclass(value, Model):
                self._attributes[name] = value.ptag

        self._children = []

    def __call__(self, *children):
        self._children = list(children)
        return self

    def get_node(self):
        node = etree.Element(self.ptag, self._attributes)
        for child in self._children:
            node.append(child.get_node())

        return node


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