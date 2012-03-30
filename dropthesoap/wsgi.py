from webob import Request, Response
from webob.exc import HTTPNotFound
from wsgiref.simple_server import make_server

class Application(object):
    def __init__(self, service):
        self.service = service

    def __call__(self, environ, start_response):
        request = Request(environ)
        if request.method == 'GET' and request.query_string == 'wsdl':
            response = Response(self.service.get_wsdl(request.path_url))
            response.content_type = 'text/xml'
        elif request.method == 'POST':
            response = Response(self.service.call(request, request.body))
            response.content_type = 'text/xml'
        else:
            response = HTTPNotFound()

        return response(environ, start_response)

    def run(self, host='localhost', port=8000):
        httpd = make_server(host, port, self)
        httpd.serve_forever()
