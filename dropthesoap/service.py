from .schema import xs, wsdl, soap
from .schema.model import Namespace, get_root, etree, Instance

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


class Service(object):
    def __init__(self, name, tns):
        self.name = name
        self.methods = {}

        self.method_schema = xs.schema(Namespace(tns))
        self.schema = xs.schema(Namespace(tns))

    def expose(self, returns=None):
        assert returns
        def inner(func):
            name = func.__name__
            defaults = func.__defaults__
            names = func.__code__.co_varnames[-len(defaults):]

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
            if isinstance(returns, customize):
                response = returns.get_element(rname)
            else:
                response = xs.element(rname, returns)

            self.schema(response)

            self.methods[name] = func, names, response
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

        for name in self.methods:
            nameRequest = '%sRequest' % name
            nameResponse = '%sResponse' % name

            messages.append(wsdl.message.instance(name=nameRequest,
                part=wsdl.part.instance(name='parameters', element='tns:%s' % name)))

            messages.append(wsdl.message.instance(name=nameResponse,
                part=wsdl.part.instance(name='parameters', element='tns:%s' % nameResponse)))

            operations.append(wsdl.operation.instance(name=name,
                input=wsdl.input.instance(message='tns:%s' % nameRequest),
                output=wsdl.output.instance(message='tns:%s' % nameResponse)))

            boperations.append(wsdl.operation.instance(
                name=name,
                operation=wsdl.soap_operation.instance(soapAction=name),
                input=wsdl.input.instance(body=wsdl.soap_body.instance(use='literal')),
                output=wsdl.output.instance(body=wsdl.soap_body.instance(use='literal'))))

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

    def dispatch(self, request):
        func, names, response = self.methods[request.tag]
        args = []
        for name in names:
            args.append(getattr(request, name))

        result = func(*args)

        if not isinstance(result, Instance):
            result = response.instance(result)

        return result

    def call(self, xml):
        envelope = soap.schema.fromstring(xml)
        request = self.method_schema.from_node(envelope.Body._any[0])
        response = self.dispatch(request)

        renvelope = soap.Envelope.instance(Body=soap.Body.instance(_any=[response]))
        tree = get_root(renvelope)
        tree.attrib['soap:encodingStyle'] = 'http://www.w3.org/2001/12/soap-encoding'

        return etree.tostring(tree)
