from StringIO import StringIO
from lxml import etree as lxml_etree
from dropthesoap.schema.model import etree, get_root

from suds.transport import Transport, Reply

def lxml_doc(node_getter):
    return lxml_etree.parse(StringIO(tostring(node_getter)))

def validate(schema, instance):
    xmlschema = lxml_etree.XMLSchema(lxml_doc(schema))
    result = xmlschema.validate(lxml_doc(instance))
    if not result:
        print xmlschema.error_log

    return result

def tostring(node_getter):
    return etree.tostring(get_root(node_getter))


class DirectSudsTransport(Transport):
    def __init__(self, service):
        Transport.__init__(self)
        self._service = service

    def open(self, _request):
        return StringIO(self._service.get_wsdl('http://testserver/'))

    def send(self, request):
        return Reply('200 OK', {}, self._service.call(request, request.message))