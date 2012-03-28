import traceback
import logging
logger = logging.getLogger('dropthesoap.request')

from .schema import xs, wsdl, soap
from .schema.model import Namespace, get_root, etree, Instance, TypeInstance

class customize(object):
    def __init__(self, type, minOccurs=None, maxOccurs=None, default=None, nillable=None):
        self.attributes = locals().copy()
        del self.attributes['self']
        del self.attributes['type']
        self.type = type

    def get_element(self, name):
        return xs.element(name, self.type, **self.attributes)

class optional(customize):
    def __init__(self, type):
        customize.__init__(self, type, minOccurs=0)


class array(customize):
    def __init__(self, type):
        customize.__init__(self, type, minOccurs=0, maxOccurs=xs.unbounded)


class Request(object):
    def __init__(self, transport_request, envelope):
        self.transport_request = transport_request
        self.envelope = envelope
        self.header = None


class Method(object):
    def __init__(self, func, names, response):
        self.func = func
        self.names = names
        self.response = response
        self.need_context = False
        self.header = None


class Fault(Exception):
    def __init__(self, code, message):
        self.code = code
        Exception.__init__(self, message)


class Service(object):
    def __init__(self, name, tns):
        self.name = name
        self.methods = {}

        self.method_schema = xs.schema(Namespace(tns))
        self.schema = xs.schema(Namespace(tns))

    def expose(self, returns):
        def inner(func):
            name = func.__name__
            defaults = func.__defaults__
            if defaults:
                names = func.__code__.co_varnames[:func.__code__.co_argcount][-len(defaults):]
            else:
                names = []
                defaults = []

            celements = []
            for n, t in zip(names, defaults):
                if isinstance(t, customize):
                    celements.append(t.get_element(n))
                else:
                    celements.append(xs.element(n, t))

            request = xs.element(name=name)(
                xs.complexType()(
                    xs.sequence()(*celements)))

            self.method_schema(request)
            self.schema(request)

            rname = name + 'Response'
            if isinstance(returns, xs.element):
                response = returns
                response.name = rname
                response.attributes['name'] = rname
            elif isinstance(returns, customize):
                response = returns.get_element(rname)
            else:
                response = xs.element(rname, returns)

            self.schema(response)

            self.methods[name] = Method(func, names, response)
            return func

        return inner

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
            self.methods[func.__name__].header = header
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
            nameRequest = '%sRequest' % name
            nameResponse = '%sResponse' % name

            messages.append(wsdl.message.instance(name=nameRequest,
                part=wsdl.part.instance(name='parameters', element='tns:%s' % name)))

            messages.append(wsdl.message.instance(name=nameResponse,
                part=wsdl.part.instance(name='parameters', element='tns:%s' % nameResponse)))

            operations.append(wsdl.operation.instance(name=name,
                input=wsdl.input.instance(message='tns:%s' % nameRequest),
                output=wsdl.output.instance(message='tns:%s' % nameResponse)))

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

    def dispatch(self, ctx, request):
        method = self.methods[request.tag]

        if method.header:
            ctx.header = method.header.from_node(ctx.envelope.Header._any[0])

        args = [ctx] if method.need_context else []
        for name in method.names:
            args.append(getattr(request, name))

        return method.response.normalize(method.func(*args))

    def call(self, transport_request, xml):
        try:
            envelope = soap.schema.fromstring(xml)
            request = self.method_schema.from_node(envelope.Body._any[0])
            ctx = Request(transport_request, envelope)

            response = self.dispatch(ctx, request)
        except Exception as e:
            faultcode = 'Server'
            if isinstance(e, Fault):
                faultcode = e.code
            else:
                logger.exception('Exception during soap request:')

            response = soap.Fault.instance(faultcode=faultcode, faultstring=str(e),
                detail=traceback.format_exc())

        renvelope = soap.Envelope.instance(Body=soap.Body.instance(_any=[response]))
        tree = get_root(renvelope)
        tree.attrib['soap:encodingStyle'] = 'http://www.w3.org/2001/12/soap-encoding'

        return etree.tostring(tree, encoding='utf-8')
