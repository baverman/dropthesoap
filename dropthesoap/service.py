import traceback
import logging
logger = logging.getLogger('dropthesoap.request')

from .schema import xs, wsdl, soap
from .schema.model import Namespace, get_root, etree


class Request(object):
    def __init__(self, transport_request, envelope):
        self.transport_request = transport_request
        self.envelope = envelope
        self.header = None


class Method(object):
    def __init__(self, func, request, response):
        self.func = func
        self.request = request
        self.response = response
        self.need_context = False
        self.header = None

    def __call__(self, ctx, request):
        if self.header:
            if ctx.envelope.Header:
                ctx.header = self.header.from_node(ctx.envelope.Header._any[0])
            else:
                ctx.header = None

        args = [ctx] if self.need_context else []
        if self.request._unpack_params:
            for name in self.request._params:
                args.append(getattr(request, name))
        else:
            args.append(request)

        return self.response.normalize(self.func(*args))



class Fault(Exception):
    def __init__(self, code, message):
        self.code = code
        Exception.__init__(self, message)


def make_message_element(name, obj):
    if isinstance(obj, xs.element):
        return obj
    else:
        if isinstance(obj, xs.Type) and not hasattr(obj, 'name'):
            return xs.element(name)(obj)
        else:
            return xs.element(name, obj)


class Service(object):
    def __init__(self, name, tns):
        self.name = name
        self.methods = {}
        self.req2method = {}

        self.schema = xs.schema(Namespace(tns))

    def expose(self, request=None, response=None):
        if callable(request) and not isinstance(request, (xs.Type, xs.element)) and type(request) is not type:
            decorated_func = request
            request = None
        else:
            decorated_func = None

        def inner(func):
            name = func.__name__

            req_name = name + 'Request'
            if request is None:
                defaults = func.__defaults__
                if defaults:
                    names = func.__code__.co_varnames[:func.__code__.co_argcount][-len(defaults):]
                else:
                    names = []
                    defaults = []

                celements = [xs.element(n, t) for n, t in zip(names, defaults)]
                request_elem = xs.element(req_name)(xs.cts(*celements))
                request_elem._params = names
                request_elem._unpack_params = True
            else:
                request_elem = make_message_element(req_name, request)
                req_name = request_elem.name
                request_elem._unpack_params = False

            self.schema(request_elem)

            resp_name = name + 'Response'
            if response is None:
                response_elem = self.schema[resp_name]
            else:
                response_elem = make_message_element(resp_name, response)
                self.schema(response_elem)

            method = Method(func, request_elem, response_elem)
            self.methods[name] = method
            self.req2method[req_name] = method
            return func

        return inner(decorated_func) if decorated_func else inner

    def wraps(self, original_func):
        name = original_func.__name__
        def inner(func):
            self.methods[name].func = func
            self.methods[name].need_context = True
            func.__name__ = name
            return func

        return inner

    def header(self, header):
        def inner(func):
            rheader = header
            if isinstance(rheader, basestring):
                rheader = self.schema[rheader]

            self.methods[func.__name__].header = rheader
            return func

        return inner

    def get_wsdl(self, url):
        defs = wsdl.definitions.instance()
        defs.types = wsdl.types.instance(_any=get_root(self.schema))

        messages = defs.message = []

        port = wsdl.portType.instance(name='%sPortType' % self.name)
        operations = port.operation = []
        defs.portType = [port]

        binding = wsdl.binding.instance(
            name='%sBinding' % self.name, type='tns:%sPortType' % self.name,
            binding = wsdl.soap_binding.instance(transport='http://schemas.xmlsoap.org/soap/http', style='document'))
        defs.binding = [binding]
        boperations = binding.operation = []

        for name, method in self.methods.iteritems():
            req_name = method.request.name
            resp_name = method.response.name

            messages.append(wsdl.message.instance(name=req_name,
                part=wsdl.part.instance(name='parameters', element='tns:%s' % req_name)))

            messages.append(wsdl.message.instance(name=resp_name,
                part=wsdl.part.instance(name='parameters', element='tns:%s' % resp_name)))

            operations.append(wsdl.operation.instance(name=name,
                input=wsdl.input.instance(message='tns:%s' % req_name),
                output=wsdl.output.instance(message='tns:%s' % resp_name)))

            binput = wsdl.input.instance(body=wsdl.soap_body.instance(use='literal'))
            if method.header:
                binput.header = wsdl.soap_header.instance(
                    use='literal', message='tns:%s' % method.header.name, part=method.header.name)

            boperations.append(wsdl.operation.instance(
                name=name,
                operation=wsdl.soap_operation.instance(soapAction=name),
                input=binput,
                output=wsdl.output.instance(body=wsdl.soap_body.instance(use='literal'))))

        for header in set(r.header for r in self.methods.itervalues() if r.header):
            messages.append(wsdl.message.instance(name=header.name,
                part=wsdl.part.instance(name=header.name, element='tns:%s' % header.name)))

        defs.service = [wsdl.service.instance(
            name=self.name,
            port=wsdl.port.instance(
                name='%sPort' % self.name,
                binding='tns:%sBinding' % self.name,
                address=wsdl.soap_address.instance(location=url))
        )]

        tree = get_root(defs)
        tree.attrib['targetNamespace'] = self.schema.targetNamespace.namespace
        tree.attrib['xmlns:tns'] = self.schema.targetNamespace.namespace

        return etree.tostring(tree)

    def call(self, transport_request, xml):
        try:
            envelope = soap.schema.fromstring(xml)
            request = self.schema.from_node(envelope.Body._any[0])
            ctx = Request(transport_request, envelope)
            method = self.req2method[request.tag]
            response = method(ctx, request)
        except Fault as e:
            response = soap.Fault.instance(faultcode=e.code, faultstring=e.message)

        return response

    def response_to_string(self, response):
        renvelope = soap.Envelope.instance(Body=soap.Body.instance(_any=[response]))
        tree = get_root(renvelope)
        tree.attrib['soap:encodingStyle'] = 'http://www.w3.org/2001/12/soap-encoding'
        return etree.tostring(tree, encoding='utf-8')
